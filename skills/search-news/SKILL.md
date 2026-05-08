---
name: search-news
description: Search for recent news and current events using SearXNG. Use when the user asks about breaking news, recent developments, current events, or time-sensitive information.
---

# SearXNG News Search

Search for news and current events via the SearXNG MCP server.

## How to Use

Call the `search` MCP tool with these preset parameters:

- `query` (required): News search terms
- `categories`: `news` (preset)
- `time_range`: `day` for breaking news, `month` for recent developments
- `pages`: Use `3` for comprehensive news coverage
- `language`: Match the user's language

## Rules

1. Always set `categories` to `news`
2. Default to `time_range=day` unless the user specifies a different period
3. Include a **Sources** section at the end with clickable markdown links
4. Summarize key findings across multiple sources
