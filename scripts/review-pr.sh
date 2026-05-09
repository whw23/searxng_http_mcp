#!/usr/bin/env bash
# Safely test a PR's code in an isolated Docker container.
# Usage: ./scripts/review-pr.sh <PR_NUMBER>
#
# - No network access (--network none)
# - No access to host credentials
# - Read-only source mount
# - Disposable container (--rm)

set -euo pipefail

PR_NUMBER="${1:?Usage: $0 <PR_NUMBER>}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKDIR="/tmp/pr-review-$$"

echo "==> Fetching PR #$PR_NUMBER..."
gh pr checkout "$PR_NUMBER" --detach

echo "==> Copying source to temp directory (read-only mount source)..."
mkdir -p "$WORKDIR"
git diff main...HEAD --stat
cp -r "$REPO_ROOT" "$WORKDIR/src"

echo "==> Running tests in isolated Docker container..."
docker run --rm \
    --network none \
    --memory 512m \
    --cpus 1 \
    --read-only \
    --tmpfs /tmp:rw,nosuid \
    -v "$WORKDIR/src:/app:ro" \
    -w /app \
    python:3.14-slim \
    sh -c '
        pip install --quiet --target /tmp/deps "mcp[cli]" pytest pytest-anyio httpx pytest-cov pyyaml 2>/dev/null
        PYTHONPATH=/tmp/deps python -m pytest tests/ -v --tb=short
    '

EXIT_CODE=$?

echo "==> Cleaning up..."
rm -rf "$WORKDIR"
git checkout dev

if [ $EXIT_CODE -eq 0 ]; then
    echo "==> Tests PASSED"
else
    echo "==> Tests FAILED (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
