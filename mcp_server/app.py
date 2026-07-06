import contextlib
import os

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from mcp_server.auth import AuthMiddleware
from mcp_server.proxy import ReverseProxyApp
from mcp_server.tools import mcp, fetch_engine_info, cleanup as tools_cleanup


async def _mcp_app(scope: Scope, receive: Receive, send: Send) -> None:
    """Serve the MCP app at /mcp and /mcp/.

    When mounted at /mcp, Starlette strips the prefix and passes an empty
    path for /mcp. When routed via Route("/mcp"), the path is /mcp. The
    inner MCP app route is /, so normalize both to /.
    """
    if scope["type"] in ("http", "websocket") and scope.get("path") in ("", "/mcp"):
        scope = dict(scope)
        scope["path"] = "/"
        scope["raw_path"] = b"/"
    await mcp.streamable_http_app()(scope, receive, send)


def create_app() -> Starlette:
    """Create the Starlette ASGI app with MCP, auth, and reverse proxy."""
    api_key = os.environ.get("API_KEY", "")
    searxng_url = os.environ.get("SEARXNG_URL", "http://127.0.0.1:8080")

    proxy = ReverseProxyApp(upstream=searxng_url)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp.session_manager.run():
            info = await fetch_engine_info()
            if info["categories"]:
                categories_str = ", ".join(info["categories"])
                search_tool = mcp._tool_manager._tools.get("search")
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

    starlette_app = Starlette(
        routes=[
            Mount("/mcp", app=_mcp_app),
            Route("/mcp", endpoint=_mcp_app, methods=["GET", "POST", "HEAD"]),
            Mount("/", app=proxy),
        ],
        lifespan=lifespan,
    )
    starlette_app.add_middleware(AuthMiddleware, api_key=api_key or None)
    return starlette_app


app = create_app()
