import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from mcp_server.tools import search, autocomplete, fetch_engine_info, engine_info, _cache


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
                "parsed_url": ["https", "example.com"],
                "positions": [1],
                "template": "default.html",
            }
        ],
        "answers": ["42"],
        "corrections": [],
        "suggestions": ["example query"],
        "infoboxes": [],
        "unresponsive_engines": [],
        "number_of_results": 1,
    }


@pytest.fixture
def mock_autocomplete_response():
    return ["python tutorial", "python download", "python documentation"]


def _make_httpx_response(data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    return resp


def _make_mock_client(response):
    mock_client = AsyncMock()
    mock_client.get.return_value = response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestSearchTool:
    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_basic(self, mock_client_cls, mock_search_response):
        response = _make_httpx_response(mock_search_response)
        mock_client_cls.return_value = _make_mock_client(response)

        result = await search(query="test")
        data = json.loads(result)

        assert data["number_of_results"] == 1
        assert data["results"][0]["title"] == "Example Result"
        assert data["answers"] == ["42"]

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_compact_format(self, mock_client_cls, mock_search_response):
        response = _make_httpx_response(mock_search_response)
        mock_client_cls.return_value = _make_mock_client(response)

        result = await search(query="test", format="compact")
        data = json.loads(result)

        r = data["results"][0]
        assert "title" in r
        assert "url" in r
        assert "content" in r
        assert "engines" not in r
        assert "score" not in r
        assert "parsed_url" not in r

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_full_format(self, mock_client_cls, mock_search_response):
        response = _make_httpx_response(mock_search_response)
        mock_client_cls.return_value = _make_mock_client(response)

        result = await search(query="test", format="full")
        data = json.loads(result)

        r = data["results"][0]
        assert "title" in r
        assert "engines" in r
        assert "score" in r
        assert "parsed_url" not in r
        assert "template" not in r

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_max_results(self, mock_client_cls):
        many_results = {
            "results": [
                {"title": f"Result {i}", "url": f"https://example.com/{i}", "content": f"Content {i}"}
                for i in range(20)
            ],
            "answers": [],
            "corrections": [],
            "suggestions": [],
            "infoboxes": [],
            "unresponsive_engines": [],
        }
        response = _make_httpx_response(many_results)
        mock_client_cls.return_value = _make_mock_client(response)

        result = await search(query="test", max_results=5)
        data = json.loads(result)

        assert data["number_of_results"] == 5
        assert len(data["results"]) == 5

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_default_max_results(self, mock_client_cls):
        many_results = {
            "results": [
                {"title": f"Result {i}", "url": f"https://example.com/{i}", "content": f"Content {i}"}
                for i in range(20)
            ],
            "answers": [],
            "corrections": [],
            "suggestions": [],
            "infoboxes": [],
            "unresponsive_engines": [],
        }
        response = _make_httpx_response(many_results)
        mock_client_cls.return_value = _make_mock_client(response)

        result = await search(query="test")
        data = json.loads(result)

        assert data["number_of_results"] == 10

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_with_pages(self, mock_client_cls, mock_search_response):
        response = _make_httpx_response(mock_search_response)
        mock_client = _make_mock_client(response)
        mock_client_cls.return_value = mock_client

        result = await search(query="test", pages=3, max_results=100)
        data = json.loads(result)

        assert mock_client.get.call_count == 3
        assert data["number_of_results"] == 3

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_cache(self, mock_client_cls, mock_search_response):
        response = _make_httpx_response(mock_search_response)
        mock_client = _make_mock_client(response)
        mock_client_cls.return_value = mock_client

        result1 = await search(query="test")
        result2 = await search(query="test")

        assert mock_client.get.call_count == 1
        data2 = json.loads(result2)
        assert data2.get("cached") is True

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_zero_results_diagnostics(self, mock_client_cls):
        empty_response = {
            "results": [],
            "answers": [],
            "corrections": [],
            "suggestions": [],
            "infoboxes": [],
            "unresponsive_engines": [["google", "timeout"]],
        }
        response = _make_httpx_response(empty_response)
        mock_client_cls.return_value = _make_mock_client(response)

        result = await search(query="xyznonexistent123", language="zh")
        data = json.loads(result)

        assert data["message"] == "No results found"
        assert data["query"] == "xyznonexistent123"
        assert len(data["suggestions"]) > 0
        assert any("language" in s for s in data["suggestions"])
        assert "google: timeout" in data["errors"]

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_error_handling(self, mock_client_cls):
        response = _make_httpx_response({}, status_code=500)
        mock_client_cls.return_value = _make_mock_client(response)

        result = await search(query="test")
        data = json.loads(result)

        assert data["message"] == "No results found"


class TestAutocompleteTool:
    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_autocomplete(self, mock_client_cls, mock_autocomplete_response):
        response = _make_httpx_response(mock_autocomplete_response)
        mock_client_cls.return_value = _make_mock_client(response)

        result = await autocomplete(query="python")
        data = json.loads(result)

        assert "python tutorial" in data
        assert len(data) == 3

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_autocomplete_error(self, mock_client_cls):
        response = _make_httpx_response({}, status_code=500)
        mock_client_cls.return_value = _make_mock_client(response)

        result = await autocomplete(query="test")
        data = json.loads(result)

        assert "error" in data


class TestFetchEngineInfo:
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
