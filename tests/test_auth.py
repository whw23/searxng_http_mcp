import base64

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from mcp_server.auth import AuthMiddleware


def _make_app(api_key: str | None = None):
    async def homepage(request):
        return PlainTextResponse("OK")

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(AuthMiddleware, api_key=api_key)
    return app


class TestAuthMiddlewareNoKey:
    def test_no_key_configured_passes_through(self):
        client = TestClient(_make_app(api_key=None))
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.text == "OK"

    def test_empty_key_passes_through(self):
        client = TestClient(_make_app(api_key=""))
        resp = client.get("/")
        assert resp.status_code == 200


class TestAuthMiddlewareXApiKey:
    def test_valid_x_api_key(self):
        client = TestClient(_make_app(api_key="secret123"))
        resp = client.get("/", headers={"x-api-key": "secret123"})
        assert resp.status_code == 200

    def test_invalid_x_api_key(self):
        client = TestClient(_make_app(api_key="secret123"))
        resp = client.get("/", headers={"x-api-key": "wrong"})
        assert resp.status_code == 401

    def test_missing_credentials(self):
        client = TestClient(_make_app(api_key="secret123"))
        resp = client.get("/")
        assert resp.status_code == 401
        assert "Basic" in resp.headers.get("www-authenticate", "")


class TestAuthMiddlewareBasicAuth:
    def test_valid_basic_auth(self):
        client = TestClient(_make_app(api_key="secret123"))
        creds = base64.b64encode(b":secret123").decode()
        resp = client.get("/", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 200

    def test_basic_auth_with_username(self):
        client = TestClient(_make_app(api_key="secret123"))
        creds = base64.b64encode(b"anyuser:secret123").decode()
        resp = client.get("/", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 200

    def test_invalid_basic_auth(self):
        client = TestClient(_make_app(api_key="secret123"))
        creds = base64.b64encode(b":wrongkey").decode()
        resp = client.get("/", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 401

    def test_malformed_basic_auth(self):
        client = TestClient(_make_app(api_key="secret123"))
        resp = client.get("/", headers={"Authorization": "Basic notbase64!!!"})
        assert resp.status_code == 401
