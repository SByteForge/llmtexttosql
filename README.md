# Text to SQL Application

## Overview

A **Text to SQL** Streamlit app that converts natural-language questions into
SQL, runs them against a database, and answers in plain language. It uses a
local LLM via [Ollama](https://ollama.com) (via LangChain) to generate the
SQL and summarize the results — free, runs entirely on your machine, no API
key required.

## Features

- Convert natural language questions into SQL
- Execute the generated SQL and display the results as a table
- Get a plain-language answer summarizing the results
- Guardrail that only allows read-only `SELECT`/`WITH` queries — the app
  refuses to run anything that would modify data or schema
- Works out of the box against a bundled SQLite demo database (a small
  customers/products/orders/order_items schema); switch to a real MySQL
  database via `.env` when you're ready

## Folder Structure

- `src/`
  - `main.py` — Streamlit entry point / UI
  - `database.py` — DB connection (SQLite demo DB or MySQL) and query execution
  - `llm.py` — Ollama-powered SQL generation + answer summarization
  - `utils.py` — SQL extraction/validation helpers, config loader
  - `config.yaml` — non-secret app settings (model name, row limits, etc.)
  - `data/` — bundled SQLite demo database (auto-created on first run)
- `tests/` — pytest suite (`ci.yml` runs this on every push/PR)
- `.github/workflows/` — CI (`ci.yml`) and deploy (`deploy.yml`) pipelines
- `docs/ARCHITECTURE.md` — component diagram, request trace, CI/CD flow
- `docs/DEPLOYMENT.md` — environment setup, branch protection, rollback
- `Dockerfile`, `docker-compose.yml` — app + Ollama containers
- `requirements.txt` — pinned dependencies
- `.env.example` — template for required environment variables

## Development, CI/CD, and deployment

Three long-lived branches — `dev` → `qa` → `main` — each map to their own
deployed environment (`dev`/`qa`/`prod`) and are protected by required CI
checks. `main` is prod; there is no separate `prod` branch. See
`docs/DEPLOYMENT.md` for the full promotion flow, required secrets, and
branch protection setup. Full architecture — what runs where, how the
pieces talk to each other — is in `docs/ARCHITECTURE.md`.

Run the tests and linter locally the same way CI does:

```bash
pip install -r requirements-dev.txt
ruff check src tests
pytest
```

Run the whole stack (app + Ollama) in Docker instead of a local venv:

```bash
docker compose up -d
docker compose exec ollama ollama pull gemma4
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/SByteForge/llmtexttosql.git
   cd llmtexttosql
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Install [Ollama](https://ollama.com), start it, and pull a model:
   ```bash
   ollama serve            # if it isn't already running
   ollama pull mistral     # or whichever model you set in src/config.yaml
   ```

4. Configure your environment:
   ```bash
   cp .env.example .env
   ```
   The defaults work as-is — `DB_TYPE=sqlite` needs no setup (a demo
   database is created automatically on first run), and Ollama is assumed to
   be running on `localhost:11434`.

5. Run the app:
   ```bash
   streamlit run src/main.py
   ```

## Using a real MySQL database

Set the following in `.env`:

```
DB_TYPE=mysql
DB_HOST=your-host
DB_PORT=3306
DB_USER=your-user
DB_PASSWORD=your-password
DB_NAME=your-database
```

Use a **read-only** MySQL user for this app. The app validates that
generated SQL is a single `SELECT`/`WITH` statement before running it, but a
least-privilege DB user is the real safety net — don't rely on the
application-layer check alone.

## Configuration

Non-secret settings live in `src/config.yaml`:

- `llm.model` — Ollama model to use (default `gemma4:latest`). Any model
  you've pulled works — just set `llm.model` to its name (`ollama list`
  shows what you have locally, `ollama pull <model>` gets more).
- `llm.base_url` — where Ollama is listening (default `http://localhost:11434`;
  override with the `OLLAMA_BASE_URL` env var if it runs elsewhere)
- `database.max_result_rows` — cap on rows returned per query
- `database.sample_rows_in_table_info` — how many sample rows of each table
  to show the model when generating SQL

### A note on model quality

Small local models are noticeably weaker at SQL generation than frontier
hosted models — expect more retries and occasional malformed queries,
especially on multi-table joins. The app's read-only guardrail (only
`SELECT`/`WITH`, single statement, no destructive keywords) still applies
regardless of which model you use.
