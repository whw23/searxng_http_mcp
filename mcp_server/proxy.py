import httpx
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Receive, Scope, Send


class ReverseProxyApp:
    """ASGI app that proxies all requests to an upstream HTTP server."""

    def __init__(self, upstream: str):
        self.upstream = upstream.rstrip("/")

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
            if k.lower() not in ("host", "x-api-key", "authorization")
        }

        async with httpx.AsyncClient() as client:
            upstream_resp = await client.request(
                method=request.method,
                url=url,
                headers=headers_to_forward,
                content=body if body else None,
                timeout=30.0,
            )

        excluded_headers = {"transfer-encoding", "content-encoding", "content-length"}
        resp_headers = {
            k: v
            for k, v in upstream_resp.headers.items()
            if k.lower() not in excluded_headers
        }

        response = Response(
            content=upstream_resp.content,
            status_code=upstream_resp.status_code,
            headers=resp_headers,
        )
        await response(scope, receive, send)
