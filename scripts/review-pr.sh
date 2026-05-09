#!/usr/bin/env bash
# Safely test a PR's code in an isolated Docker container.
# Usage: ./scripts/review-pr.sh <PR_NUMBER>
#
# - Network only during pip install, disabled for tests
# - No access to host credentials
# - Read-only source mount
# - Disposable container (--rm)

set -uo pipefail

PR_NUMBER="${1:?Usage: $0 <PR_NUMBER>}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKDIR="/tmp/pr-review-$$"
ORIGINAL_REF="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || git rev-parse HEAD)"
EXIT_CODE=0

cleanup() {
    echo "==> Cleaning up..."
    rm -rf "$WORKDIR"
    git checkout "$ORIGINAL_REF" 2>/dev/null
}
trap cleanup EXIT

echo "==> Fetching PR #$PR_NUMBER..."
gh pr checkout "$PR_NUMBER" --detach

echo "==> Copying source to temp directory..."
mkdir -p "$WORKDIR"
git diff main...HEAD --stat
cp -r "$REPO_ROOT" "$WORKDIR/src"

echo "==> Installing dependencies (network enabled)..."
docker run --rm \
    --memory 512m \
    --cpus 1 \
    -v "$WORKDIR/src:/app:ro" \
    -v "$WORKDIR/deps:/deps" \
    python:3.14-slim \
    pip install --quiet --target /deps "mcp[cli]" pytest pytest-anyio httpx pytest-cov pyyaml

echo "==> Running tests (network disabled)..."
docker run --rm \
    --network none \
    --memory 512m \
    --cpus 1 \
    --read-only \
    --tmpfs /tmp:rw,nosuid \
    -v "$WORKDIR/src:/app:ro" \
    -v "$WORKDIR/deps:/deps:ro" \
    -w /app \
    -e PYTHONPATH=/deps \
    python:3.14-slim \
    python -m pytest tests/ -v --tb=short || EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "==> Tests PASSED"
else
    echo "==> Tests FAILED (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
