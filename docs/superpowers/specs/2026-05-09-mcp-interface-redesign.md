# MCP Interface Redesign

## Goals

1. Enhance schema quality for all existing tools (add descriptions, Literal constraints, Field range limits, ToolAnnotations)
2. Add `engine_info` tool for querying available engines and categories with their mapping
3. Streamline dynamic description injection (keep categories, remove engines list)
4. NOT in scope: URL content fetching, search tool splitting, SearXNG config modification

## Approach

Use `Annotated[type, Field()]` pattern on existing function signatures (no Pydantic BaseModel refactor). This is the same approach used by competitor `aicrafted/searxng-mcp` and is native to FastMCP.

---

## Tool 1: `search` — Signature Redesign

### Current Problems

- No `description` on any parameter — AI clients see only auto-generated titles like "Time Range"
- No `enum` constraints — `time_range`, `format`, `safesearch` accept any string/int
- No range constraints — `pages` (1-5), `max_results` (1-100), `pageno` (>=1) not enforced in schema
- Missing `"week"` in time_range — confirmed valid in SearXNG source (`searx/webadapter.py`)
- No ToolAnnotations — clients don't know the tool is read-only and safe

### New Signature

```python
from typing import Annotated, Literal
from pydantic import Field
from mcp.types import ToolAnnotations

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
```

### Code Changes Required

- `if time_range:` → `if time_range is not None:` (since default changes from `""` to `None`)
- Remove runtime clamp `pages = max(1, min(pages, 5))` — Pydantic enforces `ge=1, le=5`
- Remove runtime clamp `max_results = max(1, min(max_results, 100))` — Pydantic enforces `ge=1, le=100`
- **Behavior change:** invalid values (e.g., `pages=10`) now return a validation error instead of being silently clamped. This is the correct behavior — clients should respect the schema constraints.
- Add `from typing import Annotated, Literal` and `from pydantic import Field`
- Add `from mcp.types import ToolAnnotations`

---

## Tool 2: `autocomplete` — Signature Redesign

### New Signature

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

No logic changes needed, only signature annotations and ToolAnnotations.

---

## Tool 3: `engine_info` — New Tool

### Purpose

Allow AI clients to discover available engines and categories on demand, with category-engine mapping. Most searches use default settings; this tool is for cases where the AI needs to target specific engines or categories.

### Signature

```python
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
```

### Return Structure

```json
{
  "categories": ["general", "images", "videos", "news", ...],
  "engines": ["google", "bing", "duckduckgo", ...],
  "category_engines": {
    "general": ["google", "bing", "duckduckgo", "brave", "wikipedia", ...],
    "science": ["arxiv", "google scholar", "pubmed", ...],
    "it": ["github", "docker hub", "pypi", "npm", "stack overflow", ...],
    ...
  }
}
```

### Implementation

- Extend existing `fetch_engine_info()` to also return `category_engines` mapping
- SearXNG `/config` API provides each engine's `categories` field — iterate engines to build the mapping
- Cache the result with a longer TTL than search results (e.g., 300s) since engine config rarely changes
- Fallback on failure: hardcoded categories + empty engines/mapping (consistent with existing fallback)

---

## Dynamic Description Injection Changes

### File: `app.py` lifespan

**Before:**
```python
search_tool.description = (
    f"{original_desc}\n\n"
    f"Available categories: {categories_str}\n"
)
if info["engines"]:
    engines_str = ", ".join(info["engines"][:50])
    search_tool.description += (
        f"Available engines (top 50): {engines_str}"
    )
```

**After:**
```python
search_tool.description = (
    f"{original_desc}\n\n"
    f"Available categories: {categories_str}\n"
    f"Use the engine_info tool to discover available engines and their categories."
)
```

Rationale: categories list is short (~26 items), engines list is long (93 enabled, was truncated to 50). With the new `engine_info` tool, AI can query engines on demand.

---

## Test Updates

### Existing Tests to Update

- `test_search_basic` — update mock call args (time_range `None` instead of `""`)
- `test_search_pages_clamped_to_5` — remove or rewrite; Pydantic now rejects invalid values instead of clamping
- `test_fetch_engine_info_success` — extend to verify `category_engines` mapping in return value

### New Tests to Add

- `test_engine_info` — basic call returns categories, engines, and category_engines
- `test_engine_info_fallback` — returns hardcoded categories on SearXNG failure
- `test_engine_info_caching` — second call within TTL returns cached result
- `test_search_time_range_week` — verify `"week"` is accepted
- `test_search_time_range_null` — verify `None` default means no time_range param sent to SearXNG

---

## Files Changed

| File | Changes |
|------|---------|
| `mcp_server/tools.py` | New imports, search/autocomplete signature redesign, new engine_info tool, extend fetch_engine_info() |
| `mcp_server/app.py` | Simplify dynamic description injection |
| `tests/test_tools.py` | Update existing tests, add new tests for engine_info and time_range |

---

## Expected JSON Schema Output (search tool)

After redesign, clients will see:

```json
{
  "properties": {
    "query": {
      "type": "string",
      "description": "The search query to use"
    },
    "time_range": {
      "anyOf": [
        { "enum": ["day", "week", "month", "year"] },
        { "type": "null" }
      ],
      "default": null,
      "description": "Restrict results to those published within this time window"
    },
    "safesearch": {
      "enum": [0, 1, 2],
      "default": 0,
      "description": "Safe search level: 0=off, 1=moderate, 2=strict"
    },
    "pages": {
      "type": "integer",
      "minimum": 1,
      "maximum": 5,
      "default": 1,
      "description": "Number of pages to fetch in parallel (multi-page fanout)"
    },
    "format": {
      "enum": ["compact", "full"],
      "default": "compact",
      "description": "Result detail level: 'compact' returns title/url/content only, 'full' includes engines/score/category/date/thumbnails"
    }
  },
  "required": ["query"],
  "type": "object"
}
```

vs current (no descriptions, no enums, no constraints):

```json
{
  "properties": {
    "query": { "title": "Query", "type": "string" },
    "time_range": { "default": "", "title": "Time Range", "type": "string" },
    "safesearch": { "default": 0, "title": "Safesearch", "type": "integer" },
    "pages": { "default": 1, "title": "Pages", "type": "integer" },
    "format": { "default": "compact", "title": "Format", "type": "string" }
  }
}
```
