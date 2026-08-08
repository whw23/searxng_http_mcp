import contextlib
import os

from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from mcp_server.auth import AuthMiddleware
from mcp_server.proxy import ReverseProxyApp
from mcp_server.tools import mcp as tools_mcp, fetch_engine_info, cleanup as tools_cleanup


class _MCPApp:
    """ASGI app wrapper that serves the MCP app at /mcp and /mcp/.

    When mounted at /mcp, Starlette sets the remaining path to /mcp/ and
    records the matched prefix in root_path. When routed via Route("/mcp"),
    the path is /mcp. The inner MCP app route is /, so normalize the bare
    /mcp case to / before dispatching.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket") and scope.get("path") in ("", "/mcp"):
            scope = dict(scope)
            scope["path"] = "/"
            scope["raw_path"] = b"/"
        await self.app(scope, receive, send)


def create_app(mcp_instance: MCPServer | None = None) -> Starlette:
    """Create the Starlette ASGI app with MCP, auth, and reverse proxy."""
    mcp = mcp_instance or tools_mcp

    api_key = os.environ.get("API_KEY", "")
    searxng_url = os.environ.get("SEARXNG_URL", "http://127.0.0.1:8080")

    proxy = ReverseProxyApp(upstream=searxng_url)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp.session_manager.run():
            info = await fetch_engine_info()
            if info["categories"]:
                categories_str = ", ".join(info["categories"])
                search_tool = mcp._tool_manager.get_tool("search")
                if search_tool:
                    original_desc = search_tool.description or ""
                    search_tool.description = (
                        f"{original_desc}\n\n"
                        f"Available categories: {categories_str}\n"
                        f"Use the engine_info tool to discover available engines and their categories."
                    )
            try:
                yield
            finally:
                await tools_cleanup()
                await proxy.aclose()

    mcp_app = _MCPApp(
        mcp.streamable_http_app(
            stateless_http=True,
            json_response=True,
            streamable_http_path="/",
            host="0.0.0.0",
        )
    )

    starlette_app = Starlette(
        routes=[
            Mount("/mcp", app=mcp_app),
            Route("/mcp", endpoint=mcp_app, methods=["GET", "POST", "HEAD"]),
            Mount("/", app=proxy),
        ],
        lifespan=lifespan,
    )
    starlette_app.add_middleware(AuthMiddleware, api_key=api_key or None)
    return starlette_app


app = create_app()
