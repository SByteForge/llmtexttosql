import os

from langchain_ollama import ChatOllama
from langchain_community.utilities import SQLDatabase

from utils import extract_sql, validate_readonly_sql
from database import execute_query

SQL_SYSTEM_PROMPT = """You are an expert {dialect} database analyst.
Given a database schema and a question, write a single read-only SQL query
that answers the question.

Rules:
- Output ONLY the SQL query, wrapped in <sql></sql> tags. No explanation.
- Only use SELECT / WITH statements. Never write INSERT, UPDATE, DELETE,
  DROP, ALTER, or any other statement that modifies data or schema.
- Only use tables and columns that appear in the schema below.
- Use the exact table and column names from the schema.
- Limit results to at most {max_rows} rows unless the question asks for an
  aggregate (e.g. count, sum, average) that naturally returns fewer rows.

Schema:
{schema}
"""

ANSWER_SYSTEM_PROMPT = """You answer questions about data using SQL query
results. Given the user's question, the SQL query that was run, and its
results, write a concise, plain-language answer. Reference specific numbers
from the results. If the results are empty, say so plainly. Do not mention
SQL or the query itself unless the user asked about it."""


def get_llm(config: dict) -> ChatOllama:
    llm_config = config["llm"]
    base_url = os.getenv("OLLAMA_BASE_URL") or llm_config.get("base_url", "http://localhost:11434")
    return ChatOllama(
        model=llm_config.get("model", "mistral"),
        base_url=base_url,
        num_predict=llm_config.get("num_predict", 1024),
        temperature=0,
    )


def generate_sql(llm: ChatOllama, db: SQLDatabase, question: str, max_rows: int) -> str:
    system = SQL_SYSTEM_PROMPT.format(
        dialect=db.dialect,
        schema=db.get_table_info(),
        max_rows=max_rows,
    )
    response = llm.invoke(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]
    )
    return extract_sql(response.content)


def generate_answer(llm: ChatOllama, question: str, sql: str, columns, rows) -> str:
    results_preview = ", ".join(columns) + "\n" + "\n".join(str(r) for r in rows[:50])
    response = llm.invoke(
        [
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\nSQL query: {sql}\n\n"
                    f"Results ({len(rows)} row(s)):\n{results_preview}"
                ),
            },
        ]
    )
    return response.content


def ask(llm: ChatOllama, db: SQLDatabase, question: str, max_rows: int = 200) -> dict:
    """Run the full text-to-SQL pipeline: generate SQL, validate it's
    read-only, execute it, and summarize the results in plain language.
    Returns a dict with sql/columns/rows/answer, or an 'error' key."""
    try:
        sql = generate_sql(llm, db, question, max_rows)
    except Exception as e:
        return {
            "error": (
                f"Could not reach Ollama: {e}\n\n"
                "Make sure Ollama is running (`ollama serve`) and the model "
                "in src/config.yaml has been pulled (`ollama pull <model>`)."
            )
        }

    try:
        validate_readonly_sql(sql)
    except ValueError as e:
        return {"sql": sql, "error": str(e)}

    try:
        columns, rows = execute_query(db, sql, max_rows)
    except Exception as e:
        return {"sql": sql, "error": f"Query failed: {e}"}

    try:
        answer = generate_answer(llm, question, sql, columns, rows)
    except Exception as e:
        # The query already succeeded - don't throw away sql/columns/rows
        # just because the follow-up summarization call to Ollama failed.
        return {
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "answer": None,
            "error": f"Query succeeded, but summarizing the answer failed: {e}",
        }

    return {"sql": sql, "columns": columns, "rows": rows, "answer": answer}
