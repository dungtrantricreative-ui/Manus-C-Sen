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

    async def execute(self, query: str) -> str:
        # Try Tavily first
        if settings.TAVILY_API_KEY:
            try:
                client = TavilyClient(api_key=settings.TAVILY_API_KEY)
                # Tavily search is synchronous, we run in thread if needed, 
                # but simple call for now as this is CLI environment
                response = client.search(query=query, search_depth="advanced")
                results = []
                for result in response.get('results', []):
                    results.append(f"Title: {result.get('title')}\nURL: {result.get('url')}\nContent: {result.get('content')}\n")
                if results:
                    return "\n---\n".join(results)
            except Exception as e:
                logger.warning(f"Tavily search failed: {e}. Falling back to Google.")

        # Fallback to Google Search (Free)
        try:
            from googlesearch import search
            results = []
            # googlesearch-python returns an iterator of strings
            for url in search(query, num_results=5):
                results.append(f"URL: {url}")
            
            if results:
                return "Tavily search unavailable. Google Search Results:\n" + "\n".join(results)
            return "No results found on Google or Tavily."
        except Exception as e:
            logger.error(f"Google search fallback error: {e}")
            return f"Error: All search providers failed. {str(e)}"
