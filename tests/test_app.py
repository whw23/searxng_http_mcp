import base64
from unittest.mock import patch, AsyncMock, MagicMock

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


class TestAppNoAuth:
    @patch.dict("os.environ", {}, clear=True)
    def test_mcp_endpoint_accessible(self):
        from mcp_server.app import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/mcp")
        assert resp.status_code != 404

    @patch.dict("os.environ", {}, clear=True)
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
