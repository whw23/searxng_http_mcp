---
name: search-papers
description: Search for academic papers, research articles, and scientific publications using SearXNG. Use when the user asks about research, studies, academic topics, or scientific evidence.
---

# SearXNG Academic Search

Search for academic papers and research via the SearXNG MCP server.

## How to Use

Call the `search` MCP tool with these preset parameters:

- `query` (required): Academic search terms (topic, author, paper title)
- `categories`: `science` (preset)
- `pages`: Use `3` for comprehensive literature search
- `format`: Use `full` to include publication dates and source info

## Rules

1. Always set `categories` to `science`
2. Include publication dates when available
3. Include a **Sources** section at the end with clickable markdown links
4. Note the source engines (e.g., arXiv, PubMed, Semantic Scholar) for credibility
