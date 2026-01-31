from tavily import TavilyClient
from config import settings
from base_tool import BaseTool
from loguru import logger

class SearchTool(BaseTool):
    name: str = "search_tool"
    description: str = "Search the web for simple queries, checking facts, or news. DO NOT use this for navigating complex websites (YouTube, LinkedIn, etc) or extracting deep content - use 'browser_use' instead."
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."}
        },
        "required": ["query"]
    }

    async def execute(self, query: str) -> str:
        if not settings.TAVILY_API_KEY:
            return "Error: TAVILY_API_KEY not found."
        
        try:
            # Tavily client is synchronous, but we wrap it for the agent
            client = TavilyClient(api_key=settings.TAVILY_API_KEY)
            response = client.search(query=query, search_depth="advanced")
            
            results = []
            for result in response.get('results', []):
                results.append(f"Title: {result.get('title')}\nURL: {result.get('url')}\nContent: {result.get('content')}\n")
            
            return "\n---\n".join(results) if results else "No results found."
        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"Error during search: {str(e)}"
