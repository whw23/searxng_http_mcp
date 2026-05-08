---
name: setup
description: Configure SearXNG MCP server connection mode. Use when the user wants to set up, configure, switch between local Docker mode and remote server mode, or update the SearXNG MCP connection settings.
---

# SearXNG MCP Setup

Configure how Claude connects to the SearXNG MCP server.

## Process

Ask the user which mode they want using AskUserQuestion:

<question>
Which mode would you like to use for SearXNG MCP?

- **Local mode (Docker)** — Runs SearXNG in a local Docker container via stdio. No server needed, works offline. Requires Docker installed.
- **Server mode (Remote)** — Connects to a remote SearXNG MCP server via HTTP. Requires a running server URL.
</question>

## Local Mode

If the user chooses Local mode, run:

```bash
claude mcp remove searxng 2>/dev/null
claude mcp add searxng -- docker run --rm -i --memory=512m --cpus=1 ghcr.io/whw23/searxng-http-mcp:latest --stdio
```

Then confirm: "SearXNG MCP configured in **local mode**. Docker will run SearXNG locally via stdio."

## Server Mode

If the user chooses Server mode:

1. Ask for the server URL (e.g., `http://your-server:8888/mcp/`)
2. Ask if authentication is needed
3. If yes, ask for the API key

Then run:

```bash
# Without auth
claude mcp remove searxng 2>/dev/null
claude mcp add searxng --transport http <URL>

# With auth
claude mcp remove searxng 2>/dev/null
claude mcp add searxng --transport http <URL> -- --header "x-api-key: <API_KEY>"
```

Then confirm: "SearXNG MCP configured in **server mode** pointing to `<URL>`."
