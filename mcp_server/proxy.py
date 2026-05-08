import httpx
from starlette.requests import Request
from starlette.types import Receive, Scope, Send

EXCLUDED_REQUEST_HEADERS = {
    "host", "x-api-key", "authorization", "accept-encoding",
}
EXCLUDED_RESPONSE_HEADERS = {"transfer-encoding", "content-encoding", "content-length"}


class ReverseProxyApp:
    """ASGI app that proxies all requests to an upstream HTTP server."""

    def __init__(self, upstream: str):
        self.upstream = upstream.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient()
        return self._client

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return

        request = Request(scope, receive)
        path = scope.get("path", "/")
        query_string = scope.get("query_string", b"").decode()
        url = f"{self.upstream}{path}"
        if query_string:
            url = f"{url}?{query_string}"

        body = await request.body()

        headers_to_forward = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in EXCLUDED_REQUEST_HEADERS
        }

        client_host = request.client.host if request.client else "127.0.0.1"
        original_host = request.headers.get("host", "localhost:8888")
        headers_to_forward.setdefault("x-forwarded-for", client_host)
        headers_to_forward.setdefault("x-real-ip", client_host)
        headers_to_forward["host"] = original_host
        headers_to_forward["accept-encoding"] = "identity"

        client = await self._get_client()
        upstream_resp = await client.request(
            method=request.method,
            url=url,
            headers=headers_to_forward,
            content=body if body else None,
            timeout=30.0,
            follow_redirects=False,
        )

        resp_headers: list[tuple[bytes, bytes]] = []
        for key, value in upstream_resp.headers.raw:
            if key.decode().lower() not in EXCLUDED_RESPONSE_HEADERS:
                resp_headers.append((key, value))

        content = upstream_resp.content
        resp_headers.append((b"content-length", str(len(content)).encode()))

        await send({
            "type": "http.response.start",
            "status": upstream_resp.status_code,
            "headers": resp_headers,
        })
        await send({
            "type": "http.response.body",
            "body": content,
        })

    async def aclose(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
