FROM ghcr.io/searxng/searxng:latest@sha256:3eb2fcb2153e0b1f8e9f3457695ed3db1b1443d1dbc2b6d23121835d33fd50aa

ENV PATH="/usr/local/searxng/.venv/bin:${PATH}"

# Install pip via ensurepip, then install MCP Server dependencies
RUN python -m ensurepip --upgrade && \
    python -m pip install --no-cache-dir --no-compile "mcp[cli]" && \
    find /usr/local/searxng/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true

# Copy MCP Server code
COPY mcp_server/ /usr/local/searxng/mcp_server/

# Copy custom entrypoint
COPY scripts/entrypoint.sh /usr/local/searxng/custom-entrypoint.sh
RUN chmod +x /usr/local/searxng/custom-entrypoint.sh

LABEL io.modelcontextprotocol.server.name="io.github.whw23/searxng-http-mcp"

EXPOSE 8888

COPY scripts/healthcheck.sh /usr/local/searxng/healthcheck.sh
RUN chmod +x /usr/local/searxng/healthcheck.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD /usr/local/searxng/healthcheck.sh

ENTRYPOINT ["/usr/local/searxng/custom-entrypoint.sh"]
