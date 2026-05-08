#!/bin/bash
set -e

# Start SearXNG in the background using the original entrypoint
/usr/local/searxng/entrypoint.sh &

# Wait for SearXNG to be ready
echo "Waiting for SearXNG to start..."
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8080/healthz > /dev/null 2>&1; then
        echo "SearXNG is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "Warning: SearXNG health check timed out, starting MCP server anyway."
    fi
    sleep 1
done

# Start MCP server
if [ "$1" = "--stdio" ]; then
    echo "Starting MCP server in stdio mode..." >&2
    exec python -m mcp_server.main --stdio
else
    echo "Starting MCP server in HTTP mode on port 8888..."
    exec python -m mcp_server.main
fi
