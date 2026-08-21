import re

import yaml

_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<sql>\s*(.*?)\s*</sql>", re.IGNORECASE | re.DOTALL)

_WRITE_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "REPLACE", "GRANT", "REVOKE", "ATTACH", "DETACH",
    "PRAGMA", "VACUUM",
)


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def extract_sql(text: str) -> str:
    """Pull a bare SQL statement out of a model response that may be wrapped
    in ```sql fences or <sql> tags, or may already be bare."""
    match = _TAG_RE.search(text)
    if match:
        return match.group(1).strip().rstrip(";")
    match = _SQL_FENCE_RE.search(text)
    if match:
        return match.group(1).strip().rstrip(";")
    return text.strip().rstrip(";")


def validate_readonly_sql(sql: str) -> None:
    """Raise ValueError unless `sql` is a single read-only SELECT/WITH statement.

    This is a pragmatic guardrail against an LLM emitting destructive SQL,
    not a substitute for running the app against a least-privilege DB user.
    """
    if not sql or not sql.strip():
        raise ValueError("Model did not return a SQL query.")

    if ";" in sql.strip().rstrip(";"):
        raise ValueError("Only a single SQL statement is allowed.")

    stripped = sql.strip()
    if not re.match(r"^(SELECT|WITH)\b", stripped, re.IGNORECASE):
        raise ValueError(
            "Only read-only SELECT queries are allowed. "
            f"Generated query did not start with SELECT/WITH: {stripped[:80]}"
        )

    for keyword in _WRITE_KEYWORDS:
        if re.search(rf"\b{keyword}\b", stripped, re.IGNORECASE):
            raise ValueError(f"Query contains disallowed keyword: {keyword}")
