#!/bin/sh
set -e

export PATH="/usr/local/searxng/.venv/bin:${PATH}"

# Fix for a startup-order bug in the stock image: `searx/__init__.py` calls
# `init_settings()` exactly once, at module import time, with no reload
# mechanism (no SIGHUP handler, no reload endpoint - confirmed by reading
# the source). The stock custom-entrypoint.sh starts SearXNG (entrypoint.sh
# -> exec granian -> imports searx -> settings loaded into memory) in the
# background, then races a *separate* python process (patch_settings.py) to
# edit settings.yml afterward. Whichever finishes importing/patching first
# wins; on a loaded machine granian's already-warm process reliably beats a
# freshly spawned python interpreter, so the patch lands on disk but is
# never read by the running process - every `format=json` request then
# gets `flask.abort(403)` in webapp.py's /search route, permanently, for
# that container's lifetime.
#
# Fix: do the same settings.yml creation + patch synchronously, before
# SearXNG's own entrypoint ever runs, so there's no window to lose. This
# keeps everything generated fresh on every container start (template copy,
# random secret_key, JSON-format patch) - nothing is baked into the image.

TEMPLATE_SETTINGS="/usr/local/searxng/settings.template.yml"
TARGET_SETTINGS="${__SEARXNG_CONFIG_PATH}/settings.yml"

if [ ! -f "$TARGET_SETTINGS" ]; then
    echo "\"$TARGET_SETTINGS\" does not exist, creating from template..." >&2
    cp -pfT "$TEMPLATE_SETTINGS" "$TARGET_SETTINGS"
    # Matches entrypoint.sh's own secret_key randomization so this stays
    # equivalent to stock behavior, not just the JSON-format piece.
    sed -i "s/ultrasecretkey/$(head -c 24 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9')/g" "$TARGET_SETTINGS"
fi

# Patch settings to enable JSON format. Guaranteed to complete before
# SearXNG's own process starts importing settings.yml, below.
python -m mcp_server.patch_settings "$TARGET_SETTINGS" >&2

# Start SearXNG. Its own entrypoint.sh will see settings.yml already
# exists and skip straight to `exec granian` - no race, no double work.
/usr/local/searxng/entrypoint.sh >&2 2>&1 &

# Wait for SearXNG to be ready (all logs to stderr)
echo "Waiting for SearXNG to start..." >&2
i=0
while [ "$i" -lt 30 ]; do
    if wget -qO /dev/null http://127.0.0.1:8080/healthz 2>/dev/null; then
        echo "SearXNG is ready." >&2
        break
    fi
    i=$((i + 1))
    if [ "$i" -eq 30 ]; then
        echo "Error: SearXNG failed to start after 30 seconds." >&2
        exit 1
    fi
    sleep 1
done

# Start MCP server
if [ "$1" = "--stdio" ]; then
    echo "Starting MCP server in stdio mode..." >&2
    exec python -m mcp_server.main --stdio
else
    echo "Starting MCP server in HTTP mode on port 8888..." >&2
    exec python -m mcp_server.main --http
fi
