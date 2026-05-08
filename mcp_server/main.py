import sys

from mcp_server.tools import mcp


def main():
    if "--stdio" in sys.argv:
        mcp.run(transport="stdio")
    else:
        import uvicorn
        from mcp_server.app import app

        uvicorn.run(app, host="0.0.0.0", port=8888)


if __name__ == "__main__":
    main()
