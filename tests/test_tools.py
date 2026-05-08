import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from mcp_server.tools import search, autocomplete, fetch_engine_info


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
        assert data["suggestions"] == ["example query"]

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_with_pages(self, mock_client_cls, mock_search_response):
        response = _make_httpx_response(mock_search_response)
        mock_client = _make_mock_client(response)
        mock_client_cls.return_value = mock_client

        result = await search(query="test", pages=3)
        data = json.loads(result)

        assert mock_client.get.call_count == 3
        assert data["number_of_results"] == 3

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_pages_clamped_to_5(self, mock_client_cls, mock_search_response):
        response = _make_httpx_response(mock_search_response)
        mock_client = _make_mock_client(response)
        mock_client_cls.return_value = mock_client

        await search(query="test", pages=10)

        assert mock_client.get.call_count == 5

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_search_trims_results(self, mock_client_cls):
        response = _make_httpx_response({
            "results": [
                {
                    "title": "Test",
                    "url": "https://example.com",
                    "content": "Content",
                    "engines": ["google"],
                    "score": 1.0,
                    "category": "general",
                    "parsed_url": ["https", "example.com", "/", "", "", ""],
                    "positions": [1],
                    "template": "default.html",
                }
            ],
            "answers": [],
            "corrections": [],
            "suggestions": [],
            "infoboxes": [],
        })
        mock_client_cls.return_value = _make_mock_client(response)

        result = await search(query="test")
        data = json.loads(result)

        r = data["results"][0]
        assert "parsed_url" not in r
        assert "positions" not in r
        assert "template" not in r
        assert r["title"] == "Test"


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
                {"name": "google", "enabled": True},
                {"name": "bing", "enabled": True},
                {"name": "disabled_engine", "enabled": False},
            ],
        })
        mock_client_cls.return_value = _make_mock_client(response)

        info = await fetch_engine_info()

        assert "general" in info["categories"]
        assert "google" in info["engines"]
        assert "disabled_engine" not in info["engines"]

    @pytest.mark.anyio
    @patch("mcp_server.tools.httpx.AsyncClient")
    async def test_fetch_engine_info_fallback(self, mock_client_cls):
        mock_client_cls.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        info = await fetch_engine_info()

        assert "general" in info["categories"]
        assert info["engines"] == []
