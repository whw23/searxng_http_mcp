# SearXNG HTTP MCP Server — Design Spec

## Overview

An HTTP MCP server that wraps a SearXNG instance, packaged as a single Docker container based on the official SearXNG image. Exposes search capabilities to Claude and other MCP clients via Streamable HTTP, while preserving full SearXNG Web UI access through a unified reverse proxy with authentication.

**License:** AGPL-3.0-or-later (same as SearXNG)

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
- **Auth Middleware**: Global HTTP Basic Auth + Bearer token support. Controlled by `API_KEY` environment variable. No env var = no auth.

### Communication Flow

1. Client request → Starlette `:8888`
2. Auth middleware validates credentials
3. `/mcp` requests → FastMCP handles MCP protocol (initialize, tools/list, tools/call)
4. All other requests → httpx reverse proxy → SearXNG `:8080`
5. MCP tools internally call `http://127.0.0.1:8080/search?format=json`

## Authentication

### Mechanism

Dual-mode authentication via a single `API_KEY` environment variable:

- **Bearer token**: `Authorization: Bearer <API_KEY>` — for MCP clients
- **HTTP Basic Auth**: `Authorization: Basic base64(:<API_KEY>)` — for browsers (username empty, password = API_KEY)

### Behavior

- `API_KEY` env var set → all requests require authentication
- `API_KEY` env var not set → no authentication, open access

### Middleware Logic

```text
1. If API_KEY not configured → pass through
2. Extract Authorization header
3. If "Bearer <token>" → compare token with API_KEY
4. If "Basic <base64>" → decode, extract password, compare with API_KEY
5. No header or mismatch → 401 Unauthorized (with WWW-Authenticate: Basic)
```

## MCP Tools

### Tool 1: `search`

Performs a web search via SearXNG.

| Parameter    | Type | Required | Default | Description                                                                                   |
| ------------ | ---- | -------- | ------- | --------------------------------------------------------------------------------------------- |
| `query`      | str  | yes      | —       | Search query string                                                                           |
| `categories` | str  | no       | ""      | Comma-separated: general, images, videos, news, map, music, it, science, files, social\_media |
| `language`   | str  | no       | ""      | Language code (e.g., zh, en, ja)                                                              |
| `time_range` | str  | no       | ""      | day, month, year                                                                              |
| `safesearch` | int  | no       | 0       | 0=off, 1=moderate, 2=strict                                                                  |
| `pageno`     | int  | no       | 1       | Page number                                                                                   |
| `engines`    | str  | no       | ""      | Comma-separated engine names (e.g., google,bing)                                              |

Internal call: `GET http://127.0.0.1:8080/search?q=<query>&format=json&...`

Returns structured results including: results, answers, corrections, suggestions, infoboxes.

### Tool 2: `autocomplete`

Provides search query suggestions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | str | yes | Query string to autocomplete |

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

# Copy custom entrypoint
COPY entrypoint.sh /usr/local/searxng/custom-entrypoint.sh

EXPOSE 8888

ENTRYPOINT ["/usr/local/searxng/custom-entrypoint.sh"]
```

### Entrypoint Script

1. Start SearXNG via original entrypoint (background, internal port 8080)
2. Start Starlette app on port 8888

### SearXNG Configuration

`settings.yml` must enable JSON format output:

```yaml
search:
  formats:
    - json
```

### Running

```bash
# No auth
docker run -p 8888:8888 ghcr.io/whw23/searxng-http-mcp:latest

# With auth
docker run -p 8888:8888 -e API_KEY=your-secret-key ghcr.io/whw23/searxng-http-mcp:latest
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

### Daily Schedule Logic

- Pull upstream `latest`, compare digest with previous build
- If unchanged, skip build
- If changed, trigger full build + push + publish

## Project Structure

```
searxng_http_mcp_server/
├── .github/
│   └── workflows/
│       └── build.yml
├── .gitignore
├── LICENSE                  # AGPL-3.0-or-later
├── README.md
├── Dockerfile
├── entrypoint.sh
├── config/
│   └── settings.yml         # SearXNG config (enable JSON format)
├── mcp_server/
│   ├── __init__.py
│   ├── app.py               # Starlette app: routing, reverse proxy, auth middleware
│   └── tools.py             # MCP tools: search, autocomplete
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
