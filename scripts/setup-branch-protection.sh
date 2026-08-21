#!/usr/bin/env bash
# One-time setup script - run this YOURSELF from a machine with `gh` CLI
# installed and authenticated (`gh auth login`) with admin rights on the
# repo. This is NOT executed automatically by any pipeline; it configures
# GitHub repo settings (branch protection) that only a repo admin can set.
#
# What this does:
#   - Requires the CI workflow's two jobs (lint-and-test, docker-build) to
#     pass before a PR can merge into dev/qa/main.
#   - Requires at least 1 PR approval before merging into qa/main. `main`
#     IS prod - there is no separate `prod` branch, so this is the gate
#     for what ships live.
#   - Requires branches to be up to date with the base branch before merge.
#
# Usage:
#   chmod +x scripts/setup-branch-protection.sh
#   ./scripts/setup-branch-protection.sh SByteForge/llmtexttosql

set -euo pipefail

REPO="${1:?Usage: $0 <owner>/<repo>, e.g. SByteForge/llmtexttosql}"

echo "Configuring branch protection on $REPO ..."

protect_branch() {
  local branch="$1"
  local required_approvals="$2"

  echo "-> $branch (require $required_approvals approval(s))"

  gh api \
    --method PUT \
    -H "Accept: application/vnd.github+json" \
    "repos/${REPO}/branches/${branch}/protection" \
    -f "required_status_checks[strict]=true" \
    -f "required_status_checks[checks][][context]=Lint & test" \
    -f "required_status_checks[checks][][context]=Docker image builds" \
    -f "enforce_admins=false" \
    -f "required_pull_request_reviews[required_approving_review_count]=${required_approvals}" \
    -f "restrictions=null" \
    -f "required_linear_history=true" \
    -f "allow_force_pushes=false" \
    -f "allow_deletions=false"
}

# dev: CI must pass, no review requirement (fast iteration)
protect_branch "dev" 0

# qa: CI must pass + 1 reviewer
protect_branch "qa" 1

# main (= prod): CI must pass + 1 reviewer. Combine this with a
# required-reviewer rule on the "prod" GitHub Environment (Settings >
# Environments > prod > Required reviewers) for a second, deploy-time
# approval gate - branch protection alone only gates the merge, not the
# deploy job itself.
protect_branch "main" 1

echo
echo "Done. Verify at: https://github.com/${REPO}/settings/branches"
echo
echo "Still needed (branch protection can't set these via this API call):"
echo "  1. Settings > Environments > create 'dev', 'qa', 'prod', each with"
echo "     secrets: SSH_HOST, SSH_USER, SSH_KEY, DEPLOY_PATH, APP_PORT"
echo "     (and optional var: OLLAMA_MODEL). The 'prod' Environment is used"
echo "     when deploying the 'main' branch - deploy.yml maps main->prod."
echo "  2. Settings > Environments > prod > Required reviewers - add"
echo "     yourself/teammates so every prod deploy needs manual approval"
echo "     in addition to the CI checks and PR review."
