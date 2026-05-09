import asyncio
import json
import os
import time
from typing import Annotated, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

SEARXNG_BASE_URL = os.environ.get("SEARXNG_URL", "http://127.0.0.1:8080")
CACHE_TTL = int(os.environ.get("CACHE_TTL", "60"))
MAX_CACHE_SIZE = 256

mcp = FastMCP(
    "SearXNG",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    host="0.0.0.0",
)

_http_client: httpx.AsyncClient | None = None
_cache: dict[str, tuple[float, dict]] = {}


async def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient()
    return _http_client

COMPACT_FIELDS = frozenset({"title", "url", "content"})
FULL_FIELDS = frozenset({
    "title", "url", "content", "engines", "score",
    "category", "publishedDate", "thumbnail", "img_src",
})


def _cache_key(params: dict) -> str:
    return json.dumps(params, sort_keys=True)


def _get_cached(key: str) -> dict | None:
    if key in _cache:
        ts, data = _cache[key]
        if time.monotonic() - ts < CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: dict):
    now = time.monotonic()
    expired = [k for k, (ts, _) in _cache.items() if now - ts >= CACHE_TTL]
    for k in expired:
        del _cache[k]
    if len(_cache) >= MAX_CACHE_SIZE:
        oldest = min(_cache, key=lambda k: _cache[k][0])
        del _cache[oldest]
    _cache[key] = (now, data)


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
            "music", "it", "science", "files", "social media",
            "web", "apps", "books", "packages", "repos",
            "software wikis", "scientific publications", "q&a",
            "shopping", "movies", "translate", "radio", "lyrics",
            "currency", "weather", "other",
        ],
        "engines": [],
    }


def _trim_result(result: dict, fields: list[str]) -> dict:
    """Keep only specified fields from a search result."""
    return {k: v for k, v in result.items() if k in fields and v}


def _build_diagnostics(query: str, params: dict, errors: list[str]) -> dict:
    """Build diagnostic info when search returns zero results."""
    tips = [
        "Try broader or different keywords",
        "Remove time_range filter if set",
        "Try different categories or engines",
    ]
    if params.get("language"):
        tips.append(f"Try removing language filter (currently: {params['language']})")
    if params.get("engines"):
        tips.append("Some specified engines may be unresponsive — try without engines filter")
    if params.get("time_range"):
        tips.append(f"Time range '{params['time_range']}' may be too restrictive")

    diag: dict = {
        "query": query,
        "message": "No results found",
        "suggestions": tips,
    }
    if errors:
        diag["errors"] = errors
    return diag


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

    cache_params = {**params, "pageno": pageno, "pages": pages}
    cache_k = _cache_key(cache_params)
    cached = _get_cached(cache_k)
    if cached is not None:
        results = cached["results"][:max_results]
        output = {**cached, "results": results, "number_of_results": len(results), "cached": True}
        return json.dumps(output, ensure_ascii=False)

    all_results = []
    all_answers: set[str] = set()
    all_suggestions: set[str] = set()
    all_corrections: set[str] = set()
    all_infoboxes = []
    errors: list[str] = []

    client = await _get_client()
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
            errors.append(str(resp))
            continue
        if resp.status_code != 200:
            errors.append(f"HTTP {resp.status_code}")
            continue
        data = resp.json()
        all_results.extend(_trim_result(r, fields) for r in data.get("results", []))
        all_answers.update(data.get("answers", []))
        all_suggestions.update(data.get("suggestions", []))
        all_corrections.update(data.get("corrections", []))
        all_infoboxes.extend(data.get("infoboxes", []))
        for engine_name, error_msg in data.get("unresponsive_engines", []):
            errors.append(f"{engine_name}: {error_msg}")

    if not all_results and not all_answers:
        return json.dumps(_build_diagnostics(query, params, errors), ensure_ascii=False)

    output: dict = {
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

    _set_cache(cache_k, output)

    results = output["results"][:max_results]
    return_data = {**output, "results": results, "number_of_results": len(results)}
    return json.dumps(return_data, ensure_ascii=False)


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
    client = await _get_client()
    resp = await client.get(
        f"{SEARXNG_BASE_URL}/autocomplete",
        params={"q": query},
        timeout=10.0,
    )
    if resp.status_code != 200:
        return json.dumps({"error": f"Autocomplete failed with status {resp.status_code}"})
    return json.dumps(resp.json(), ensure_ascii=False)


async def cleanup():
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
