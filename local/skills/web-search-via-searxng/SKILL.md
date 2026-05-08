---
name: web-search-via-searxng
description: Search the web using SearXNG metasearch engine. Use when you need to find information online, look up documentation, research topics, or answer questions requiring current knowledge. Also provides autocomplete suggestions.
---

# SearXNG Web Search

Use the configured SearXNG MCP server to search the web.

## When to Use

- Answering questions that need up-to-date information
- Looking up documentation or API references
- Researching technical topics
- Finding news or current events
- Searching for images, videos, academic papers, code, packages

## Tools

### `search`

Main search tool. Parameters:

- `query` (required): Search terms
- `categories`: Filter by type — general, images, videos, news, map, music, it, science, files, social media, packages, repos, q&a, etc.
- `language`: Language code (e.g., zh, en, ja)
- `time_range`: day, month, year
- `safesearch`: 0 (off), 1 (moderate), 2 (strict)
- `pageno`: Starting page number (default 1)
- `pages`: Number of pages to fetch, 1-5 (default 1). Use for comprehensive results
- `max_results`: Maximum results to return (default 10, max 100)
- `format`: `compact` (default, title/url/content only) or `full` (includes engines, score, dates)
- `engines`: Comma-separated engine names (e.g., google,bing,duckduckgo)

### `autocomplete`

Get search query suggestions. Use before searching to discover relevant terms.

- `query` (required): Partial query to autocomplete

## Rules

1. Always include a **Sources** section at the end with clickable markdown links
2. Use `categories` to narrow results (e.g., `news` for current events, `it` for tech, `science` for papers)
3. Use `pages=3` when you need comprehensive results
4. Use `language` when the user writes in a specific language
5. Use `format=full` when you need to evaluate result quality (scores, engines)
6. Use `autocomplete` to refine ambiguous queries before searching
