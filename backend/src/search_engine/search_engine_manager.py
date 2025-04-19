# search_engine_manager.py
from typing import Optional, Type
from enum import Enum
from src.logger import get_formatted_logger
from .base import BaseSearchEngine
from .tavily_search_engine import TavilyEngine
from .arxiv_search_engine import ArXivSearchEngine
from .wikipedia_search_engine import WikipediaSearchEngine
from src.enums import SearchEngineType
logger = get_formatted_logger(__file__)  
# Add other search engine types here

class SearchEngineManager:
    """
    Factory class for managing different types of Search Engine implementations
    """
    _search_engine_implementations = {
        SearchEngineType.TAVILY: TavilyEngine,
        SearchEngineType.ARXIV: ArXivSearchEngine,
        SearchEngineType.WIKI: WikipediaSearchEngine,
    }

    @classmethod
    def get_search_engine_implementation(
        cls,
        search_engine_type: SearchEngineType
    ) -> Optional[Type[BaseSearchEngine]]:
        """
        Get the Search engine implementation class for a given search engine type
        
        Args:
            search_engine_type: The type of Search engine implementation to get
            
        Returns:
            The Search Engine implementation class or None if not found
        """
        implementation = cls._search_engine_implementations.get(search_engine_type)
        if implementation is None:
            logger.warning(f"Search engine type {search_engine_type} not implemented yet, falling back to Tavily search engine")
            implementation = cls._search_engine_implementations[SearchEngineType.TAVILY]
        return implementation

    @classmethod
    def create_search_engine(
        cls,
        search_engine_type: SearchEngineType,
        api_key: str = None,
        **kwargs
    ) -> BaseSearchEngine:
        """
        Create a new Search Engine instance of the specified type
        
        Args:
            search_engine_type: The type of Search Engine to create
            api_key: API key for the search engine
            **kwargs: Additional arguments to pass to the Search Engine implementation
            
        Returns:
            A new Search Engine instance
            
        Raises:
            ValueError: If the Search Engine type is not recognized
        """
        implementation = cls.get_search_engine_implementation(search_engine_type)
        if implementation is None:
            raise ValueError(f"Unsupported Search Engine type: {search_engine_type}")
            
        try:
            search_engine_instance = implementation(
                api_key=api_key,
                **kwargs
            )
            logger.info(f"Successfully created {search_engine_type.value} instance")
            return search_engine_instance
            
        except Exception as e:
            logger.error(f"Error creating Search Engine instance: {str(e)}")
            raise

    @classmethod
    def register_implementation(
        cls,
        search_engine_type: SearchEngineType,
        implementation: Type[BaseSearchEngine]
    ):
        """
        Register a new Search Engine implementation
        
        Args:
            search_engine_type: The type of Search Engine to register
            implementation: The implementation class
        """
        if not issubclass(implementation, BaseSearchEngine):
            raise ValueError("Implementation must inherit from BaseSearchEngine")
            
        cls._search_engine_implementations[search_engine_type] = implementation
        logger.info(f"Registered new implementation for {search_engine_type.value}")