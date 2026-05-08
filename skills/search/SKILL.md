---
name: search
description: Search the web using SearXNG metasearch engine. Use when you need to find information online, look up documentation, research topics, or answer questions requiring current knowledge.
---

# SearXNG Web Search

Use the configured SearXNG MCP server to search the web.

## When to Use

- Answering questions that need up-to-date information
- Looking up documentation or API references
- Researching technical topics
- Finding news or current events

## How to Use

Call the `search` MCP tool with your query:

- `query` (required): Search terms
- `categories`: general, images, videos, news, it, science
- `language`: Language code (e.g., zh, en, ja)
- `time_range`: day, month, year
- `pages`: Number of pages (1-5) for more results

## Rules

1. Always include a **Sources** section at the end with clickable markdown links
2. Use `categories` to narrow results (e.g., `news` for current events, `it` for tech)
3. Use `pages=3` when you need comprehensive results
4. Use `language` when the user writes in a specific language
