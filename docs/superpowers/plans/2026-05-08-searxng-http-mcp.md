# SearXNG HTTP MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Docker-based MCP server wrapping SearXNG with HTTP + stdio transports, auth, reverse proxy, and Claude Code Plugin support.

**Architecture:** Single Docker container based on `ghcr.io/searxng/searxng:latest`. A Starlette app on port 8888 serves as the unified entry point: `/mcp` routes to FastMCP, everything else reverse-proxies to SearXNG on internal port 8080. Auth via `x-api-key` header and HTTP Basic Auth. stdio mode available via `--stdio` flag.

**Tech Stack:** Python, FastMCP (mcp[cli]), Starlette, httpx, Docker, GitHub Actions

**Design Spec:** `docs/superpowers/specs/2026-05-08-searxng-http-mcp-design.md`

---

## File Map

| File | Responsibility |
| ---- | -------------- |
| `mcp_server/__init__.py` | Package marker |
| `mcp_server/tools.py` | FastMCP instance, `search` and `autocomplete` tools, dynamic description loader |
| `mcp_server/auth.py` | Starlette auth middleware (`x-api-key` + Basic Auth) |
| `mcp_server/proxy.py` | httpx reverse proxy ASGI app |
| `mcp_server/app.py` | Starlette app: compose auth + MCP mount + proxy, HTTP entry point |
| `mcp_server/main.py` | CLI entry point: parse `--stdio` flag, launch HTTP or stdio mode |
| `config/settings.yml` | SearXNG settings (enable JSON format) |
| `entrypoint.sh` | Docker entrypoint: start SearXNG, then MCP server |
| `Dockerfile` | Container image definition |
| `.gitignore` | Python gitignore |
| `LICENSE` | MIT license |
| `README.md` | Full project documentation |
| `.claude-plugin/plugin.json` | Claude Code plugin manifest |
| `.claude-plugin/marketplace.json` | Self-hosted marketplace metadata |
| `skills/search/SKILL.md` | Claude Code search skill |
| `.github/workflows/build.yml` | CI/CD: build, push, publish |
| `tests/test_auth.py` | Auth middleware unit tests |
| `tests/test_tools.py` | MCP tools unit tests |
| `tests/test_proxy.py` | Reverse proxy unit tests |
| `tests/test_app.py` | Integration tests for the Starlette app |

---

## Task 1: Project Scaffolding

**Files:**

- Create: `.gitignore`
- Create: `LICENSE`
- Create: `mcp_server/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg-info/
dist/
build/
*.egg

# Virtual environment
.venv/
venv/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db

# Test / Coverage
.pytest_cache/
.coverage
htmlcov/
```

- [ ] **Step 2: Create MIT LICENSE file**

Create `LICENSE` with MIT license text. Copyright holder: `whw23`.

- [ ] **Step 3: Create empty package files**

Create `mcp_server/__init__.py` and `tests/__init__.py` as empty files.

- [ ] **Step 4: Commit**

```bash
git add .gitignore LICENSE mcp_server/__init__.py tests/__init__.py
git commit -m "chore: scaffold project with gitignore, license, and package init"
```

---

## Task 2: MCP Tools (`search` and `autocomplete`)

**Files:**

- Create: `mcp_server/tools.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write failing tests for search tool**

```python
# tests/test_tools.py
import json
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.tools import mcp, fetch_engine_info


@pytest.fixture
def mock_search_response():
    return {
        "results": [
            {
                "title": "Example Result",
                "url": "https://example.com",
                "content": "This is a test result.",
                "engines": ["google", "bing"],
                "score": 5.0,
                "category": "general",
            }
        ],
        "answers": ["42"],
        "corrections": [],
        "suggestions": ["example query"],
        "infoboxes": [],
        "number_of_results": 1,
    }


@pytest.fixture
def mock_autocomplete_response():
    return ["python tutorial", "python download", "python documentation"]


class TestSearchTool:
    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_basic(self, mock_client_cls, mock_search_response):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_search_response

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        tools = mcp._tool_manager._tools
        search_fn = tools["search"].fn
        result = await search_fn(query="test")

        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "q=test" in call_args[1]["params"]["q"] or call_args[1]["params"]["q"] == "test"
        assert "results" in result

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_with_pages(self, mock_client_cls, mock_search_response):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_search_response

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        tools = mcp._tool_manager._tools
        search_fn = tools["search"].fn
        result = await search_fn(query="test", pages=3)

        assert mock_client.get.call_count == 3

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_pages_clamped_to_5(self, mock_client_cls, mock_search_response):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_search_response

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        tools = mcp._tool_manager._tools
        search_fn = tools["search"].fn
        result = await search_fn(query="test", pages=10)

        assert mock_client.get.call_count == 5


class TestAutocompleteTool:
    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_autocomplete(self, mock_client_cls, mock_autocomplete_response):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_autocomplete_response

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        tools = mcp._tool_manager._tools
        autocomplete_fn = tools["autocomplete"].fn
        result = await autocomplete_fn(query="python")

        mock_client.get.assert_called_once()
        assert "python tutorial" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pip install "mcp[cli]" pytest pytest-anyio httpx
pytest tests/test_tools.py -v
```

Expected: FAIL — `mcp_server.tools` module does not exist yet.

- [ ] **Step 3: Implement MCP tools**

```python
# mcp_server/tools.py
import asyncio
import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

SEARXNG_BASE_URL = os.environ.get("SEARXNG_URL", "http://127.0.0.1:8080")

mcp = FastMCP(
    "SearXNG",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
)


async def fetch_engine_info() -> dict:
    """Fetch available engines and categories from SearXNG config API."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SEARXNG_BASE_URL}/config", timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                categories = list(data.get("categories", {}).keys())
                engines = [
                    e["name"]
                    for e in data.get("engines", [])
                    if e.get("enabled", True)
                ]
                return {"categories": categories, "engines": engines}
    except Exception:
        pass
    return {
        "categories": [
            "general", "images", "videos", "news", "map",
            "music", "it", "science", "files", "social_media",
        ],
        "engines": [],
    }


def _trim_result(result: dict) -> dict:
    """Keep only essential fields from a search result to reduce token usage."""
    fields = [
        "title", "url", "content", "engines", "score",
        "category", "publishedDate", "thumbnail", "img_src",
    ]
    return {k: v for k, v in result.items() if k in fields and v}


@mcp.tool()
async def search(
    query: str,
    categories: str = "",
    language: str = "",
    time_range: str = "",
    safesearch: int = 0,
    pageno: int = 1,
    pages: int = 1,
    engines: str = "",
) -> str:
    """Search the web using SearXNG metasearch engine.

    Aggregates results from multiple search engines (Google, Bing, DuckDuckGo, etc.).
    Returns results, answers, suggestions, corrections, and infoboxes.
    """
    pages = max(1, min(pages, 5))

    params = {"q": query, "format": "json"}
    if categories:
        params["categories"] = categories
    if language:
        params["language"] = language
    if time_range:
        params["time_range"] = time_range
    if safesearch:
        params["safesearch"] = str(safesearch)
    if engines:
        params["engines"] = engines

    all_results = []
    all_answers = set()
    all_suggestions = set()
    all_corrections = set()
    all_infoboxes = []

    async with httpx.AsyncClient() as client:
        tasks = []
        for page in range(pageno, pageno + pages):
            page_params = {**params, "pageno": str(page)}
            tasks.append(
                client.get(
                    f"{SEARXNG_BASE_URL}/search",
                    params=page_params,
                    timeout=30.0,
                )
            )
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    for resp in responses:
        if isinstance(resp, Exception):
            continue
        if resp.status_code != 200:
            continue
        data = resp.json()
        all_results.extend(_trim_result(r) for r in data.get("results", []))
        all_answers.update(data.get("answers", []))
        all_suggestions.update(data.get("suggestions", []))
        all_corrections.update(data.get("corrections", []))
        all_infoboxes.extend(data.get("infoboxes", []))

    output = {
        "results": all_results,
        "number_of_results": len(all_results),
    }
    if all_answers:
        output["answers"] = list(all_answers)
    if all_suggestions:
        output["suggestions"] = list(all_suggestions)
    if all_corrections:
        output["corrections"] = list(all_corrections)
    if all_infoboxes:
        output["infoboxes"] = all_infoboxes

    return json.dumps(output, ensure_ascii=False)


@mcp.tool()
async def autocomplete(query: str) -> str:
    """Get search query suggestions from SearXNG.

    Returns a list of autocomplete suggestions for the given query.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SEARXNG_BASE_URL}/autocomplete",
            params={"q": query},
            timeout=10.0,
        )
    if resp.status_code != 200:
        return json.dumps({"error": f"Autocomplete failed with status {resp.status_code}"})
    return json.dumps(resp.json(), ensure_ascii=False)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_tools.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_server/tools.py tests/test_tools.py
git commit -m "feat: implement search and autocomplete MCP tools"
```

---

## Task 3: Auth Middleware

**Files:**

- Create: `mcp_server/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests for auth middleware**

```python
# tests/test_auth.py
import base64
from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from mcp_server.auth import AuthMiddleware


def _make_app(api_key: str | None = None):
    async def homepage(request):
        return PlainTextResponse("OK")

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(AuthMiddleware, api_key=api_key)
    return app


class TestAuthMiddlewareNoKey:
    def test_no_key_configured_passes_through(self):
        app = _make_app(api_key=None)
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.text == "OK"

    def test_empty_key_passes_through(self):
        app = _make_app(api_key="")
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200


class TestAuthMiddlewareXApiKey:
    def test_valid_x_api_key(self):
        app = _make_app(api_key="secret123")
        client = TestClient(app)
        resp = client.get("/", headers={"x-api-key": "secret123"})
        assert resp.status_code == 200

    def test_invalid_x_api_key(self):
        app = _make_app(api_key="secret123")
        client = TestClient(app)
        resp = client.get("/", headers={"x-api-key": "wrong"})
        assert resp.status_code == 401

    def test_missing_credentials(self):
        app = _make_app(api_key="secret123")
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 401
        assert "Basic" in resp.headers.get("www-authenticate", "")


class TestAuthMiddlewareBasicAuth:
    def test_valid_basic_auth(self):
        app = _make_app(api_key="secret123")
        client = TestClient(app)
        creds = base64.b64encode(b":secret123").decode()
        resp = client.get("/", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 200

    def test_basic_auth_with_username(self):
        app = _make_app(api_key="secret123")
        client = TestClient(app)
        creds = base64.b64encode(b"anyuser:secret123").decode()
        resp = client.get("/", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 200

    def test_invalid_basic_auth(self):
        app = _make_app(api_key="secret123")
        client = TestClient(app)
        creds = base64.b64encode(b":wrongkey").decode()
        resp = client.get("/", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 401

    def test_malformed_basic_auth(self):
        app = _make_app(api_key="secret123")
        client = TestClient(app)
        resp = client.get("/", headers={"Authorization": "Basic notbase64!!!"})
        assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_auth.py -v
```

Expected: FAIL — `mcp_server.auth` module does not exist yet.

- [ ] **Step 3: Implement auth middleware**

```python
# mcp_server/auth.py
import base64
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class AuthMiddleware(BaseHTTPMiddleware):
    """Authenticate requests via x-api-key header or HTTP Basic Auth."""

    def __init__(self, app, api_key: str | None = None):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        if not self.api_key:
            return await call_next(request)

        # Check x-api-key header
        x_api_key = request.headers.get("x-api-key", "")
        if x_api_key and secrets.compare_digest(x_api_key, self.api_key):
            return await call_next(request)

        # Check Basic Auth
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                _, _, password = decoded.partition(":")
                if secrets.compare_digest(password, self.api_key):
                    return await call_next(request)
            except Exception:
                pass

        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="SearXNG MCP"'},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_server/auth.py tests/test_auth.py
git commit -m "feat: implement auth middleware with x-api-key and Basic Auth"
```

---

## Task 4: Reverse Proxy

**Files:**

- Create: `mcp_server/proxy.py`
- Create: `tests/test_proxy.py`

- [ ] **Step 1: Write failing tests for reverse proxy**

```python
# tests/test_proxy.py
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient

from mcp_server.proxy import ReverseProxyApp


class TestReverseProxy:
    @patch("mcp_server.proxy.httpx.AsyncClient")
    def test_proxy_get_request(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = MagicMock()
        mock_response.headers.items.return_value = [("content-type", "text/html")]
        mock_response.content = b"<html>SearXNG</html>"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        proxy = ReverseProxyApp(upstream="http://127.0.0.1:8080")
        app = Starlette(routes=[Mount("/", app=proxy)])
        client = TestClient(app)

        resp = client.get("/")
        assert resp.status_code == 200
        assert b"SearXNG" in resp.content

    @patch("mcp_server.proxy.httpx.AsyncClient")
    def test_proxy_preserves_query_params(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = MagicMock()
        mock_response.headers.items.return_value = [("content-type", "application/json")]
        mock_response.content = b'{"results": []}'

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        proxy = ReverseProxyApp(upstream="http://127.0.0.1:8080")
        app = Starlette(routes=[Mount("/", app=proxy)])
        client = TestClient(app)

        resp = client.get("/search?q=test&format=json")
        assert resp.status_code == 200

        call_args = mock_client.request.call_args
        assert "q=test" in str(call_args)

    @patch("mcp_server.proxy.httpx.AsyncClient")
    def test_proxy_post_request(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = MagicMock()
        mock_response.headers.items.return_value = [("content-type", "text/html")]
        mock_response.content = b"<html>OK</html>"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        proxy = ReverseProxyApp(upstream="http://127.0.0.1:8080")
        app = Starlette(routes=[Mount("/", app=proxy)])
        client = TestClient(app)

        resp = client.post("/search", data={"q": "test"})
        assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_proxy.py -v
```

Expected: FAIL — `mcp_server.proxy` module does not exist yet.

- [ ] **Step 3: Implement reverse proxy**

```python
# mcp_server/proxy.py
import httpx
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


class ReverseProxyApp:
    """ASGI app that proxies all requests to an upstream HTTP server."""

    def __init__(self, upstream: str):
        self.upstream = upstream.rstrip("/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return

        request = Request(scope, receive)
        path = scope.get("path", "/")
        query_string = scope.get("query_string", b"").decode()
        url = f"{self.upstream}{path}"
        if query_string:
            url = f"{url}?{query_string}"

        body = await request.body()

        headers_to_forward = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in ("host", "x-api-key", "authorization")
        }

        async with httpx.AsyncClient() as client:
            upstream_resp = await client.request(
                method=request.method,
                url=url,
                headers=headers_to_forward,
                content=body if body else None,
                timeout=30.0,
            )

        excluded_headers = {"transfer-encoding", "content-encoding", "content-length"}
        resp_headers = {
            k: v
            for k, v in upstream_resp.headers.items()
            if k.lower() not in excluded_headers
        }

        response = Response(
            content=upstream_resp.content,
            status_code=upstream_resp.status_code,
            headers=resp_headers,
        )
        await response(scope, receive, send)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_proxy.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_server/proxy.py tests/test_proxy.py
git commit -m "feat: implement httpx reverse proxy for SearXNG"
```

---

## Task 5: Starlette App (Compose Everything)

**Files:**

- Create: `mcp_server/app.py`
- Create: `mcp_server/main.py`
- Create: `tests/test_app.py`

- [ ] **Step 1: Write failing tests for the composed app**

```python
# tests/test_app.py
import base64
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient


class TestAppNoAuth:
    @patch.dict("os.environ", {}, clear=True)
    def test_mcp_endpoint_accessible(self):
        from mcp_server.app import create_app

        app = create_app()
        client = TestClient(app)
        # MCP endpoint should respond (even if not a valid MCP request,
        # it should not 404)
        resp = client.get("/mcp")
        assert resp.status_code != 404

    @patch.dict("os.environ", {}, clear=True)
    @patch("mcp_server.proxy.httpx.AsyncClient")
    def test_proxy_route_forwards(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = MagicMock()
        mock_response.headers.items.return_value = [("content-type", "text/html")]
        mock_response.content = b"<html>SearXNG</html>"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        from mcp_server.app import create_app

        app = create_app()
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200


class TestAppWithAuth:
    @patch.dict("os.environ", {"API_KEY": "testkey"})
    def test_mcp_requires_auth(self):
        from mcp_server.app import create_app

        app = create_app()
        client = TestClient(app)
        resp = client.get("/mcp")
        assert resp.status_code == 401

    @patch.dict("os.environ", {"API_KEY": "testkey"})
    def test_mcp_with_x_api_key(self):
        from mcp_server.app import create_app

        app = create_app()
        client = TestClient(app)
        resp = client.get("/mcp", headers={"x-api-key": "testkey"})
        assert resp.status_code != 401

    @patch.dict("os.environ", {"API_KEY": "testkey"})
    def test_proxy_with_basic_auth(self):
        from mcp_server.app import create_app

        app = create_app()
        client = TestClient(app)
        creds = base64.b64encode(b":testkey").decode()
        resp = client.get(
            "/some-path",
            headers={"Authorization": f"Basic {creds}"},
        )
        # Should not be 401 (proxy may fail to reach upstream, but auth passes)
        assert resp.status_code != 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_app.py -v
```

Expected: FAIL — `mcp_server.app` module does not exist yet.

- [ ] **Step 3: Implement app.py**

```python
# mcp_server/app.py
import contextlib
import os

from starlette.applications import Starlette
from starlette.routing import Mount

from mcp_server.auth import AuthMiddleware
from mcp_server.proxy import ReverseProxyApp
from mcp_server.tools import mcp


def create_app() -> Starlette:
    """Create the Starlette ASGI app with MCP, auth, and reverse proxy."""
    api_key = os.environ.get("API_KEY", "")
    searxng_url = os.environ.get("SEARXNG_URL", "http://127.0.0.1:8080")

    proxy = ReverseProxyApp(upstream=searxng_url)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp.session_manager.run():
            yield

    app = Starlette(
        routes=[
            Mount("/mcp", app=mcp.streamable_http_app()),
            Mount("/", app=proxy),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(AuthMiddleware, api_key=api_key or None)
    return app


app = create_app()
```

- [ ] **Step 4: Implement main.py**

```python
# mcp_server/main.py
import sys

from mcp_server.tools import mcp


def main():
    if "--stdio" in sys.argv:
        mcp.run(transport="stdio")
    else:
        import uvicorn
        from mcp_server.app import app

        uvicorn.run(app, host="0.0.0.0", port=8888)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_app.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add mcp_server/app.py mcp_server/main.py tests/test_app.py
git commit -m "feat: compose Starlette app with MCP, auth, and reverse proxy"
```

---

## Task 6: SearXNG Configuration

**Files:**

- Create: `config/settings.yml`

- [ ] **Step 1: Create SearXNG settings**

```yaml
# SearXNG configuration for MCP server
# Enables JSON format output required by MCP tools

use_default_settings: true

search:
  formats:
    - json

server:
  secret_key: "searxng-mcp-default-secret-key"
  bind_address: "127.0.0.1"
  port: 8080
```

- [ ] **Step 2: Commit**

```bash
git add config/settings.yml
git commit -m "feat: add SearXNG settings with JSON format enabled"
```

---

## Task 7: Docker Setup

**Files:**

- Create: `Dockerfile`
- Create: `entrypoint.sh`

- [ ] **Step 1: Create entrypoint script**

```bash
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
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
FROM ghcr.io/searxng/searxng:latest

# Install MCP Server dependencies
RUN pip install --no-cache-dir "mcp[cli]"

# Copy SearXNG config
COPY config/settings.yml /etc/searxng/settings.yml

# Copy MCP Server code
COPY mcp_server/ /usr/local/searxng/mcp_server/

# Copy custom entrypoint
COPY entrypoint.sh /usr/local/searxng/custom-entrypoint.sh
RUN chmod +x /usr/local/searxng/custom-entrypoint.sh

EXPOSE 8888

ENTRYPOINT ["/usr/local/searxng/custom-entrypoint.sh"]
```

- [ ] **Step 3: Build and test the image locally**

```bash
docker build -t searxng-http-mcp:local .
docker run -d -p 8888:8888 --name searxng-mcp-test searxng-http-mcp:local
sleep 10
curl -sf http://localhost:8888/ | head -c 200
curl -sf http://localhost:8888/mcp -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'
docker stop searxng-mcp-test && docker rm searxng-mcp-test
```

Expected: Both curl commands return valid responses.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile entrypoint.sh
git commit -m "feat: add Dockerfile and entrypoint with HTTP/stdio support"
```

---

## Task 8: Claude Code Plugin

**Files:**

- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `skills/search/SKILL.md`

- [ ] **Step 1: Create plugin.json**

```json
{
  "name": "searxng-http-mcp",
  "version": "1.0.0",
  "description": "SearXNG metasearch engine MCP server — search the web with privacy",
  "author": {
    "name": "whw23"
  },
  "repository": "https://github.com/whw23/searxng-http-mcp",
  "license": "MIT",
  "keywords": ["search", "searxng", "web-search", "mcp"],
  "skills": "./skills/"
}
```

- [ ] **Step 2: Create marketplace.json**

```json
{
  "name": "searxng-http-mcp",
  "owner": {
    "name": "whw23"
  },
  "description": "SearXNG metasearch engine MCP server",
  "plugins": [
    {
      "name": "searxng-http-mcp",
      "source": "./",
      "description": "SearXNG metasearch engine MCP server — search the web with privacy",
      "version": "1.0.0",
      "license": "MIT",
      "keywords": ["search", "searxng", "web-search", "mcp"]
    }
  ]
}
```

- [ ] **Step 3: Create search skill**

```markdown
---
name: search
description: Search the web using SearXNG metasearch engine. Use when you need to find information online, look up documentation, research topics, or answer questions requiring current knowledge.
---

# SearXNG Web Search

Use the configured SearXNG MCP server to search the web.

## When to Use

- Answering questions that need up-to-date information
- Looking up documentation or API references
- Researching technical topics
- Finding news or current events

## How to Use

Call the `search` MCP tool with your query:

- `query` (required): Search terms
- `categories`: general, images, videos, news, it, science
- `language`: Language code (e.g., zh, en, ja)
- `time_range`: day, month, year
- `pages`: Number of pages (1-5) for more results

## Rules

1. Always include a **Sources** section at the end with clickable markdown links
2. Use `categories` to narrow results (e.g., `news` for current events, `it` for tech)
3. Use `pages=3` when you need comprehensive results
4. Use `language` when the user writes in a specific language
```

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/ skills/
git commit -m "feat: add Claude Code plugin with search skill"
```

---

## Task 9: GitHub Actions CI/CD

**Files:**

- Create: `.github/workflows/build.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
name: Build and Publish

on:
  push:
    branches: [main]
  schedule:
    - cron: "17 3 * * *"  # Daily at 03:17 UTC

permissions:
  contents: read
  packages: write
  id-token: write  # For MCP Registry OIDC

env:
  IMAGE_NAME: ghcr.io/whw23/searxng-http-mcp
  UPSTREAM_IMAGE: ghcr.io/searxng/searxng:latest

jobs:
  check-and-build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Check upstream image digest
        id: upstream
        run: |
          docker pull ${{ env.UPSTREAM_IMAGE }}
          DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' ${{ env.UPSTREAM_IMAGE }})
          echo "digest=$DIGEST" >> "$GITHUB_OUTPUT"

          # Extract upstream version tag
          UPSTREAM_VERSION=$(docker inspect --format='{{index .Config.Env}}' ${{ env.UPSTREAM_IMAGE }} | grep -oP '__SEARXNG_VERSION=\K[^ ]+' || echo "unknown")
          echo "version=$UPSTREAM_VERSION" >> "$GITHUB_OUTPUT"

          # Check if we already built this digest
          CACHE_KEY="upstream-digest"
          PREV_DIGEST=""
          if [ -f /tmp/prev-digest ]; then
            PREV_DIGEST=$(cat /tmp/prev-digest)
          fi
          echo "prev_digest=$PREV_DIGEST" >> "$GITHUB_OUTPUT"

      - name: Skip if unchanged (scheduled only)
        if: github.event_name == 'schedule' && steps.upstream.outputs.digest == steps.upstream.outputs.prev_digest
        run: |
          echo "Upstream unchanged, skipping build."
          exit 0

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Generate tags
        id: tags
        run: |
          SHORT_SHA=$(echo "${{ github.sha }}" | cut -c1-7)
          UPSTREAM_VERSION="${{ steps.upstream.outputs.version }}"
          FULL_TAG="${UPSTREAM_VERSION}-${SHORT_SHA}"
          echo "full_tag=$FULL_TAG" >> "$GITHUB_OUTPUT"
          echo "short_sha=$SHORT_SHA" >> "$GITHUB_OUTPUT"

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ${{ env.IMAGE_NAME }}:${{ steps.tags.outputs.full_tag }}
            ${{ env.IMAGE_NAME }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Save upstream digest
        run: echo "${{ steps.upstream.outputs.digest }}" > /tmp/prev-digest
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: add GitHub Actions workflow for build, push, and publish"
```

---

## Task 10: README

**Files:**

- Create: `README.md`

- [ ] **Step 1: Write README**

Create `README.md` following the 12-section structure defined in the design spec:

1. Header with badges (MIT license, Docker image, MCP Registry)
2. Features list (self-contained, auth, dual transport, dynamic descriptions, multi-page fanout, plugin)
3. Quick Start (single `docker run` command)
4. Architecture diagram
5. Usage (HTTP mode, stdio mode, environment variables table)
6. MCP Tools Reference (search and autocomplete parameter tables)
7. Client Configuration (Server mode + Local mode for all 9 clients: Claude Code, Claude Desktop, Cursor, VS Code Copilot, Windsurf, Cline, OpenCode, Continue.dev, Hermes Agent)
8. Claude Code Plugin installation
9. SearXNG Configuration (Web UI access, volume mount for custom settings.yml)
10. Build from Source (clone, docker build, run)
11. Contributing (dev branch workflow)
12. License (MIT)

The README should use the exact configuration formats discovered during design:

- Claude Desktop: `claude_desktop_config.json` with `url` or `command`/`args`
- Cursor: similar JSON config
- OpenCode: `.opencode.json` with `type: "stdio"` or `type: "sse"` + `url`
- Hermes Agent: `~/.hermes/config.yaml` with `command`/`args` or `url`/`headers`
- Others: standard MCP JSON config

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README with client configurations"
```

---

## Task 11: Dynamic Tool Descriptions

**Files:**

- Modify: `mcp_server/tools.py`
- Modify: `mcp_server/app.py`

- [ ] **Step 1: Add startup hook to fetch engine info**

Modify `mcp_server/app.py` to call `fetch_engine_info()` during lifespan startup and update the `search` tool's description with the available engines and categories.

```python
# In mcp_server/app.py, update the lifespan function:

@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp.session_manager.run():
        info = await fetch_engine_info()
        if info["categories"]:
            categories_str = ", ".join(info["categories"])
            search_tool = mcp._tool_manager._tools.get("search")
            if search_tool and search_tool.fn:
                original_desc = search_tool.description or ""
                search_tool.description = (
                    f"{original_desc}\n\n"
                    f"Available categories: {categories_str}\n"
                )
                if info["engines"]:
                    engines_str = ", ".join(info["engines"][:50])
                    search_tool.description += (
                        f"Available engines (top 50): {engines_str}"
                    )
        yield
```

Update the import in `app.py`:

```python
from mcp_server.tools import mcp, fetch_engine_info
```

- [ ] **Step 2: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add mcp_server/app.py
git commit -m "feat: dynamically populate search tool description from SearXNG config"
```

---

## Task 12: Final Integration Test

- [ ] **Step 1: Build Docker image**

```bash
docker build -t searxng-http-mcp:local .
```

- [ ] **Step 2: Test HTTP mode**

```bash
docker run -d -p 8888:8888 -e API_KEY=testkey --name mcp-test searxng-http-mcp:local
sleep 15

# Test SearXNG UI via proxy (with auth)
curl -s -u :testkey http://localhost:8888/ | head -c 100

# Test MCP initialize
curl -s http://localhost:8888/mcp \
  -H "x-api-key: testkey" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'

# Test auth rejection
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/mcp

docker stop mcp-test && docker rm mcp-test
```

Expected: UI returns HTML, MCP returns JSON with capabilities, unauthenticated request returns 401.

- [ ] **Step 3: Test stdio mode**

```bash
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | docker run --rm -i searxng-http-mcp:local --stdio
```

Expected: Returns JSON-RPC response with server capabilities.

- [ ] **Step 4: Commit any final fixes if needed**

---

## Summary

| Task | Component | Commits |
| ---- | --------- | ------- |
| 1 | Project scaffolding | 1 |
| 2 | MCP tools (search + autocomplete) | 1 |
| 3 | Auth middleware | 1 |
| 4 | Reverse proxy | 1 |
| 5 | Starlette app composition | 1 |
| 6 | SearXNG configuration | 1 |
| 7 | Docker setup | 1 |
| 8 | Claude Code Plugin | 1 |
| 9 | GitHub Actions CI/CD | 1 |
| 10 | README | 1 |
| 11 | Dynamic tool descriptions | 1 |
| 12 | Final integration test | 0-1 |

Total: 11-12 commits, 12 tasks.
