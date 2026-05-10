"""Mock MCP stdio server for integration tests.

Patches httpx so the MCP tools work without a real SearXNG instance.
Launched as a subprocess by test_stdio.py.
"""

from unittest.mock import AsyncMock, MagicMock

import httpx

MOCK_SEARCH_RESPONSE = {
    "results": [
        {
            "title": "Test Result",
            "url": "https://example.com",
            "content": "Test content from mock.",
            "engines": ["google"],
            "score": 5.0,
            "category": "general",
        }
    ],
    "answers": [],
    "suggestions": ["test suggestion"],
    "corrections": [],
    "infoboxes": [],
    "unresponsive_engines": [],
}

MOCK_AUTOCOMPLETE_RESPONSE = ["test query", "test automation", "testing"]

MOCK_CONFIG_RESPONSE = {
    "categories": ["general", "images", "news"],
    "engines": [
        {"name": "google", "enabled": True, "categories": ["general"]},
        {"name": "bing", "enabled": True, "categories": ["general", "images"]},
        {"name": "google news", "enabled": True, "categories": ["news"]},
    ],
}


def _mock_response(data: dict | list, status_code: int = 200) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    return resp


async def _mock_get(url: str, **kwargs) -> httpx.Response:
    if "/search" in url:
        return _mock_response(MOCK_SEARCH_RESPONSE)
    if "/autocomplete" in url:
        return _mock_response(MOCK_AUTOCOMPLETE_RESPONSE)
    if "/config" in url:
        return _mock_response(MOCK_CONFIG_RESPONSE)
    return _mock_response({"error": "not found"}, 404)


if __name__ == "__main__":
    import mcp_server.tools as tools_mod

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = _mock_get
    mock_client.is_closed = False
    tools_mod._http_client = mock_client

    tools_mod.mcp.run(transport="stdio")
