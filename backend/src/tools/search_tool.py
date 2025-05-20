from src.search_engine import TavilyEngine
from src.search_engine import WikipediaSearchEngine

def search_web():
    tavily_client = TavilyEngine()
    def search_web_by_tavily(query: str) -> dict:
        """The Web Search tool uses the Tavily Search API to search the web for the query and returns results."""
        # Implementation here
        search_results=tavily_client.search(
            query=query,
            max_results=5,
        )
        return search_results["data"]["results"]
    return search_web_by_tavily

def search_wiki():
    wikipedia_client = WikipediaSearchEngine(top_k_results=2)
    def search_wiki_by_wikipedia(query: str) -> dict:
        """
        The Wikipedia Search tool provides access to a vast collection of articles covering a wide range of topics.
        Can query specific keywords or topics to retrieve accurate and comprehensive information.
        """
        # Implementation here
        search_results=wikipedia_client.search(
            query=query
        )
        return search_results["results"]
    return search_wiki_by_wikipedia
