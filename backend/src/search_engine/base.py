from src.logger import get_formatted_logger
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Optional
from datetime import datetime

class BaseSearchEngine(ABC):
    """
    Abstract base class for search engine implementations.
    Defines the interface for all search engine classes.
    """
    def __init__(self):
        self.logger = get_formatted_logger(__file__)
        # self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing {self.__class__.__name__}")
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> Dict:
        """Search the web for given query"""
        pass
    
    @abstractmethod
    def search_context(self, query: str, **kwargs) -> Dict:
        """Search the web and return context information"""
        pass
    
    @abstractmethod
    def qna_search(self, query: str, **kwargs) -> Dict:
        """Question-answering search based on query"""
        pass
    
    @abstractmethod
    def extract(self, url: str, **kwargs) -> Dict:
        """Extract information from a specific URL"""
        pass
    
    def log_request(self, operation: str, params: Dict) -> None:
        """Log the request with operation and parameters"""
        self.logger.info(f"Request: {operation} - Parameters: {params}")
    
    def log_response(self, operation: str, status: str, response: Optional[Dict] = None) -> None:
        """Log the response with operation, status and optional response data"""
        if response:
            self.logger.info(f"Response: {operation} - Status: {status} - Data size: {len(str(response))} bytes")
        else:
            self.logger.info(f"Response: {operation} - Status: {status}")
    
    def handle_error(self, operation: str, error: Exception) -> Dict:
        """Handle errors that occur during operations"""
        error_msg = str(error)
        trace = traceback.format_exc()
        self.logger.error(f"Error in {operation}: {error_msg}\n{trace}")
        return {
            "status": "error",
            "operation": operation,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }