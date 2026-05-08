#!/bin/sh
set -e

export PATH="/usr/local/searxng/.venv/bin:${PATH}"

# Ensure JSON format is enabled in SearXNG settings.
ensure_json_format() {
    settings="/etc/searxng/settings.yml"
    i=0
    while [ ! -f "$settings" ] && [ "$i" -lt 10 ]; do
        sleep 1
        i=$((i + 1))
    done
    python -m mcp_server.patch_settings "$settings"
}

# Start SearXNG in the background, redirect all output to stderr
/usr/local/searxng/entrypoint.sh >&2 2>&1 &

# Patch settings to enable JSON format
ensure_json_format >&2

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
        echo "Warning: SearXNG health check timed out, starting MCP server anyway." >&2
    fi
    sleep 1
done

# Start MCP server
if [ "$1" = "--stdio" ]; then
    echo "Starting MCP server in stdio mode..." >&2
    exec python -m mcp_server.main --stdio
else
    echo "Starting MCP server in HTTP mode on port 8888..." >&2
    exec python -m mcp_server.main
fi
