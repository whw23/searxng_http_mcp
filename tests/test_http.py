"""Integration tests for MCP HTTP transport mode."""

import json
import socket
import threading
import time

import pytest
import uvicorn
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from unittest.mock import AsyncMock, MagicMock, patch

import httpx


MOCK_SEARCH_RESPONSE = {
    "results": [
        {
            "title": "HTTP Test Result",
            "url": "https://example.com",
            "content": "Test content from HTTP mock.",
            "engines": ["google"],
            "score": 5.0,
            "category": "general",
        }
    ],
    "answers": [],
    "suggestions": ["http suggestion"],
    "corrections": [],
    "infoboxes": [],
    "unresponsive_engines": [],
}

MOCK_AUTOCOMPLETE_RESPONSE = ["http query", "http test"]

MOCK_CONFIG_RESPONSE = {
    "categories": ["general", "images", "news"],
    "engines": [
        {"name": "google", "enabled": True, "categories": ["general"]},
        {"name": "bing", "enabled": True, "categories": ["general", "images"]},
    ],
}


def _mock_response(data):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = data
    return resp


async def _mock_get(url, **kwargs):
    if "/search" in str(url):
        return _mock_response(MOCK_SEARCH_RESPONSE)
    if "/autocomplete" in str(url):
        return _mock_response(MOCK_AUTOCOMPLETE_RESPONSE)
    if "/config" in str(url):
        return _mock_response(MOCK_CONFIG_RESPONSE)
    resp = _mock_response({"error": "not found"})
    resp.status_code = 404
    return resp


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_url():
    """Start a real HTTP MCP server with mocked SearXNG and return its URL."""
    import mcp_server.tools as tools_mod

    prev_client = tools_mod._http_client
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = _mock_get
    mock_client.is_closed = False
    tools_mod._http_client = mock_client

    port = _find_free_port()

    with patch.dict("os.environ", {"API_KEY": "", "SEARXNG_URL": "http://mock:8080"}):
        from mcp_server.app import create_app
        app = create_app()

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if server.started:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Server did not start in time")

        yield f"http://127.0.0.1:{port}/mcp/"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        assert not thread.is_alive(), "Server thread did not shut down cleanly"

        tools_mod._http_client = prev_client
        tools_mod._cache.clear()
        tools_mod._engine_info_cache = None
        tools_mod._engine_info_cache_ts = 0


@pytest.fixture
async def session(server_url):
    """Connect to the HTTP MCP server and return a session."""
    async with streamable_http_client(server_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as s:
            await s.initialize()
            yield s


@pytest.mark.anyio
async def test_list_tools(session):
    result = await session.list_tools()
    tool_names = {t.name for t in result.tools}
    assert tool_names == {"search", "autocomplete", "engine_info"}


@pytest.mark.anyio
async def test_search(session):
    result = await session.call_tool("search", {"query": "test"})
    assert not result.isError
    data = json.loads(result.content[0].text)
    assert "results" in data
    assert len(data["results"]) > 0
    assert data["results"][0]["title"] == "HTTP Test Result"


@pytest.mark.anyio
async def test_search_full_format(session):
    result = await session.call_tool(
        "search", {"query": "test", "format": "full", "max_results": 1}
    )
    assert not result.isError
    data = json.loads(result.content[0].text)
    assert data["results"][0].get("engines") is not None


@pytest.mark.anyio
async def test_autocomplete(session):
    result = await session.call_tool("autocomplete", {"query": "http"})
    assert not result.isError
    data = json.loads(result.content[0].text)
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.anyio
async def test_engine_info(session):
    result = await session.call_tool("engine_info", {})
    assert not result.isError
    data = json.loads(result.content[0].text)
    assert "categories" in data
    assert "engines" in data
    assert "category_engines" in data
    assert "general" in data["categories"]
