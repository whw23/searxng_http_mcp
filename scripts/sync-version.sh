#!/bin/sh
set -e

VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)".*/\1/')
echo "Syncing version: $VERSION"

sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/g" \
  server.json \
  .claude-plugin/marketplace.json \
  plugins/local/.claude-plugin/plugin.json \
  plugins/remote/.claude-plugin/plugin.json \
  plugins/standalone/.claude-plugin/plugin.json

sed -i "/^name = \"searxng-http-mcp\"/{n;s/version = \"[^\"]*\"/version = \"$VERSION\"/;}" uv.lock

echo "Done. All version fields set to $VERSION"
