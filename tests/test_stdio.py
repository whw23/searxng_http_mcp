"""Integration tests for MCP stdio transport mode."""

import json
import os
import sys
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
MOCK_SERVER = str(Path(__file__).parent / "stdio_server_mock.py")


@pytest.fixture
async def session():
    """Start the mock MCP server in stdio mode and return a connected session."""
    env = {"PYTHONPATH": PROJECT_ROOT, "PATH": os.environ.get("PATH", "")}
    async with stdio_client(
        StdioServerParameters(command=sys.executable, args=[MOCK_SERVER], env=env)
    ) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as s:
            await s.initialize()
            yield s


@pytest.mark.anyio
async def test_list_tools(session):
    result = await session.list_tools()
    tool_names = {t.name for t in result.tools}
    assert tool_names == {"search", "autocomplete", "engine_info"}


@pytest.mark.anyio
async def test_search(session):
    result = await session.call_tool("search", {"query": "test"})
    assert not result.isError
    data = json.loads(result.content[0].text)
    assert "results" in data
    assert len(data["results"]) > 0
    assert data["results"][0]["title"] == "Test Result"


@pytest.mark.anyio
async def test_search_full_format(session):
    result = await session.call_tool(
        "search", {"query": "test", "format": "full", "max_results": 1}
    )
    assert not result.isError
    data = json.loads(result.content[0].text)
    assert data["results"][0].get("engines") is not None


@pytest.mark.anyio
async def test_autocomplete(session):
    result = await session.call_tool("autocomplete", {"query": "test"})
    assert not result.isError
    data = json.loads(result.content[0].text)
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.anyio
async def test_engine_info(session):
    result = await session.call_tool("engine_info", {})
    assert not result.isError
    data = json.loads(result.content[0].text)
    assert "categories" in data
    assert "engines" in data
    assert "category_engines" in data
    assert "general" in data["categories"]
