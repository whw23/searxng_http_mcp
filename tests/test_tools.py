import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from mcp_server.tools import (
    search, autocomplete, fetch_engine_info, engine_info, cleanup,
    _cache, _set_cache, _get_cached, _cache_key, MAX_CACHE_SIZE,
)


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

        await search(query="test")
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
    async def test_search_zero_results_with_engines_and_time_range(self, mock_client_cls):
        empty_response = {
            "results": [], "answers": [], "corrections": [],
            "suggestions": [], "infoboxes": [], "unresponsive_engines": [],
        }
        response = _make_httpx_response(empty_response)
        mock_client_cls.return_value = _make_mock_client(response)

        result = await search(query="test", engines="google", time_range="day")
        data = json.loads(result)

        assert data["message"] == "No results found"
        assert any("engines" in s for s in data["suggestions"])
        assert any("day" in s for s in data["suggestions"])

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_with_all_optional_params(self, mock_client_cls, mock_search_response):
        response = _make_httpx_response(mock_search_response)
        mock_client = _make_mock_client(response)
        mock_client_cls.return_value = mock_client

        await search(
            query="test", categories="news", engines="google",
            language="en", time_range="week", safesearch=1,
        )

        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["categories"] == "news"
        assert params["engines"] == "google"
        assert params["language"] == "en"
        assert params["time_range"] == "week"
        assert params["safesearch"] == "1"

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_corrections_and_infoboxes(self, mock_client_cls):
        response_data = {
            "results": [{"title": "R", "url": "https://r.com", "content": "c"}],
            "answers": [],
            "corrections": ["corrected query"],
            "suggestions": [],
            "infoboxes": [{"infobox": "test", "content": "info"}],
            "unresponsive_engines": [],
        }
        response = _make_httpx_response(response_data)
        mock_client_cls.return_value = _make_mock_client(response)

        result = await search(query="test")
        data = json.loads(result)

        assert data["corrections"] == ["corrected query"]
        assert len(data["infoboxes"]) == 1

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_exception_handling(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection reset")
        mock_client_cls.return_value = mock_client

        result = await search(query="test")
        data = json.loads(result)

        assert data["message"] == "No results found"

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


class TestCache:
    def test_cache_expiry(self):
        key = _cache_key({"q": "expired"})
        _set_cache(key, {"results": []})
        assert _get_cached(key) is not None

        ts, data = _cache[key]
        _cache[key] = (ts - 9999, data)
        assert _get_cached(key) is None
        assert key not in _cache

    def test_cache_eviction_when_full(self):
        for i in range(MAX_CACHE_SIZE):
            _set_cache(_cache_key({"q": f"query_{i}"}), {"results": []})
        assert len(_cache) == MAX_CACHE_SIZE

        _set_cache(_cache_key({"q": "overflow"}), {"results": []})
        assert len(_cache) == MAX_CACHE_SIZE

    def test_cache_expired_cleanup(self):
        _set_cache(_cache_key({"q": "old"}), {"results": []})
        key = _cache_key({"q": "old"})
        ts, data = _cache[key]
        _cache[key] = (ts - 9999, data)

        _set_cache(_cache_key({"q": "new"}), {"results": []})
        assert _cache_key({"q": "old"}) not in _cache


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
        mock_client = _make_mock_client(MagicMock())
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client_cls.return_value = mock_client

        info = await fetch_engine_info()

        assert "general" in info["categories"]
        assert info["engines"] == []
        assert info["category_engines"] == {}

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_fetch_engine_info_list_categories(self, mock_client_cls):
        response = _make_httpx_response({
            "categories": ["general", "images"],
            "engines": [{"name": "google", "enabled": True, "categories": ["general"]}],
        })
        mock_client_cls.return_value = _make_mock_client(response)

        info = await fetch_engine_info()

        assert info["categories"] == ["general", "images"]

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_fetch_engine_info_invalid_categories_type(self, mock_client_cls):
        response = _make_httpx_response({
            "categories": 42,
            "engines": [],
        })
        mock_client_cls.return_value = _make_mock_client(response)

        info = await fetch_engine_info()

        assert info["categories"] == []


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
        mock_client = _make_mock_client(MagicMock())
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client_cls.return_value = mock_client

        result = await engine_info()
        data = json.loads(result)

        assert "general" in data["categories"]
        assert data["engines"] == []
        assert data["category_engines"] == {}

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_engine_info_caching(self, mock_client_cls):
        response = _make_httpx_response({
            "categories": {"general": {}},
            "engines": [{"name": "google", "enabled": True, "categories": ["general"]}],
        })
        mock_client = _make_mock_client(response)
        mock_client_cls.return_value = mock_client

        await engine_info()
        await engine_info()

        assert mock_client.get.call_count == 1


class TestCleanup:
    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_cleanup_closes_client(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client_cls.return_value = mock_client

        import mcp_server.tools as _mod
        _mod._http_client = mock_client

        await cleanup()

        mock_client.aclose.assert_called_once()
        assert _mod._http_client is None

    @pytest.mark.anyio
    async def test_cleanup_no_client(self):
        import mcp_server.tools as _mod
        _mod._http_client = None
        await cleanup()
