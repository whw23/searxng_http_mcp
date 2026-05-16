#!/bin/sh
set -e

VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)".*/\1/')
echo "Syncing version: $VERSION"

# macOS sed requires -i '' while GNU sed requires -i alone
if sed --version >/dev/null 2>&1; then
  SED_INPLACE="sed -i"
else
  SED_INPLACE="sed -i ''"
fi

eval $SED_INPLACE "\"s/\\\"version\\\": \\\"[^\\\"]*\\\"/\\\"version\\\": \\\"$VERSION\\\"/g\"" \
  server.json \
  .claude-plugin/marketplace.json \
  plugins/local/.claude-plugin/plugin.json \
  plugins/remote/.claude-plugin/plugin.json \
  plugins/standalone/.claude-plugin/plugin.json \
  plugins/local/.plugin/plugin.json \
  plugins/remote/.plugin/plugin.json \
  plugins/standalone/.plugin/plugin.json \
  plugins/local/.codex-plugin/plugin.json \
  plugins/remote/.codex-plugin/plugin.json \
  plugins/standalone/.codex-plugin/plugin.json

eval $SED_INPLACE "\"/^name = \\\"searxng-http-mcp\\\"/{n;s/version = \\\"[^\\\"]*\\\"/version = \\\"$VERSION\\\"/;}\"" uv.lock

echo "Done. All version fields set to $VERSION"
