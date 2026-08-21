#!/usr/bin/env bash
# One-time setup script - run this YOURSELF from a machine with `gh` CLI
# installed and authenticated (`gh auth login`) with admin rights on the
# repo. This is NOT executed automatically by any pipeline; it configures
# GitHub repo settings (branch protection) that only a repo admin can set.
#
# What this does:
#   - Requires the CI workflow's two jobs (lint-and-test, docker-build) to
#     pass before anything lands on dev/qa/main. That's the only gate -
#     no PR review requirement, no human approval. Pushing directly (or
#     merging a PR with zero reviews) is allowed as long as CI is green.
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

  echo "-> $branch (CI required, no review requirement)"

  gh api \
    --method PUT \
    -H "Accept: application/vnd.github+json" \
    "repos/${REPO}/branches/${branch}/protection" \
    -f "required_status_checks[strict]=true" \
    -f "required_status_checks[checks][][context]=Lint & test" \
    -f "required_status_checks[checks][][context]=Docker image builds" \
    -f "enforce_admins=false" \
    -f "required_pull_request_reviews=null" \
    -f "restrictions=null" \
    -f "required_linear_history=true" \
    -f "allow_force_pushes=false" \
    -f "allow_deletions=false"
}

protect_branch "dev"
protect_branch "qa"
protect_branch "main"  # main IS prod - there is no separate prod branch

echo
echo "Done. Verify at: https://github.com/${REPO}/settings/branches"
echo
echo "Still needed (branch protection can't set these via this API call):"
echo "  1. Settings > Environments > create 'dev', 'qa', 'prod', each with"
echo "     secrets: SSH_HOST, SSH_USER, SSH_KEY, DEPLOY_PATH, APP_PORT"
echo "     (and optional var: OLLAMA_MODEL). The 'prod' Environment is used"
echo "     when deploying the 'main' branch - deploy.yml maps main->prod."
echo "  2. No required-reviewer gate is set on the 'prod' Environment by"
echo "     default here - deploys to main run unattended once CI passes,"
echo "     same as dev/qa. Add one yourself under Settings > Environments >"
echo "     prod > Required reviewers only if you later want a manual"
echo "     approval step before production deploys."
