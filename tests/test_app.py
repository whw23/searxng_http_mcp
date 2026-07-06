import base64
import os
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from mcp.server.fastmcp import FastMCP
from starlette.testclient import TestClient


def _make_proxy_mock():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = MagicMock()
    mock_response.headers.items.return_value = [("content-type", "text/html")]
    mock_response.content = b"<html>SearXNG</html>"

    mock_client = AsyncMock()
    mock_client.request.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.fixture(scope="module")
def no_auth_client():
    """Shared TestClient with lifespan active and no API key."""
    os.environ.pop("API_KEY", None)
    test_mcp = FastMCP(
        "test",
        stateless_http=True,
        json_response=True,
        streamable_http_path="/",
    )

    @test_mcp.tool()
    async def ping() -> str:
        return "pong"

    from mcp_server.app import create_app

    app = create_app(mcp_instance=test_mcp)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


class TestAppNoAuth:
    def test_mcp_endpoint_accessible(self, no_auth_client):
        resp = no_auth_client.get("/mcp")
        assert resp.status_code < 500

    def test_mcp_without_slash_hits_mcp_app(self, no_auth_client):
        with patch("mcp_server.proxy.httpx.AsyncClient") as mock_client_cls:
            resp = no_auth_client.get("/mcp")
            # The MCP app is reached directly; no redirect and no proxy fallback.
            assert resp.status_code < 500
            assert "location" not in resp.headers
            mock_client_cls.assert_not_called()

    def test_mcp_post_without_slash_hits_mcp_app(self, no_auth_client):
        with patch("mcp_server.proxy.httpx.AsyncClient") as mock_client_cls:
            resp = no_auth_client.post("/mcp", headers={"accept": "application/json"})
            # The MCP app is reached directly; no proxy fallback.
            assert resp.status_code < 500
            mock_client_cls.assert_not_called()

    def test_mcp_with_slash_hits_mcp_app(self, no_auth_client):
        with patch("mcp_server.proxy.httpx.AsyncClient") as mock_client_cls:
            resp = no_auth_client.get("/mcp/")
            # The MCP app is reached (it does not fall through to the proxy).
            assert resp.status_code < 500
            assert "location" not in resp.headers
            mock_client_cls.assert_not_called()

    def test_mcp_query_string_reaches_mcp_app(self, no_auth_client):
        with patch("mcp_server.proxy.httpx.AsyncClient") as mock_client_cls:
            resp = no_auth_client.get("/mcp?foo=1")
            # Query string is preserved and the request reaches the MCP app.
            assert resp.status_code < 500
            assert "location" not in resp.headers
            mock_client_cls.assert_not_called()

    @patch("mcp_server.proxy.httpx.AsyncClient")
    def test_proxy_route_forwards(self, mock_client_cls):
        mock_client_cls.return_value = _make_proxy_mock()

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
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/mcp", headers={"x-api-key": "testkey"})
        assert resp.status_code != 401

    @patch.dict("os.environ", {"API_KEY": "testkey"})
    @patch("mcp_server.proxy.httpx.AsyncClient")
    def test_proxy_with_basic_auth(self, mock_client_cls):
        mock_client_cls.return_value = _make_proxy_mock()

        from mcp_server.app import create_app

        app = create_app()
        client = TestClient(app)
        creds = base64.b64encode(b":testkey").decode()
        resp = client.get(
            "/some-path",
            headers={"Authorization": f"Basic {creds}"},
        )
        assert resp.status_code != 401
