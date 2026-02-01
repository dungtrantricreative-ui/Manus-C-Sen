from tavily import TavilyClient
from config import settings
from base_tool import BaseTool
from loguru import logger
import asyncio

class SearchTool(BaseTool):
    name: str = "search_tool"
    description: str = "Search the web for simple queries, checking facts, or news. Use 'browser_use' for deep navigation."
    instructions: str = """
1. **QUICK FACTS**: Use this tool for facts, dates, news, or finding URLs.
2. **NO DOWNLOAD**: This tool cannot download files. Use Terminal for that.
3. **BRIDGE**: Use this tool to find the right URL, then switch to `browser_use` for deep reading.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."}
        },
        "required": ["query"]
    }

    async def execute(self, query: str = "", **kwargs) -> str:
        # Resilient argument handling
        query = query or kwargs.get("text") or kwargs.get("input") or ""
        if not query:
            return "Error: No search query provided."
        
        results = []
        
        # 1. Try Tavily (Advanced)
        if settings.TAVILY_API_KEY:
            try:
                client = TavilyClient(api_key=settings.TAVILY_API_KEY)
                response = client.search(query=query, search_depth="advanced")
                for result in response.get('results', []):
                    results.append(f"Title: {result.get('title')}\nSource: {result.get('url')}\nSnippets: {result.get('content')}\n")
                if results:
                    return "--- Tavily Results ---\n" + "\n".join(results)
            except Exception as e:
                logger.debug(f"Tavily failed: {e}")

        # 2. Try DuckDuckGo (Resilient)
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                ddg_results = ddgs.text(query, max_results=5)
                for r in ddg_results:
                    results.append(f"Title: {r.get('title')}\nSource: {r.get('href')}\nSnippets: {r.get('body')}\n")
                if results:
                    return "--- DuckDuckGo Results ---\n" + "\n".join(results)
        except Exception as e:
            logger.debug(f"DuckDuckGo failed: {e}")

        # 3. Fallback to Google Search (Free)
        try:
            from googlesearch import search
            google_results = []
            for url in search(query, num_results=5):
                google_results.append(f"URL: {url}")
            
            if google_results:
                return "--- Google Results ---\n" + "\n".join(google_results)
        except Exception as e:
            logger.debug(f"Google failed: {e}")

        return "Error: No results found after trying all search providers."
