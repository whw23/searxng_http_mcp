import base64
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class AuthMiddleware(BaseHTTPMiddleware):
    """Authenticate requests via x-api-key header or HTTP Basic Auth."""

    def __init__(self, app, api_key: str | None = None):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        if not self.api_key:
            return await call_next(request)

        x_api_key = request.headers.get("x-api-key", "")
        if x_api_key and secrets.compare_digest(x_api_key, self.api_key):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                _, _, password = decoded.partition(":")
                if secrets.compare_digest(password, self.api_key):
                    return await call_next(request)
            except Exception:
                pass

        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="SearXNG MCP"'},
        )
