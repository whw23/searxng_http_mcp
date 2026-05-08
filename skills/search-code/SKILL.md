---
name: search-code
description: Search for code, technical documentation, packages, and programming Q&A using SearXNG. Use when the user asks about libraries, APIs, error messages, code examples, or software packages.
---

# SearXNG Code Search

Search for code and technical content via the SearXNG MCP server.

## How to Use

Call the `search` MCP tool with these preset parameters:

- `query` (required): Technical search terms (library names, error messages, API references)
- `categories`: `it` (preset)
- `engines`: Optionally narrow to `github,stackoverflow,pypi,npm` for targeted results
- `format`: Use `full` to include engine info and scores
- `language`: `en` recommended for code content

## Rules

1. Always set `categories` to `it`
2. Include code snippets from results when relevant
3. Include a **Sources** section at the end with clickable markdown links
4. Prefer official documentation and high-score results
