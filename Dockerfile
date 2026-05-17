FROM ghcr.io/searxng/searxng:latest@sha256:654eff5a61e7a768b233b89da64ba71904d06c67c2f43fb31ab5ce20b6f1e44c

ENV PATH="/usr/local/searxng/.venv/bin:${PATH}"

# Install pip via ensurepip, upgrade to fix CVEs, then install MCP Server dependencies
COPY requirements.docker.txt /tmp/requirements.docker.txt
RUN python -m ensurepip --upgrade && \
    python -m pip install --no-cache-dir "pip==26.1.1" --require-hashes --no-deps \
        --hash=sha256:99cb1c2899893b075ff56e4ed0af55669a955b49ad7fb8d8603ecdaf4ed653fb && \
    python -m pip install --no-cache-dir --no-compile --require-hashes -r /tmp/requirements.docker.txt && \
    rm /tmp/requirements.docker.txt && \
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
