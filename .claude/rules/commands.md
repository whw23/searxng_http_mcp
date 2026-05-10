## Commands

```bash
# Install dependencies
pip install "mcp[cli]" pytest pytest-anyio httpx pytest-cov pyyaml

# Run tests
pytest tests/ -v

# Run single test file
pytest tests/test_tools.py -v

# Run with coverage
pytest tests/ -v --cov=mcp_server --cov-report=term-missing --cov-fail-under=80

# Start HTTP server (requires SearXNG on port 8080)
python -m mcp_server.main

# Start stdio server
python -m mcp_server.main --stdio
```
