import sys

from mcp_server.tools import mcp


def main():
    if "--http" in sys.argv:
        import uvicorn
        from mcp_server.app import app

        uvicorn.run(app, host="0.0.0.0", port=8888)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
