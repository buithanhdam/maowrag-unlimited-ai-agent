from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator, List, Optional
from llama_index.core.llms import ChatMessage
from src.logger import get_formatted_logger
import asyncio
from .base import BaseLLM
from pydantic_settings import BaseSettings
# from llama_index.llms.anthropic import Anthropic
from llama_index.llms.gemini import Gemini
# from llama_index.llms.openai import OpenAI
from src.config import global_config, get_llm_config
from src.enums import LLMProviderType

logger = get_formatted_logger(__file__)

class UnifiedLLM(BaseLLM):
    def __init__(
        self, 
        api_key: str = None, 
        llm_provider: LLMProviderType = LLMProviderType.GOOGLE, 
        model_id: str = None, 
        temperature: float = None, 
        max_tokens: int = None, 
        system_prompt: str = None,
    ):
        LLM_CONFIG = get_llm_config(llm_type=llm_provider)
        super().__init__(
            api_key=api_key or LLM_CONFIG.api_key,
            llm_provider=llm_provider or LLM_CONFIG.llm_provider,
            model_id=model_id or LLM_CONFIG.model_id,
            temperature=temperature or LLM_CONFIG.temperature,
            max_tokens=max_tokens or LLM_CONFIG.max_tokens,
            system_prompt=system_prompt or LLM_CONFIG.system_prompt,
        )
        self._initialize_model()

    def _initialize_model(self) -> None:
        try:
            
            if self.llm_provider == LLMProviderType.GOOGLE:
                self.model = Gemini(
                    api_key=self.api_key,
                    model=self.model_id,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            # elif self.model_name == "claude":
            #     self.model = Anthropic(
            #         api_key=self.api_key,
            #         model=self.model_id,
            #         temperature=self.temperature,
            #         max_tokens=self.max_tokens
            #     )
            # elif self.model_name == "openai":
            #     self.model = OpenAI(
            #         api_key=self.api_key,
            #         model=self.model_id,
            #         temperature=self.temperature,
            #         max_tokens=self.max_tokens
            #     )
            else:
                raise ValueError(f"Unsupported model type: {self.llm_provider}")
        except Exception as e:
            logger.error(f"Failed to initialize {self.llm_provider} model: {str(e)}")
            raise

    def _prepare_messages(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> List[ChatMessage]:
        messages = []
        if self.system_prompt:
            messages.append(ChatMessage(role="system", content=self.system_prompt))
            messages.append(ChatMessage(role="assistant", content="I understand and will follow these instructions."))
        
        if chat_history:
            messages.extend(chat_history)
        
        messages.append(ChatMessage(role="user", content=query))
        return messages

    def _extract_response(self, response) -> str:
        """Trích xuất text từ response của model."""
        try:
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'content'):
                return response.content.parts[0].text
            else:
                return response.message.content
        except Exception as e:
            logger.error(f"Error extracting response from {self.model_name}: {str(e)}")
            return response.message.content

    def chat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> str:
        try:
            messages = self._prepare_messages(query, chat_history)
            response = self.model.chat(messages)
            return self._extract_response(response)
        except Exception as e:
            logger.error(f"Error in {self.llm_provider} chat: {str(e)}")
            raise

    async def achat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> str:
        try:
            messages = self._prepare_messages(query, chat_history)
            response = await self.model.achat(messages)
            return self._extract_response(response)
        except Exception as e:
            logger.error(f"Error in {self.llm_provider} async chat: {str(e)}")
            raise

    def stream_chat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> Generator[str, None, None]:
        try:
            messages = self._prepare_messages(query, chat_history)
            response_stream = self.model.stream_chat(messages)
            for response in response_stream:
                yield self._extract_response(response)
        except Exception as e:
            logger.error(f"Error in {self.llm_provider} stream chat: {str(e)}")
            raise

    async def astream_chat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> AsyncGenerator[str, None]:
        try:
            messages = self._prepare_messages(query, chat_history)
            response = await self.model.astream_chat(messages)
            
            if asyncio.iscoroutine(response):
                response = await response
            
            if hasattr(response, '__aiter__'):
                async for chunk in response:
                    yield self._extract_response(chunk)
            else:
                yield self._extract_response(response)
                
        except Exception as e:
            logger.error(f"Error in {self.llm_provider} async stream chat: {str(e)}")
            raise

    @asynccontextmanager
    async def session(self):
        """Context manager để quản lý phiên làm việc với model"""
        try:
            yield self
        finally:
            # Cleanup code if needed
            pass