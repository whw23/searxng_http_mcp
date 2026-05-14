## Commands

```bash
# Install dependencies
uv sync

# Run tests
pytest tests/ -v

# Run single test file
pytest tests/test_tools.py -v

# Run with coverage
pytest tests/ -v --cov=mcp_server --cov-report=term-missing --cov-fail-under=80

# Start stdio server (default)
python -m mcp_server.main

# Start HTTP server (Docker mode)
python -m mcp_server.main --http

# Sync version from pyproject.toml to all config files
bash scripts/sync-version.sh

# Build PyPI package
uv build
```
