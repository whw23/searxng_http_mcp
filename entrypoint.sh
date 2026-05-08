#!/bin/sh
set -e

export PATH="/usr/local/searxng/.venv/bin:${PATH}"

# Start SearXNG in the background, redirect all output to stderr
/usr/local/searxng/entrypoint.sh >&2 2>&1 &

# Wait for SearXNG to be ready (all logs to stderr)
echo "Waiting for SearXNG to start..." >&2
i=0
while [ "$i" -lt 30 ]; do
    if curl -sf http://127.0.0.1:8080/healthz > /dev/null 2>&1; then
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
