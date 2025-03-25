from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator, List, Optional
from llama_index.core.llms import ChatMessage
from src.logger import get_formatted_logger
from pydantic_settings import BaseSettings
logger = get_formatted_logger(__file__)

class BaseLLM(ABC):
    def __init__(
        self, 
        api_key: str, 
        model_name: str, 
        model_id: str, 
        temperature: float, 
        max_tokens: int, 
        system_prompt: str
    ):
        """
        Khởi tạo base LLM class.

        Args:
            api_key (str): API key cho model
            model_name (str): Tên của model
            model_id (str): ID của model
            temperature (float): Nhiệt độ cho việc sinh text
            max_tokens (int): Số tokens tối đa cho mỗi response
            system_prompt (str): System prompt mặc định
        """
        self.api_key = api_key
        self.model_name = model_name
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
       

    @abstractmethod
    def _initialize_model(self) -> None:
        pass

    @abstractmethod
    def _prepare_messages(
        self, 
        query: str, 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> List[ChatMessage]:
        pass

    @abstractmethod
    def chat(
        self, 
        query: str, 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> str:
        pass

    @abstractmethod
    async def achat(
        self, 
        query: str, 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> str:
        pass

    @abstractmethod
    def stream_chat(
        self, 
        query: str, 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> Generator[str, None, None]:
        pass

    @abstractmethod
    async def astream_chat(
        self, 
        query: str, 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> AsyncGenerator[str, None]:
        pass
    
    def get_model_name(self) -> str:
        return self.model_name

    def get_model_config(self) -> dict:
        return {
            "model_name": self.model_name,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt
        }
    @asynccontextmanager
    async def session(self):
        try:
            yield self
        finally:
            # Cleanup code if needed
            pass