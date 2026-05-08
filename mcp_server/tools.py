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
    all_answers: set[str] = set()
    all_suggestions: set[str] = set()
    all_corrections: set[str] = set()
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
