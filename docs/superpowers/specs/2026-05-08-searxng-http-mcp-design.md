# SearXNG HTTP MCP Server — Design Spec

## Overview

An HTTP MCP server that wraps a SearXNG instance, packaged as a single Docker container based on the official SearXNG image. Exposes search capabilities to Claude and other MCP clients via Streamable HTTP and stdio, while preserving full SearXNG Web UI access through a unified reverse proxy with authentication.

**License:** MIT (MCP Server code). SearXNG itself remains AGPL-3.0-or-later.

**Repository:** `github.com/whw23/searxng-http-mcp`

**Image:** `ghcr.io/whw23/searxng-http-mcp`

## Competitive Advantages

Compared to existing solutions (mcp-searxng, searxng-mcp, searxng-deepdive):

- **Self-contained** — SearXNG built into the container, no separate instance needed
- **Auth support** — `x-api-key` + HTTP Basic Auth, competitors have none
- **Dual transport** — HTTP and stdio in one image
- **Dynamic tool descriptions** — engine/category lists populated from live SearXNG config
- **Multi-page fanout** — fetch multiple pages in a single tool call
- **Claude Code Plugin** — installable via marketplace

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

### Components

- **SearXNG**: Runs internally on `127.0.0.1:8080` with default Granian config. Not directly exposed.
- **Starlette App**: Single entry point on port `8888`. Routes `/mcp` to FastMCP, reverse proxies everything else to SearXNG via httpx.
- **Auth Middleware**: Global `x-api-key` header + HTTP Basic Auth support. Controlled by `API_KEY` environment variable. No env var = no auth.

### Communication Flow

1. Client request → Starlette `:8888`
2. Auth middleware validates credentials
3. `/mcp` requests → FastMCP handles MCP protocol (initialize, tools/list, tools/call)
4. All other requests → httpx reverse proxy → SearXNG `:8080`
5. MCP tools internally call `http://127.0.0.1:8080/search?format=json`

## Authentication

### Mechanism

Dual-mode authentication via a single `API_KEY` environment variable:

- **x-api-key header**: `x-api-key: <API_KEY>` — for MCP clients and programmatic access
- **HTTP Basic Auth**: `Authorization: Basic base64(:<API_KEY>)` — for browsers (username empty, password = API_KEY)

### Behavior

- `API_KEY` env var set → all requests require authentication
- `API_KEY` env var not set → no authentication, open access

### Middleware Logic

```text
1. If API_KEY not configured → pass through
2. Check x-api-key header → compare with API_KEY
3. Check Authorization header:
   a. If "Basic <base64>" → decode, extract password, compare with API_KEY
4. No valid credentials → 401 Unauthorized (with WWW-Authenticate: Basic)
```

## MCP Tools

### Dynamic Tool Descriptions

On startup, the MCP server queries SearXNG's internal API to discover available engines and categories. These are dynamically injected into the `search` tool's parameter descriptions, so Claude always knows what's available on the current instance.

### Tool 1: `search`

Performs a web search via SearXNG.

| Parameter    | Type | Required | Default | Description                                                                                  |
| ------------ | ---- | -------- | ------- | -------------------------------------------------------------------------------------------- |
| `query`      | str  | yes      | —       | Search query string                                                                          |
| `categories` | str  | no       | ""      | Comma-separated: general, images, videos, news, map, music, it, science, files, social_media |
| `language`   | str  | no       | ""      | Language code (e.g., zh, en, ja)                                                             |
| `time_range` | str  | no       | ""      | day, month, year                                                                             |
| `safesearch` | int  | no       | 0       | 0=off, 1=moderate, 2=strict                                                                  |
| `pageno`     | int  | no       | 1       | Starting page number                                                                         |
| `pages`      | int  | no       | 1       | Number of pages to fetch (1-5), enables multi-page fanout                                    |
| `engines`    | str  | no       | ""      | Comma-separated engine names (e.g., google,bing)                                             |

Internal call: `GET http://127.0.0.1:8080/search?q=<query>&format=json&...`

When `pages` > 1, the server concurrently requests multiple pages and merges the results.

Returns structured results including: results, answers, corrections, suggestions, infoboxes. Results are trimmed to essential fields to reduce token consumption.

### Tool 2: `autocomplete`

Provides search query suggestions.

| Parameter | Type | Required | Description                |
| --------- | ---- | -------- | -------------------------- |
| `query`   | str  | yes      | Query string to autocomplete |

Internal call: `GET http://127.0.0.1:8080/autocomplete?q=<query>`

## Docker

### Base Image

`ghcr.io/searxng/searxng:latest`

### Dockerfile

```dockerfile
FROM ghcr.io/searxng/searxng:latest

# Install MCP Server dependencies
RUN pip install mcp[cli]

# Copy MCP Server code
COPY mcp_server/ /usr/local/searxng/mcp_server/

# Copy SearXNG config (enable JSON format)
COPY config/settings.yml /etc/searxng/settings.yml

# Copy custom entrypoint
COPY entrypoint.sh /usr/local/searxng/custom-entrypoint.sh

EXPOSE 8888

ENTRYPOINT ["/usr/local/searxng/custom-entrypoint.sh"]
```

### Entrypoint Script

Accepts a `--stdio` flag to select transport mode:

- **No flag (default)**: Start SearXNG (background) + Starlette app on port 8888
- **`--stdio`**: Start SearXNG (background) + MCP server on stdin/stdout

### SearXNG Configuration

`settings.yml` must enable JSON format output:

```yaml
search:
  formats:
    - json
```

### Running

Two transport modes supported:

```bash
# HTTP mode (default) — no auth
docker run -p 8888:8888 ghcr.io/whw23/searxng-http-mcp:latest

# HTTP mode — with auth
docker run -p 8888:8888 -e API_KEY=your-secret-key ghcr.io/whw23/searxng-http-mcp:latest

# stdio mode — for local use with Claude Desktop / Claude Code
docker run --rm -i ghcr.io/whw23/searxng-http-mcp:latest --stdio
```

### Transport Modes

| Mode  | Entrypoint behavior                                 | Ports | Auth             |
| ----- | --------------------------------------------------- | ----- | ---------------- |
| HTTP  | Start SearXNG + Starlette app (reverse proxy + MCP) | 8888  | Yes (API_KEY)    |
| stdio | Start SearXNG + MCP server on stdin/stdout          | None  | No               |

In stdio mode, SearXNG still runs internally on port 8080 for the MCP tools to call. No Starlette app, no reverse proxy, no auth — communication happens entirely via stdin/stdout.

## Claude Code Plugin

### Distribution

Self-hosted marketplace in the same repository. Users install via:

```bash
/plugin marketplace add whw23/searxng-http-mcp
/plugin install searxng-http-mcp@searxng-http-mcp
```

### Plugin Contents

- **MCP server configuration** — auto-connects to the SearXNG MCP server
- **Skills** — search-related skills (e.g., `/search` command)
- **Marketplace metadata** — `.claude-plugin/marketplace.json`

### Plugin Structure

```text
.claude-plugin/
├── plugin.json
└── marketplace.json
skills/
└── search/
    └── SKILL.md
```

## CI/CD — GitHub Actions

### Triggers

- **push** to `main` (includes PR merges)
- **schedule**: daily cron

All triggers build only from the `main` branch.

### Build & Push Workflow

1. Pull `ghcr.io/searxng/searxng:latest`, extract upstream version tag (e.g., `2026.5.7-ef6290c8c`)
2. Build our image
3. Tag as:
   - `ghcr.io/whw23/searxng-http-mcp:<upstream-version>-<our-git-hash>` (e.g., `2026.5.7-ef6290c8c-a1b2c3d`)
   - `ghcr.io/whw23/searxng-http-mcp:latest`
4. Push to GHCR
5. Publish to MCP Registry via GitHub OIDC (namespace: `io.github.whw23/searxng-http-mcp`)

### Docker MCP Catalog

One-time manual submission: submit PR to `docker/mcp-registry` with `server.yaml` and `tools.json`. Not part of automated CI.

### Daily Schedule Logic

- Pull upstream `latest`, compare digest with previous build
- If unchanged, skip build
- If changed, trigger full build + push + publish

## README Structure

The README serves as the primary documentation and project showcase. Structure:

1. **Header** — project name, badges (license, Docker pulls, MCP Registry), one-line description
2. **Features** — bullet list of key capabilities and competitive advantages
3. **Quick Start** — minimal steps to get running (docker run one-liner)
4. **Architecture** — architecture diagram (same as this spec)
5. **Usage**
   - HTTP mode (with/without auth)
   - stdio mode
   - Environment variables reference table
6. **MCP Tools Reference** — `search` and `autocomplete` parameter tables with examples
7. **Client Configuration** — Server mode and Local mode examples for each supported client (see table below)
8. **Claude Code Plugin** — installation via marketplace
9. **SearXNG Configuration** — how to customize SearXNG via Web UI or settings.yml volume mount
10. **Build from Source** — clone, docker build, run
11. **Contributing** — dev branch workflow, how to submit PRs
12. **License** — MIT

## MCP Client Configuration Examples

README includes configuration examples for both **Server mode** (remote HTTP) and **Local mode** (Docker stdio) for the following clients:

| Client          | Server Mode | Local Mode   |
| --------------- | ----------- | ------------ |
| Claude Code     | HTTP URL    | Docker stdio |
| Claude Desktop  | HTTP URL    | Docker stdio |
| Cursor          | HTTP URL    | Docker stdio |
| VS Code Copilot | HTTP URL    | Docker stdio |
| Windsurf        | HTTP URL    | Docker stdio |
| Cline           | HTTP URL    | Docker stdio |
| OpenCode        | HTTP URL    | Docker stdio |
| Continue.dev    | HTTP URL    | Docker stdio |
| Hermes Agent    | HTTP URL    | Docker stdio |

### Server Mode Example (Claude Desktop)

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

### Local Mode Example (Claude Desktop)

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

## Project Structure

```text
searxng-http-mcp/
├── .github/
│   └── workflows/
│       └── build.yml
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── .gitignore
├── LICENSE                      # MIT
├── README.md
├── Dockerfile
├── entrypoint.sh
├── config/
│   └── settings.yml             # SearXNG config (enable JSON format)
├── mcp_server/
│   ├── __init__.py
│   ├── app.py                   # Starlette app: routing, reverse proxy, auth middleware
│   └── tools.py                 # MCP tools: search, autocomplete
├── skills/
│   └── search/
│       └── SKILL.md
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-08-searxng-http-mcp-design.md
```

## Dependencies

Only `mcp[cli]` — which transitively brings:

- Starlette (ASGI framework)
- uvicorn (ASGI server)
- httpx (async HTTP client, used for reverse proxy and SearXNG API calls)

No additional packages required.

## Development

- Development happens on the `dev` branch
- Merge to `main` for releases
- GitHub Action only builds from `main`
