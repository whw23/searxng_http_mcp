FROM ghcr.io/searxng/searxng:latest@sha256:735156112935ab87447d981fba81367fe3fd8861a740dd93e7f26ddfe4f2848a

ENV PATH="/usr/local/searxng/.venv/bin:${PATH}"

# Install pip via ensurepip, upgrade to fix CVEs, then install MCP Server dependencies.
# `--hash` is a per-requirement option only; passing it on the CLI fails silently
# with `; true`, so pin pip via a hashed requirements file instead.
COPY requirements.pip.txt /tmp/requirements.pip.txt
COPY requirements.docker.txt /tmp/requirements.docker.txt
RUN python -m ensurepip --upgrade && \
    python -m pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.pip.txt && \
    python -m pip install --no-cache-dir --no-compile --require-hashes -r /tmp/requirements.docker.txt && \
    rm /tmp/requirements.pip.txt /tmp/requirements.docker.txt && \
    { find /usr/local/searxng/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true; }

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
