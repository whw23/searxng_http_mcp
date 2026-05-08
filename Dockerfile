FROM ghcr.io/searxng/searxng:latest

# Install MCP Server dependencies
RUN pip install --no-cache-dir "mcp[cli]"

# Copy SearXNG config
COPY config/settings.yml /etc/searxng/settings.yml

# Copy MCP Server code
COPY mcp_server/ /usr/local/searxng/mcp_server/

# Copy custom entrypoint
COPY entrypoint.sh /usr/local/searxng/custom-entrypoint.sh
RUN chmod +x /usr/local/searxng/custom-entrypoint.sh

EXPOSE 8888

ENTRYPOINT ["/usr/local/searxng/custom-entrypoint.sh"]
