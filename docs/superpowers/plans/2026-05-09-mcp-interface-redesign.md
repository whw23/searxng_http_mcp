# MCP Interface Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance MCP tool schemas with descriptions, Literal/Field constraints, and ToolAnnotations; add `engine_info` tool; streamline dynamic description injection.

**Architecture:** Annotated + Field pattern on existing function signatures. New `engine_info` tool wraps extended `fetch_engine_info()`. Dynamic description injection simplified to categories only.

**Tech Stack:** Python 3.14, FastMCP, Pydantic Field, typing.Annotated/Literal, mcp.types.ToolAnnotations

---

### Task 1: Redesign `search` tool signature

**Files:**
- Modify: `mcp_server/tools.py:1-10` (imports)
- Modify: `mcp_server/tools.py:128-161` (search function signature and param building)

- [ ] **Step 1: Update imports**

In `mcp_server/tools.py`, replace the imports block:

```python
import asyncio
import json
import os
import time

import httpx
from mcp.server.fastmcp import FastMCP
```

with:

```python
import asyncio
import json
import os
import time
from typing import Annotated, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field
```

- [ ] **Step 2: Replace search function signature and param building**

Replace lines 128-161 (from `@mcp.tool()` through the `params` building block) with:

```python
@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def search(
    query: Annotated[str, Field(
        description="The search query to use",
    )],
    categories: Annotated[str, Field(
        description="Comma-separated category names to focus on (e.g., 'general,news,science')",
    )] = "",
    engines: Annotated[str, Field(
        description="Comma-separated engine names to use (e.g., 'google,arxiv,wikipedia')",
    )] = "",
    language: Annotated[str, Field(
        description="Search language code (e.g., 'en', 'zh', 'ja', 'de')",
    )] = "",
    time_range: Annotated[
        Literal["day", "week", "month", "year"] | None,
        Field(description="Restrict results to those published within this time window"),
    ] = None,
    safesearch: Annotated[
        Literal[0, 1, 2],
        Field(description="Safe search level: 0=off, 1=moderate, 2=strict"),
    ] = 0,
    pageno: Annotated[int, Field(
        ge=1,
        description="Starting page number",
    )] = 1,
    pages: Annotated[int, Field(
        ge=1, le=5,
        description="Number of pages to fetch in parallel (multi-page fanout)",
    )] = 1,
    max_results: Annotated[int, Field(
        ge=1, le=100,
        description="Maximum number of results to return",
    )] = 10,
    format: Annotated[
        Literal["compact", "full"],
        Field(description="Result detail level: 'compact' returns title/url/content only, 'full' includes engines/score/category/date/thumbnails"),
    ] = "compact",
) -> str:
    """Search the web using SearXNG metasearch engine.

    Aggregates results from 200+ search engines (Google, Bing, DuckDuckGo, Brave, etc.)
    with privacy. Returns results, answers, suggestions, corrections, and infoboxes.
    Use 'categories' to focus on specific content types. Use 'pages' for more results.
    """
    fields = COMPACT_FIELDS if format == "compact" else FULL_FIELDS

    params: dict = {"q": query, "format": "json"}
    if categories:
        params["categories"] = categories
    if language:
        params["language"] = language
    if time_range is not None:
        params["time_range"] = time_range
    if safesearch:
        params["safesearch"] = str(safesearch)
    if engines:
        params["engines"] = engines
```

Key changes vs current code:
- Removed `pages = max(1, min(pages, 5))` and `max_results = max(1, min(max_results, 100))` — Pydantic enforces
- Changed `if time_range:` to `if time_range is not None:` — default is now `None` instead of `""`

- [ ] **Step 3: Run tests to check current state**

Run: `cd /Users/wanghaowei/searxng_http_mcp_server && .venv/bin/pytest tests/test_tools.py -v`

Expected: Most tests pass. `test_search_pages_clamped_to_5` will fail because `pages=10` now triggers Pydantic validation error instead of being clamped.

- [ ] **Step 4: Commit**

```bash
git add mcp_server/tools.py
git commit -m "feat: add Annotated/Field/Literal constraints and ToolAnnotations to search tool

- Add descriptions to all parameters via Field()
- Add Literal constraints: time_range, safesearch, format
- Add range constraints: pageno ge=1, pages ge=1 le=5, max_results ge=1 le=100
- Add ToolAnnotations (readOnly, idempotent, openWorld)
- Change time_range default from '' to None, add 'week' support
- Remove runtime clamp in favor of schema-level validation"
```

---

### Task 2: Update tests for `search` signature changes

**Files:**
- Modify: `tests/test_tools.py:168-175` (pages clamped test)

- [ ] **Step 1: Remove `test_search_pages_clamped_to_5`**

Delete the entire `test_search_pages_clamped_to_5` method from `TestSearchTool` class. Pydantic now enforces `pages` range at the MCP protocol layer (schema validation during request deserialization). Direct function calls in tests bypass this validation, so testing it here is not meaningful.

- [ ] **Step 2: Run tests**

Run: `cd /Users/wanghaowei/searxng_http_mcp_server && .venv/bin/pytest tests/test_tools.py -v`

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_tools.py
git commit -m "test: remove pages clamp test, now enforced by Pydantic schema"
```

---

### Task 3: Redesign `autocomplete` tool signature

**Files:**
- Modify: `mcp_server/tools.py:230-245` (autocomplete function)

- [ ] **Step 1: Replace autocomplete function signature**

Replace the `@mcp.tool()` decorator and function signature (keep the function body unchanged):

```python
@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def autocomplete(
    query: Annotated[str, Field(
        description="Partial query string to get suggestions for",
    )],
) -> str:
    """Get search query suggestions from SearXNG.

    Returns a list of autocomplete suggestions for the given partial query.
    Use this to discover relevant search terms before performing a full search.
    """
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/wanghaowei/searxng_http_mcp_server && .venv/bin/pytest tests/test_tools.py::TestAutocompleteTool -v`

Expected: All PASS (no logic changes).

- [ ] **Step 3: Commit**

```bash
git add mcp_server/tools.py
git commit -m "feat: add Field description and ToolAnnotations to autocomplete tool"
```

---

### Task 4: Extend `fetch_engine_info` to return category-engine mapping

**Files:**
- Modify: `mcp_server/tools.py:62-96` (fetch_engine_info function)
- Modify: `tests/test_tools.py:251-281` (fetch_engine_info tests)

- [ ] **Step 1: Write the failing test**

Add a new test in `TestFetchEngineInfo` class and update the existing success test. In `tests/test_tools.py`, replace the `test_fetch_engine_info_success` method:

```python
    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_fetch_engine_info_success(self, mock_client_cls):
        response = _make_httpx_response({
            "categories": {"general": {}, "images": {}, "news": {}},
            "engines": [
                {"name": "google", "enabled": True, "categories": ["general"]},
                {"name": "bing", "enabled": True, "categories": ["general", "images"]},
                {"name": "google images", "enabled": True, "categories": ["images"]},
                {"name": "disabled_engine", "enabled": False, "categories": ["general"]},
            ],
        })
        mock_client_cls.return_value = _make_mock_client(response)

        info = await fetch_engine_info()

        assert "general" in info["categories"]
        assert "google" in info["engines"]
        assert "disabled_engine" not in info["engines"]
        assert "category_engines" in info
        assert "google" in info["category_engines"]["general"]
        assert "bing" in info["category_engines"]["general"]
        assert "bing" in info["category_engines"]["images"]
        assert "google images" in info["category_engines"]["images"]
        assert "disabled_engine" not in info["category_engines"]["general"]
```

Also add a fallback test for `category_engines`:

```python
    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_fetch_engine_info_fallback(self, mock_client_cls):
        mock_client_cls.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        info = await fetch_engine_info()

        assert "general" in info["categories"]
        assert info["engines"] == []
        assert info["category_engines"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/wanghaowei/searxng_http_mcp_server && .venv/bin/pytest tests/test_tools.py::TestFetchEngineInfo -v`

Expected: FAIL — `category_engines` key not found in result.

- [ ] **Step 3: Update `fetch_engine_info` implementation**

Replace the `fetch_engine_info` function in `mcp_server/tools.py`:

```python
async def fetch_engine_info() -> dict:
    """Fetch available engines and categories from SearXNG config API."""
    try:
        client = await _get_client()
        resp = await client.get(
            f"{SEARXNG_BASE_URL}/config", timeout=10.0
        )
        if resp.status_code == 200:
            data = resp.json()
            raw_categories = data.get("categories", [])
            if isinstance(raw_categories, list):
                categories = raw_categories
            elif isinstance(raw_categories, dict):
                categories = list(raw_categories.keys())
            else:
                categories = []

            engines = []
            category_engines: dict[str, list[str]] = {}
            for e in data.get("engines", []):
                if not e.get("enabled", True):
                    continue
                name = e["name"]
                engines.append(name)
                for cat in e.get("categories", []):
                    category_engines.setdefault(cat, []).append(name)

            return {
                "categories": categories,
                "engines": engines,
                "category_engines": category_engines,
            }
    except Exception:
        pass
    return {
        "categories": [
            "general", "images", "videos", "news", "map",
            "music", "it", "science", "files", "social media",
            "web", "apps", "books", "packages", "repos",
            "software wikis", "scientific publications", "q&a",
            "shopping", "movies", "translate", "radio", "lyrics",
            "currency", "weather", "other",
        ],
        "engines": [],
        "category_engines": {},
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/wanghaowei/searxng_http_mcp_server && .venv/bin/pytest tests/test_tools.py::TestFetchEngineInfo -v`

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_server/tools.py tests/test_tools.py
git commit -m "feat: extend fetch_engine_info to return category-engine mapping"
```

---

### Task 5: Add `engine_info` MCP tool

**Files:**
- Modify: `mcp_server/tools.py` (add new tool after autocomplete, add engine info cache)
- Modify: `tests/test_tools.py` (add new test class, update fixture and imports)

- [ ] **Step 1: Write the failing tests**

In `tests/test_tools.py`, update the import line to include `engine_info` and its cache:

```python
from mcp_server.tools import search, autocomplete, fetch_engine_info, engine_info, _cache, _engine_info_cache
```

Update the `clear_cache` fixture to also clear engine_info cache:

```python
@pytest.fixture(autouse=True)
def clear_cache():
    import mcp_server.tools as _mod
    _cache.clear()
    _mod._engine_info_cache = None
    _mod._engine_info_cache_ts = 0
    yield
    _cache.clear()
    _mod._engine_info_cache = None
    _mod._engine_info_cache_ts = 0
```

Then add a new test class at the end:

```python
class TestEngineInfoTool:
    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_engine_info_basic(self, mock_client_cls):
        response = _make_httpx_response({
            "categories": {"general": {}, "science": {}},
            "engines": [
                {"name": "google", "enabled": True, "categories": ["general"]},
                {"name": "arxiv", "enabled": True, "categories": ["science"]},
            ],
        })
        mock_client_cls.return_value = _make_mock_client(response)

        result = await engine_info()
        data = json.loads(result)

        assert "general" in data["categories"]
        assert "google" in data["engines"]
        assert "google" in data["category_engines"]["general"]
        assert "arxiv" in data["category_engines"]["science"]

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_engine_info_fallback(self, mock_client_cls):
        mock_client_cls.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        result = await engine_info()
        data = json.loads(result)

        assert "general" in data["categories"]
        assert data["engines"] == []
        assert data["category_engines"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/wanghaowei/searxng_http_mcp_server && .venv/bin/pytest tests/test_tools.py::TestEngineInfoTool -v`

Expected: FAIL — `engine_info` not found in imports.

- [ ] **Step 3: Add `engine_info` tool to `mcp_server/tools.py`**

Add after the `autocomplete` function (before `cleanup`):

```python
_engine_info_cache: dict | None = None
_engine_info_cache_ts: float = 0
ENGINE_INFO_CACHE_TTL = 300


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def engine_info() -> str:
    """Get available search engines and categories from the SearXNG instance.

    Returns the list of enabled engines grouped by category.
    Use this to discover what engines and categories are available
    before calling search with specific engines or categories filters.
    """
    global _engine_info_cache, _engine_info_cache_ts
    now = time.monotonic()
    if _engine_info_cache is not None and now - _engine_info_cache_ts < ENGINE_INFO_CACHE_TTL:
        return json.dumps(_engine_info_cache, ensure_ascii=False)

    info = await fetch_engine_info()
    _engine_info_cache = info
    _engine_info_cache_ts = now
    return json.dumps(info, ensure_ascii=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/wanghaowei/searxng_http_mcp_server && .venv/bin/pytest tests/test_tools.py::TestEngineInfoTool -v`

Expected: All PASS.

- [ ] **Step 5: Run full test suite**

Run: `cd /Users/wanghaowei/searxng_http_mcp_server && .venv/bin/pytest tests/test_tools.py -v`

Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add mcp_server/tools.py tests/test_tools.py
git commit -m "feat: add engine_info MCP tool with category-engine mapping and caching"
```

---

### Task 6: Simplify dynamic description injection in `app.py`

**Files:**
- Modify: `mcp_server/app.py:22-36` (lifespan description injection)

- [ ] **Step 1: Replace description injection block**

In `mcp_server/app.py`, replace lines 22-36 (the `info = await fetch_engine_info()` block inside lifespan) with:

```python
            info = await fetch_engine_info()
            if info["categories"]:
                categories_str = ", ".join(info["categories"])
                search_tool = mcp._tool_manager._tools.get("search")
                if search_tool:
                    original_desc = search_tool.description or ""
                    search_tool.description = (
                        f"{original_desc}\n\n"
                        f"Available categories: {categories_str}\n"
                        f"Use the engine_info tool to discover available engines and their categories."
                    )
```

- [ ] **Step 2: Run full test suite**

Run: `cd /Users/wanghaowei/searxng_http_mcp_server && .venv/bin/pytest tests/test_tools.py -v`

Expected: All PASS (app.py lifespan is not exercised in unit tests).

- [ ] **Step 3: Commit**

```bash
git add mcp_server/app.py
git commit -m "refactor: simplify dynamic description injection, remove engines list

Categories list kept (short, useful as quick reference).
Engines list removed (long, now available via engine_info tool)."
```

---

### Task 7: Verify generated JSON schemas

**Files:** None modified — verification only.

- [ ] **Step 1: Dump and verify all tool schemas**

Run:

```bash
cd /Users/wanghaowei/searxng_http_mcp_server && .venv/bin/python -c "
import json
from mcp_server.tools import mcp

tools = mcp._tool_manager.list_tools()
for t in tools:
    print(f'=== {t.name} ===')
    print(f'Description: {t.description[:80]}...')
    print(f'Annotations: {t.annotations}')
    print(json.dumps(t.parameters, indent=2))
    print()
"
```

Expected output should show:
- **search**: All parameters have `description` field. `time_range` has `anyOf` with `enum` + `null`. `safesearch` has `enum: [0, 1, 2]`. `pages` has `minimum: 1, maximum: 5`. `format` has `enum: ["compact", "full"]`. Annotations present.
- **autocomplete**: `query` has `description`. Annotations present.
- **engine_info**: No parameters (empty properties). Annotations present.

- [ ] **Step 2: Run full test suite one final time**

Run: `cd /Users/wanghaowei/searxng_http_mcp_server && .venv/bin/pytest tests/test_tools.py -v`

Expected: All PASS.

- [ ] **Step 3: Final commit if any cleanup needed**

If no changes needed, skip this step.
