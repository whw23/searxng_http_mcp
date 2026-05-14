#!/bin/sh
set -e

# Start SearXNG Flask dev server in background (logs to stderr for diagnostics)
SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml .venv/bin/python -m searx.webapp >&2 2>&1 &

# Wait for SearXNG to be ready
i=0
while [ "$i" -lt 30 ]; do
    if wget -qO /dev/null http://127.0.0.1:8080/ 2>/dev/null; then
        echo "SearXNG is ready." >&2
        break
    fi
    i=$((i + 1))
    sleep 1
done

if [ "$i" -eq 30 ]; then
    echo "SearXNG failed to start after 30 seconds." >&2
    exit 1
fi

# Start MCP server in stdio mode
exec .venv/bin/python -m mcp_server.main --stdio
