from tavily import TavilyClient
from config import settings
from base_tool import BaseTool
from loguru import logger
import asyncio
from duckduckgo_search import DDGS

class SearchTool(BaseTool):
    name: str = "search_tool"
    description: str = "Perform a web search. The primary interface for external knowledge."
    instructions: str = """
1. **QUERY STRATEGY**: If a query fails, simplify it. Don't use natural language questions; use keywords.
2. **FALLBACK**: This tool automatically tries multiple providers (Tavily -> DuckDuckGo -> Google).
3. **NEXT STEP**: After searching, use `scraper` on the most promising URLs found.
4. **LIMITS**: Returns max 5-10 results. Read snippets carefully before scraping.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The keyword-based search query."}
        },
        "required": ["query"]
    }

    async def execute(self, query: str = "", **kwargs) -> str:
        # Resilient argument handling
        query = query or kwargs.get("text") or kwargs.get("input") or ""
        if not query:
            return "Error: No search query provided."
        
        results = []
        errors = []

        # 1. Try DuckDuckGo (Fast & Free) - Priority moved up for speed? No, user wants performance. 
        # Actually Tavily key exists, use it first for better RAG.
        
        # 1. Tavily (Best for LLMs)
        if settings.TAVILY_API_KEY:
            try:
                client = TavilyClient(api_key=settings.TAVILY_API_KEY)
                response = client.search(query=query, search_depth="advanced")
                tavily_res = []
                for result in response.get('results', []):
                    tavily_res.append(f"Title: {result.get('title')}\nLink: {result.get('url')}\nInfo: {result.get('content')}\n")
                if tavily_res:
                    return f"--- Tavily Search Results ({query}) ---\n" + "\n".join(tavily_res)
            except Exception as e:
                errors.append(f"Tavily: {e}")

        # 2. DuckDuckGo (Backup)
        try:
            # Using synchronous context manager in executor to avoid event loop blocking if needed, 
            # but DDGS recent versions are decent.
            with DDGS() as ddgs:
                ddg_gen = ddgs.text(query, max_results=6)
                ddg_res = []
                for r in ddg_gen:
                    ddg_res.append(f"Title: {r.get('title')}\nLink: {r.get('href')}\nInfo: {r.get('body')}\n")
                if ddg_res:
                    return f"--- DuckDuckGo Results ({query}) ---\n" + "\n".join(ddg_res)
        except Exception as e:
             errors.append(f"DDG: {e}")

        # 3. Google (Last Resort via scraped frontend or library)
        try:
            from googlesearch import search
            google_res = []
            # googlesearch-python returns only URLs
            for url in search(query, num_results=5, advanced=True):
                 google_res.append(f"Title: {url.title}\nLink: {url.url}\nInfo: {url.description}")
            
            if google_res:
                 return f"--- Google Results ({query}) ---\n" + "\n".join(google_res)
        except Exception as e:
            errors.append(f"Google: {e}")

        return f"Search failed for '{query}'. Errors: {'; '.join(errors)}"
