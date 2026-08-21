# Deployment

This app deploys as two containers (the Streamlit app + Ollama) via Docker
Compose, pushed to a self-hosted VPS over SSH from GitHub Actions. There is
no managed/serverless path here because Ollama needs a machine with enough
RAM to hold the model resident — see `docs/ARCHITECTURE.md` for why.

## Branch -> environment mapping

**`main` is prod.** There is no separate `prod` branch — `main` already
means "what's live" on GitHub by convention, so a second branch claiming
the same thing would just be a second source of truth waiting to drift
from the first. `dev` and `qa` are the only branches added on top of it.

| Branch | GitHub Environment | Typical use |
|---|---|---|
| `dev`  | `dev`  | Every push auto-deploys. Break things here. |
| `qa`   | `qa`   | Every push auto-deploys once CI passes. No review gate. |
| `main` | `prod` | Every push auto-deploys once CI passes. No review gate by default (see below if you want one later). |

Pushing to any of these three branches triggers `.github/workflows/deploy.yml`,
which runs the full CI suite (`ci.yml`) first, then builds and pushes a
Docker image to GHCR and SSHes into the matching environment's server to
redeploy. If CI fails, nothing gets built or deployed — that's the only
gate; there's no PR review or manual approval step anywhere by default.
The workflow maps `main` -> the `prod` GitHub Environment (and image tag
`:prod`) explicitly, since the branch name and the environment name
intentionally differ here.

## One-time setup (you do this, not me)

### 1. Provision a VPS per environment (or one VPS, three separate deploy paths)

Any Linux box with Docker + Docker Compose installed and enough RAM for
whichever Ollama model you're running (9-10GB free RAM minimum for `gemma4`;
more for anything bigger — see the model-sizing note in `README.md`).

On each server:

```bash
mkdir -p ~/llmtexttosql-<env>   # e.g. ~/llmtexttosql-dev
cd ~/llmtexttosql-<env>
# copy docker-compose.yml from the repo here (scp it once, or `git clone` a
# shallow copy) - the deploy job only needs `docker-compose.yml` present in
# $DEPLOY_PATH, it doesn't check out the rest of the repo on the server.
```

### 2. Create GitHub Environments and secrets

Repo Settings > Environments > New environment, once each for `dev`, `qa`,
`prod` (yes, `prod` — even though the branch that deploys to it is `main`).
In each one, add these **secrets**:

| Secret | Value |
|---|---|
| `SSH_HOST` | server IP/hostname for this environment |
| `SSH_USER` | SSH user with docker permissions |
| `SSH_KEY` | private key for that user (generate a deploy-only key, don't reuse your personal one) |
| `DEPLOY_PATH` | e.g. `/home/deploy/llmtexttosql-dev` |
| `APP_PORT` | host port to expose Streamlit on, e.g. `8501` |

And optionally this **variable** (not secret):

| Variable | Value |
|---|---|
| `OLLAMA_MODEL` | model to auto-pull after deploy, e.g. `gemma4:latest`. Defaults to `gemma4:latest` if unset. |

### 3. Enable branch protection / required status checks

Run `scripts/setup-branch-protection.sh <owner>/<repo>` from a machine with
`gh` authenticated as a repo admin. It requires the `Lint & test` and
`Docker image builds` CI jobs to pass before anything lands on dev/qa/main
— no PR review requirement, no human approval anywhere. Direct pushes are
allowed as long as CI is green. See the script itself for exactly what it
sets and what you still have to do by hand (Environments aren't settable
via the branch-protection API).

### 4. (Optional) Add a manual approval gate on prod later

Not set up by default, since nobody's signed up to be the reviewer. If you
ever want one: Repo Settings > Environments > `prod` > **Required
reviewers** — GitHub will then pause the `deploy` job on every push to
`main` until someone approves it in the Actions UI.

## Promotion flow

```
dev   → push, CI required, auto-deploys
qa    → push, CI required, auto-deploys, no review
main  → push, CI required, auto-deploys, no review  (= prod)
```

There's no PR-and-wait-for-approval step baked in anywhere — CI passing is
the only thing standing between a push and a live deploy, on every branch.

## First deploy / redeploy manually

If you ever need to deploy without pushing (e.g. first-time setup, or the
image already exists and you just want to restart), SSH in and run:

```bash
cd $DEPLOY_PATH
export IMAGE=ghcr.io/<owner>/<repo>
export IMAGE_TAG=<dev|qa|prod>
export APP_PORT=8501
docker compose pull app
docker compose up -d
docker compose exec ollama ollama pull gemma4:latest
```

## Rollback

Redeploy the previous image tag:

```bash
docker pull ghcr.io/<owner>/<repo>:<previous-sha-or-tag>
docker tag ghcr.io/<owner>/<repo>:<previous-sha-or-tag> ghcr.io/<owner>/<repo>:<env>
docker compose up -d
```

GHCR keeps every pushed tag by default; tag deploys by commit SHA as well as
branch name if you want fine-grained rollback targets (not set up by
default here — `deploy.yml` currently only tags by branch name).
