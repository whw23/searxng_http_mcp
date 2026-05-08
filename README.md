# SearXNG HTTP MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Image](https://img.shields.io/badge/ghcr.io-searxng--http--mcp-blue)](https://ghcr.io/whw23/searxng-http-mcp)

A self-contained MCP server wrapping [SearXNG](https://github.com/searxng/searxng) metasearch engine. Ships as a single Docker image with built-in SearXNG — no separate instance needed.

## Features

- **Self-contained** — SearXNG built into the Docker image, one container does everything
- **Dual transport** — HTTP (Streamable HTTP) and stdio mode in one image
- **Authentication** — `x-api-key` header + HTTP Basic Auth, controlled via `API_KEY` env var
- **Reverse proxy** — SearXNG Web UI accessible through the same port for configuration
- **Multi-page fanout** — fetch up to 5 pages of results in a single tool call
- **Dynamic tool descriptions** — engine and category lists populated from live SearXNG config
- **Token-efficient** — results trimmed to essential fields
- **Claude Code Plugin** — installable via self-hosted marketplace

## Quick Start

```bash
docker run -p 8888:8888 ghcr.io/whw23/searxng-http-mcp:latest
```

That's it. SearXNG + MCP server running on port 8888.

## Architecture

```text
┌──────────────────────────────────────────────┐
│              Docker Container                │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │   Starlette App  :8888 (exposed)       │  │
│  │                                        │  │
│  │   Auth Middleware (API_KEY env var)     │  │
│  │   ├─ /mcp  → FastMCP Server            │  │
│  │   └─ /*    → Reverse Proxy (httpx) ──┐ │  │
│  └────────────────────────────────────────┘  │
│                                          │   │
│  ┌───────────────────────────────────┐   │   │
│  │  SearXNG  127.0.0.1:8080         │◄──┘   │
│  │  (internal, not exposed)          │       │
│  └───────────────────────────────────┘       │
│                                              │
│  Exposed port: 8888                          │
└──────────────────────────────────────────────┘
```

## Usage

### HTTP Mode (default)

```bash
# Without authentication
docker run -p 8888:8888 ghcr.io/whw23/searxng-http-mcp:latest

# With authentication
docker run -p 8888:8888 -e API_KEY=your-secret-key ghcr.io/whw23/searxng-http-mcp:latest
```

- MCP endpoint: `http://localhost:8888/mcp`
- SearXNG Web UI: `http://localhost:8888/`

### stdio Mode

```bash
docker run --rm -i ghcr.io/whw23/searxng-http-mcp:latest --stdio
```

No ports exposed. Communication via stdin/stdout. SearXNG runs internally for the MCP tools.

### Environment Variables

| Variable      | Default                    | Description                                |
| ------------- | -------------------------- | ------------------------------------------ |
| `API_KEY`     | *(empty, no auth)*         | API key for authentication                 |
| `SEARXNG_URL` | `http://127.0.0.1:8080`    | Internal SearXNG URL (rarely needs change) |

### Authentication

When `API_KEY` is set, all requests require one of:

- **`x-api-key` header** — for MCP clients: `x-api-key: your-key`
- **HTTP Basic Auth** — for browsers: username empty, password = API key

When `API_KEY` is not set, all requests are open.

## MCP Tools Reference

### `search`

Search the web using SearXNG. Aggregates results from multiple search engines.

| Parameter    | Type | Required | Default | Description                                              |
| ------------ | ---- | -------- | ------- | -------------------------------------------------------- |
| `query`      | str  | yes      | —       | Search query string                                      |
| `categories` | str  | no       | ""      | Comma-separated: general, images, videos, news, it, etc. |
| `language`   | str  | no       | ""      | Language code (e.g., zh, en, ja)                         |
| `time_range` | str  | no       | ""      | day, month, year                                         |
| `safesearch` | int  | no       | 0       | 0=off, 1=moderate, 2=strict                              |
| `pageno`     | int  | no       | 1       | Starting page number                                     |
| `pages`      | int  | no       | 1       | Number of pages to fetch (1-5)                           |
| `engines`    | str  | no       | ""      | Comma-separated engine names (e.g., google,bing)         |

Returns: results, answers, suggestions, corrections, infoboxes.

### `autocomplete`

Get search query suggestions.

| Parameter | Type | Required | Description                    |
| --------- | ---- | -------- | ------------------------------ |
| `query`   | str  | yes      | Query string to autocomplete   |

## Client Configuration

### Claude Desktop

**Server mode** — edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "searxng": {
      "url": "http://your-server:8888/mcp",
      "headers": {
        "x-api-key": "your-secret-key"
      }
    }
  }
}
```

**Local mode**:

```json
{
  "mcpServers": {
    "searxng": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "ghcr.io/whw23/searxng-http-mcp:latest", "--stdio"]
    }
  }
}
```

### Claude Code

**Server mode**:

```bash
claude mcp add searxng --transport http http://your-server:8888/mcp -- --header "x-api-key: your-secret-key"
```

**Local mode**:

```bash
claude mcp add searxng -- docker run --rm -i ghcr.io/whw23/searxng-http-mcp:latest --stdio
```

### Cursor

**Server mode** — add to MCP settings:

```json
{
  "mcpServers": {
    "searxng": {
      "url": "http://your-server:8888/mcp",
      "headers": {
        "x-api-key": "your-secret-key"
      }
    }
  }
}
```

**Local mode**:

```json
{
  "mcpServers": {
    "searxng": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "ghcr.io/whw23/searxng-http-mcp:latest", "--stdio"]
    }
  }
}
```

### VS Code Copilot

Same format as Cursor. Add to your MCP configuration.

### Windsurf

Same format as Cursor. Add to your MCP configuration.

### Cline

Same format as Cursor. Configure via Cline's MCP settings panel.

### Continue.dev

Same format as Cursor. Add to Continue's MCP configuration.

### OpenCode

**Server mode** — edit `.opencode.json`:

```json
{
  "mcpServers": {
    "searxng": {
      "type": "sse",
      "url": "http://your-server:8888/mcp",
      "headers": {
        "x-api-key": "your-secret-key"
      }
    }
  }
}
```

**Local mode**:

```json
{
  "mcpServers": {
    "searxng": {
      "type": "stdio",
      "command": "docker",
      "args": ["run", "--rm", "-i", "ghcr.io/whw23/searxng-http-mcp:latest", "--stdio"]
    }
  }
}
```

### Hermes Agent

**Server mode** — edit `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  searxng:
    url: "http://your-server:8888/mcp"
    headers:
      x-api-key: "your-secret-key"
```

**Local mode**:

```yaml
mcp_servers:
  searxng:
    command: "docker"
    args: ["run", "--rm", "-i", "ghcr.io/whw23/searxng-http-mcp:latest", "--stdio"]
```

## Claude Code Plugin

Install via self-hosted marketplace:

```bash
/plugin marketplace add whw23/searxng-http-mcp
/plugin install searxng-http-mcp@searxng-http-mcp
```

The plugin includes a `/search` skill for web search.

## SearXNG Configuration

### Via Web UI

Access the SearXNG Web UI at `http://localhost:8888/` to configure search engines, languages, and other settings. Changes persist during the container's lifetime.

### Via Volume Mount

Mount a custom `settings.yml` for persistent configuration:

```bash
docker run -p 8888:8888 \
  -v /path/to/your/settings.yml:/etc/searxng/settings.yml \
  ghcr.io/whw23/searxng-http-mcp:latest
```

The settings file must include `formats: [json]` under `search:` for MCP tools to work.

## Build from Source

```bash
git clone https://github.com/whw23/searxng-http-mcp.git
cd searxng-http-mcp
docker build -t searxng-http-mcp:local .
docker run -p 8888:8888 searxng-http-mcp:local
```

## Contributing

1. Fork the repository
2. Create a feature branch from `dev`
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Submit a PR to `dev`

Development happens on the `dev` branch. Merges to `main` trigger image builds.

## License

[MIT](LICENSE) — MCP server code.

SearXNG itself is licensed under [AGPL-3.0-or-later](https://github.com/searxng/searxng/blob/master/LICENSE).
