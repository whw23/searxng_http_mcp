from unittest.mock import AsyncMock, patch, MagicMock

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient

from mcp_server.proxy import ReverseProxyApp


def _make_upstream_response(content=b"<html>OK</html>", status_code=200,
                            content_type="text/html"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = MagicMock()
    resp.headers.items.return_value = [("content-type", content_type)]
    resp.content = content
    return resp


def _make_mock_client(response):
    mock_client = AsyncMock()
    mock_client.request.return_value = response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestReverseProxy:
    @patch("mcp_server.proxy.httpx.AsyncClient")
    def test_proxy_get_request(self, mock_client_cls):
        response = _make_upstream_response(b"<html>SearXNG</html>")
        mock_client_cls.return_value = _make_mock_client(response)

        proxy = ReverseProxyApp(upstream="http://127.0.0.1:8080")
        app = Starlette(routes=[Mount("/", app=proxy)])
        client = TestClient(app)

        resp = client.get("/")
        assert resp.status_code == 200
        assert b"SearXNG" in resp.content

    @patch("mcp_server.proxy.httpx.AsyncClient")
    def test_proxy_preserves_query_params(self, mock_client_cls):
        response = _make_upstream_response(b'{"results": []}',
                                           content_type="application/json")
        mock_client = _make_mock_client(response)
        mock_client_cls.return_value = mock_client

        proxy = ReverseProxyApp(upstream="http://127.0.0.1:8080")
        app = Starlette(routes=[Mount("/", app=proxy)])
        client = TestClient(app)

        resp = client.get("/search?q=test&format=json")
        assert resp.status_code == 200

        call_args = mock_client.request.call_args
        assert "q=test" in str(call_args)

    @patch("mcp_server.proxy.httpx.AsyncClient")
    def test_proxy_post_request(self, mock_client_cls):
        response = _make_upstream_response()
        mock_client_cls.return_value = _make_mock_client(response)

        proxy = ReverseProxyApp(upstream="http://127.0.0.1:8080")
        app = Starlette(routes=[Mount("/", app=proxy)])
        client = TestClient(app)

        resp = client.post("/search", data={"q": "test"})
        assert resp.status_code == 200

    @patch("mcp_server.proxy.httpx.AsyncClient")
    def test_proxy_strips_auth_headers(self, mock_client_cls):
        response = _make_upstream_response()
        mock_client = _make_mock_client(response)
        mock_client_cls.return_value = mock_client

        proxy = ReverseProxyApp(upstream="http://127.0.0.1:8080")
        app = Starlette(routes=[Mount("/", app=proxy)])
        client = TestClient(app)

        client.get("/", headers={
            "x-api-key": "secret",
            "Authorization": "Basic abc",
        })

        call_args = mock_client.request.call_args
        forwarded_headers = call_args[1]["headers"]
        assert "x-api-key" not in forwarded_headers
        assert "authorization" not in forwarded_headers
