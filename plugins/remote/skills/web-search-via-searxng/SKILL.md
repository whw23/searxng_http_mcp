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

## How to Search

**Prefer delegating to the `web-searcher` agent** via the Agent tool. The agent handles
searching, deduplication, and summarization, and returns a clean result without polluting
your context window with raw JSON. Only call the MCP search tools directly when:

- The `web-searcher` agent is unavailable (e.g., no subagent support)
- You need a single quick lookup where spawning an agent is overkill

## MCP Tools Reference

When searching directly (without the agent), use these tools:

### `search`

Main search tool. Parameters:

- `query` (required): Search terms
- `categories`: Filter by type — general, images, videos, news, map, music, it, science, files, social media, packages, repos, q&a, etc.
- `language`: Language code (e.g., zh, en, ja)
- `time_range`: day, week, month, year
- `safesearch`: 0 (off), 1 (moderate), 2 (strict)
- `pageno`: Starting page number (default 1)
- `pages`: Number of pages to fetch, 1-5 (default 1). Use for comprehensive results
- `max_results`: Maximum results to return (default 10, max 100)
- `format`: `compact` (default, title/url/content only) or `full` (includes engines, score, dates)
- `engines`: Comma-separated engine names (e.g., google,bing,duckduckgo)

### `autocomplete`

Get search query suggestions. Use before searching to discover relevant terms.

- `query` (required): Partial query to autocomplete

### `engine_info`

Discover available search engines and categories. No parameters. Returns engines grouped by category.

Use this when you need to target specific engines or categories (e.g., "search academic papers" → call engine_info to find science engines, then search with `categories=science`).

## Category Selection Guide

Use `categories` as the primary filter. Only fall back to `engines` when categories produce poor results.

| User intent | Category | When to use `engines` instead |
|---|---|---|
| Current events, breaking news | `news` | — |
| Academic papers, research | `science` or `scientific publications` | `arxiv` for preprints, `pubmed` for biomedical |
| Code, libraries, tech docs | `it` | `github` for repos, `stackoverflow` for Q&A |
| Package lookup (npm, pip) | `packages` | `pypi`, `docker hub` by name |
| Images, photos | `images` | — |
| Videos | `videos` | `youtube` for YouTube-specific |
| Maps, locations | `map` | — |
| Definitions, word meanings | `dictionaries` or `define` | — |
| Weather | `weather` | — |
| Translation | `translate` | — |
| Shopping, products | `shopping` | — |
| Torrents, file search | `files` | — |
| Social media posts | `social media` | — |
| General knowledge | `general` (default) | — |

## Rules

1. **Delegate to `web-searcher` agent by default** — it returns clean summaries and keeps raw data out of your context
2. Always include a **Sources** section at the end with clickable markdown links
3. **Prefer `categories` over `engines`** to narrow results — categories leverage multiple engines automatically
4. Only use `engines` when you need a specific source (e.g., `arxiv` for preprints, `github` for repos)
5. Use `pages=3` when you need comprehensive results
6. Use `language` when the user writes in a specific language
7. Use `format=full` when you need to evaluate result quality (scores, engines)
8. Use `autocomplete` to refine ambiguous queries before searching
9. Use `engine_info` only when the category table above doesn't cover the use case
