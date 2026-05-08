FROM ghcr.io/searxng/searxng:latest

ENV PATH="/usr/local/searxng/.venv/bin:${PATH}"

# Install pip via ensurepip, then install MCP Server dependencies
RUN python -m ensurepip --upgrade && \
    python -m pip install --no-cache-dir "mcp[cli]"

# Copy MCP Server code
COPY mcp_server/ /usr/local/searxng/mcp_server/

# Copy custom entrypoint
COPY entrypoint.sh /usr/local/searxng/custom-entrypoint.sh
RUN chmod +x /usr/local/searxng/custom-entrypoint.sh

EXPOSE 8888

ENTRYPOINT ["/usr/local/searxng/custom-entrypoint.sh"]
