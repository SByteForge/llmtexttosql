# Architecture

## Runtime: what sits where, per environment

Each environment (`dev`/`qa`/`prod`) is its own VPS running two containers
via Docker Compose. Nothing is shared between environments except the
container image (same image, different tag, promoted branch by branch).
The `prod` environment is deployed from the `main` branch — there is no
separate `prod` branch (see the CI/CD section below for why).

```mermaid
flowchart TB
    subgraph client["Client"]
        Browser["Browser"]
    end

    subgraph vps["VPS (one per environment: dev / qa / prod)"]
        subgraph appc["app container"]
            Streamlit["Streamlit process\nmain.py"]
            LLMmod["llm.py"]
            DBmod["database.py"]
            Utils["utils.py"]
            Streamlit --> LLMmod
            Streamlit --> DBmod
            LLMmod --> Utils
        end

        subgraph ollamac["ollama container"]
            OllamaServer["Ollama server\n:11434"]
            Weights[("model weights\nvolume: ollama_data")]
            OllamaServer --- Weights
        end

        SQLite[("SQLite file\nvolume: app_data")]
        DBmod -- "file I/O" --> SQLite
        LLMmod -- "HTTP POST /api/chat" --> OllamaServer
    end

    subgraph externaldb["Optional: external MySQL"]
        MySQL[("MySQL server")]
    end

    Browser -- "HTTP :APP_PORT" --> Streamlit
    DBmod -. "TCP, if DB_TYPE=mysql" .-> MySQL

    style appc fill:#1e293b,color:#fff
    style ollamac fill:#1e293b,color:#fff
    style vps fill:#0f172a,color:#fff
```

**Key point:** the app process never touches the model directly — it only
speaks HTTP to Ollama, which owns loading/unloading weights into RAM/VRAM.
That's why memory pressure on the box (see the "system running slow"
incident during development) is invisible to the app's own error handling;
it only surfaces as a slow or failed HTTP call.

## One question, stage by stage

```mermaid
sequenceDiagram
    participant U as Browser
    participant S as Streamlit (main.py)
    participant L as llm.py
    participant O as Ollama server
    participant D as database.py / DB

    U->>S: Submit question
    S->>L: ask(llm, db, question)
    L->>O: POST /api/chat (generate SQL)
    O-->>L: SQL text
    L->>L: extract_sql() + validate_readonly_sql()
    alt validation fails
        L-->>S: error (no query run)
    else valid SELECT/WITH
        L->>D: execute_query(sql)
        D-->>L: columns, rows
        L->>O: POST /api/chat (summarize results)
        O-->>L: plain-language answer
        L-->>S: sql, columns, rows, answer
    end
    S-->>U: render answer + table + SQL
```

Failure containment (see conversation history for the full breakdown):
generate-SQL failures, validation failures, query failures, and
generate-answer failures are each caught independently in `ask()` — a
failure at any later stage doesn't throw away results already computed at
an earlier stage.

## CI/CD pipeline

```mermaid
flowchart LR
    subgraph promote["Promotion flow - CI-gated, no review required"]
        direction LR
        Feature["feature branch"] -->|push, CI required| Dev["dev"]
        Dev -->|push, CI required| QA["qa"]
        QA -->|push, CI required| Main["main (= prod)"]
    end

    Dev -.push.-> CID["CI: lint, test,\ndocker build"]
    QA -.push.-> CIQ["CI: lint, test,\ndocker build"]
    Main -.push.-> CIP["CI: lint, test,\ndocker build"]

    CID -->|pass| DeployD["Deploy job\nenv: dev secrets"]
    CIQ -->|pass| DeployQ["Deploy job\nenv: qa secrets"]
    CIP -->|pass| DeployP["Deploy job\nenv: prod secrets\n(main -> prod)"]

    DeployD --> GHCR[("ghcr.io image:dev")]
    DeployQ --> GHCR2[("ghcr.io image:qa")]
    DeployP --> GHCR3[("ghcr.io image:prod")]

    GHCR --> VPSD["dev VPS\ndocker compose up"]
    GHCR2 --> VPSQ["qa VPS\ndocker compose up"]
    GHCR3 --> VPSP["prod VPS\ndocker compose up"]
```

**There is no separate `prod` branch — `main` is prod.** A standalone
`prod` branch alongside `main` would just be a second "this is what's
live" claim that can silently drift from the first; `main` already carries
that meaning by GitHub convention, so the pipeline builds on it instead of
duplicating it.

**No human approval gate anywhere, by design.** CI passing is the only
thing standing between a push and a live deploy on every branch, including
`main`. A push straight to `main` deploys straight to prod once
`lint-and-test` and `docker-build` are green — there's no PR review
requirement and no required-reviewer approval on the `prod` Environment.
That's a deliberate trade-off for a solo/small-team setup where nobody's
signed up to be the reviewer; `docs/DEPLOYMENT.md` notes how to add a
manual approval gate later if that changes.

Every push to `dev`/`qa`/`main` re-runs the same `ci.yml` checks
(`lint-and-test`, `docker-build`) via `workflow_call` before `deploy.yml`'s
`deploy` job is allowed to run — so "passed CI" means the identical thing
whether it happened via a PR or a direct push. The `deploy` job resolves
`main` → the `prod` GitHub Environment explicitly (branch name and
environment name differ on purpose here); `dev`/`qa` map straight through.
That environment binding is what scopes secrets per-branch — see
`docs/DEPLOYMENT.md` for the exact GitHub settings.

## Where each piece sits (component inventory)

| Component | Process/artifact | Lives in | Talks to |
|---|---|---|---|
| Browser | client process | user's machine | Streamlit, over HTTP/WS |
| Streamlit + `main.py`/`llm.py`/`database.py`/`utils.py` | one Docker container (`app`) | VPS, per environment | Ollama (HTTP), SQLite (file) or MySQL (TCP) |
| Ollama server | one Docker container (`ollama`) | VPS, per environment | model weights on its own volume |
| SQLite demo DB | file on a named volume (`app_data`) | same VPS, mounted into `app` container | — |
| MySQL (optional) | separate DB server, not managed by this repo | wherever `DB_HOST` points | `app` container over TCP |
| GitHub Actions runners | ephemeral, GitHub-hosted | GitHub's infra | GHCR (push), VPS (SSH) |
| GHCR image registry | GitHub-hosted | GitHub's infra | pulled by each VPS on deploy |
