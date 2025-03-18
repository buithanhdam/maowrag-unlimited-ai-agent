from typing import Dict, List
from datetime import datetime
from tavily import TavilyClient
from .base import BaseSearchEngine
import os
from dotenv import load_dotenv
load_dotenv()

class TavilyEngine(BaseSearchEngine):
    """
    Implementation of BaseSearchEngine for Tavily Search API.
    """
    def __init__(self, api_key: str = None):
        super().__init__()
        try:
            if not api_key:
                self.logger.warning("API key not provided, initializing Tavily client with base api key from .env")
                api_key = os.getenv("TAVILY_API_KEY")
            self.client = TavilyClient(api_key=api_key)
            self.logger.info("Tavily client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Tavily client: {str(e)}")
            raise
    
    def search(self, query: str, max_results: int = 5, search_depth: str = "basic", 
               include_domains: List[str] = None, exclude_domains: List[str] = None) -> Dict:
        """
        Perform a web search using Tavily API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            search_depth: "basic" or "advanced" search depth
            include_domains: List of domains to include in search
            exclude_domains: List of domains to exclude from search
            
        Returns:
            Dict containing search results or error information
        """
        operation = "search"
        params = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains
        }
        
        self.log_request(operation, params)
        
        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_domains=include_domains,
                exclude_domains=exclude_domains
            )
            self.log_response(operation, "success", response)
            return {
                "status": "success",
                "operation": operation,
                "data": response,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return self.handle_error(operation, e)
    
    def search_context(self, query: str, max_tokens: int = 4000, search_depth: str = "basic",
                      include_domains: List[str] = None, exclude_domains: List[str] = None) -> Dict:
        """
        Search for context information related to a query.
        
        Args:
            query: Search query string
            max_tokens: Maximum number of tokens in the response
            search_depth: "basic" or "advanced" search depth
            include_domains: List of domains to include in search
            exclude_domains: List of domains to exclude from search
            
        Returns:
            Dict containing context search results or error information
        """
        operation = "search_context"
        params = {
            "query": query,
            "max_tokens": max_tokens,
            "search_depth": search_depth,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains
        }
        
        self.log_request(operation, params)
        
        try:
            response = self.client.get_search_context(
                query=query,
                max_tokens=max_tokens,
                search_depth=search_depth,
                include_domains=include_domains,
                exclude_domains=exclude_domains
            )
            self.log_response(operation, "success", response)
            return {
                "status": "success",
                "operation": operation,
                "data": response,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return self.handle_error(operation, e)
    
    def qna_search(self, query: str, search_depth: str = "advanced", 
                   include_domains: List[str] = None, exclude_domains: List[str] = None) -> Dict:
        """
        Perform a question-answering search using Tavily API.
        
        Args:
            query: Question to be answered
            search_depth: "basic" or "advanced" search depth
            include_domains: List of domains to include in search
            exclude_domains: List of domains to exclude from search
            
        Returns:
            Dict containing QnA search results or error information
        """
        operation = "qna_search"
        params = {
            "query": query,
            "search_depth": search_depth,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains
        }
        
        self.log_request(operation, params)
        
        try:
            response = self.client.qna_search(
                query=query,
                search_depth=search_depth,
                include_domains=include_domains,
                exclude_domains=exclude_domains
            )
            self.log_response(operation, "success", response)
            return {
                "status": "success",
                "operation": operation,
                "data": response,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return self.handle_error(operation, e)
    
    def extract(self, urls: List[str], include_images: bool = False) -> Dict:
        """
        Extract content from a URL using Tavily API.
        
        Args:
            url: The URL to extract content from
            max_tokens: Maximum number of tokens to include in response
            summarize: Whether to summarize the content
            include_images: Whether to include image descriptions
            
        Returns:
            Dict containing extracted content or error information
        """
        operation = "extract"
        params = {
            "urls": urls,
            "include_images": include_images
        }
        
        self.log_request(operation, params)
        
        try:
            response = self.client.extract(
                urls=urls,
                include_images=include_images
            )
            self.log_response(operation, "success", response)
            return {
                "status": "success",
                "operation": operation,
                "data": response,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return self.handle_error(operation, e)


# Ví dụ sử dụng
# if __name__ == "__main__":
#     try:
#         # Thay thế API key thực tế
#         tavily_client = TavilyEngine()
        
#         # Ví dụ search
#         search_results = tavily_client.search("who is leonel messi?", max_results=5)
#         print(search_results["data"]["results"])
        
#         # # Ví dụ qna_search
#         qna_results = tavily_client.qna_search("who is leonel messi?")
#         print(qna_results)
        
#         # # Ví dụ extract
#         extract_results = tavily_client.extract("https://vi.wikipedia.org/wiki/Lionel_Messi")
#         print(extract_results["data"]["results"])
        
#     except Exception as e:
#         print(f"Error in example: {str(e)}")