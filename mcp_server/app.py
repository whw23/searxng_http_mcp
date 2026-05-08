import contextlib
import os

from starlette.applications import Starlette
from starlette.routing import Mount

from mcp_server.auth import AuthMiddleware
from mcp_server.proxy import ReverseProxyApp
from mcp_server.tools import mcp, fetch_engine_info, cleanup as tools_cleanup


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
                    )
                    if info["engines"]:
                        engines_str = ", ".join(info["engines"][:50])
                        search_tool.description += (
                            f"Available engines (top 50): {engines_str}"
                        )
            try:
                yield
            finally:
                await tools_cleanup()
                await proxy.aclose()

    starlette_app = Starlette(
        routes=[
            Mount("/mcp", app=mcp.streamable_http_app()),
            Mount("/", app=proxy),
        ],
        lifespan=lifespan,
    )
    starlette_app.add_middleware(AuthMiddleware, api_key=api_key or None)
    return starlette_app


app = create_app()
