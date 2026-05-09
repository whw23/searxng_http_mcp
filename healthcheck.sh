#!/bin/sh
# Check SearXNG (always required)
wget -qO /dev/null http://127.0.0.1:8080/healthz || exit 1

# In remote/HTTP mode, also verify MCP server on port 8888.
# In stdio mode, port 8888 is not open — skip gracefully.
if nc -z 127.0.0.1 8888 2>/dev/null; then
    # Port is open (remote mode) — verify MCP responds
    wget -qO /dev/null --timeout=3 http://127.0.0.1:8888/mcp/ 2>/dev/null || exit 1
fi
