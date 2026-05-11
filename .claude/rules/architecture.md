## Architecture

```
mcp_server/          # MCP server package
  main.py            # Entry point (HTTP or stdio mode)
  app.py             # Starlette ASGI app (MCP + auth + reverse proxy)
  tools.py           # MCP tools (search, autocomplete, engine_info)
  auth.py            # API key + Basic Auth middleware
  proxy.py           # SearXNG reverse proxy
  patch_settings.py  # SearXNG settings patcher
tests/               # pytest + pytest-anyio
plugins/             # Claude Code plugin (local + remote variants)
```

## Code Style

- Python 3.14+, type annotations with `Annotated` + `Field`
- Async throughout (`async def`, `httpx.AsyncClient`)
- No comments unless explaining non-obvious "why"

## Testing

- `pytest-anyio` for async tests (`@pytest.mark.anyio`)
- Mock `httpx.AsyncClient` for unit tests
- `stdio_client` / `streamable_http_client` for transport integration tests
- `plugins/local/` and `plugins/remote/` skills and agents must stay identical

## Gotchas

- `docs/superpowers/` is in `.gitignore` — plugin caches are local only
- `mcp_server` is not installed as a package — tests need `PYTHONPATH` set to project root
