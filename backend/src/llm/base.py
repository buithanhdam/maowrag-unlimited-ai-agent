from contextlib import asynccontextmanager
from llama_index.core.types import PydanticProgramMode
from typing import AsyncGenerator, Generator, List, Optional
from llama_index.core.llms import ChatMessage
import logging
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_chain,
    wait_fixed,
    before_sleep_log,
)
import asyncio
from llama_index.core.llms.function_calling import FunctionCallingLLM

# from llama_index.llms.anthropic import Anthropic
from llama_index.llms.gemini import Gemini
from google.api_core.exceptions import GoogleAPICallError
from llama_index.llms.openai import OpenAI

from src.config import LLMProviderType, get_llm_config
from src.logger import get_formatted_logger

logger = get_formatted_logger(__file__)


def retry_on_quota_error():
    def is_429_error(exception: Exception) -> bool:
        if isinstance(exception, GoogleAPICallError):
            return exception.code.value == 429 or "429" in str(exception)
        return "429" in str(exception)

    wait_strategy = wait_chain(wait_fixed(3), wait_fixed(5), wait_fixed(10))
    retry_if_429_error = retry_if_exception(is_429_error)
    return retry(
        retry=retry_if_429_error,
        stop=stop_after_attempt(3),
        wait=wait_strategy,
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


class BaseLLM:
    def __init__(
        self,
        api_key: str = None,
        provider: LLMProviderType = LLMProviderType.GOOGLE,
        model_id: str = None,
        temperature: float = None,
        max_tokens: int = None,
        system_prompt: str = None,
    ):
        LLM_CONFIG = get_llm_config(provider)
        self.api_key = api_key or LLM_CONFIG.api_key
        self.provider = provider or LLM_CONFIG.provider
        self.model_id = model_id or LLM_CONFIG.model_id
        self.temperature = temperature or LLM_CONFIG.temperature
        self.max_tokens = max_tokens or LLM_CONFIG.max_tokens
        self.system_prompt = system_prompt or LLM_CONFIG.system_prompt
        self._initialize_model()

    def _set_system_prompt(self, system_prompt: str) -> None:
        self.system_prompt = (
            f"Base prompt: {self.system_prompt}\nUser prompt:{system_prompt}"
        )

    def _get_system_prompt(self) -> str:
        return self.system_prompt

    def _initialize_model(self) -> None:
        try:

            if self.provider == LLMProviderType.GOOGLE:
                self.model = Gemini(
                    api_key=self.api_key,
                    model=self.model_id,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    pydantic_program_mode=PydanticProgramMode.OPENAI,
                )
            elif self.provider == LLMProviderType.OPENAI:
                self.model = OpenAI(
                    api_key=self.api_key,
                    model=self.model_id,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    pydantic_program_mode=PydanticProgramMode.OPENAI,
                )
            else:
                raise ValueError(f"Unsupported model type: {self.provider}")
        except Exception as e:
            logger.error(f"Failed to initialize {self.provider} model: {str(e)}")
            raise

    def _get_model(self) -> FunctionCallingLLM:
        return self.model

    def _prepare_messages(
        self, query: str, chat_history: Optional[List[ChatMessage]] = None
    ) -> List[ChatMessage]:
        messages = []
        if self.system_prompt:
            messages.append(ChatMessage(role="system", content=self.system_prompt))
            messages.append(
                ChatMessage(
                    role="assistant",
                    content="I understand and will follow these instructions.",
                )
            )

        if chat_history:
            messages.extend(chat_history)

        messages.append(ChatMessage(role="user", content=query))
        return messages

    def _extract_response(self, response) -> str:
        """Trích xuất text từ response của model."""
        try:
            if hasattr(response, "text"):
                return response.text
            elif hasattr(response, "content"):
                return response.content.parts[0].text
            else:
                return response.message.content
        except Exception as e:
            logger.error(f"Error extracting response from {self.provider}: {str(e)}")
            return response.message.content

    @retry_on_quota_error()
    def chat(self, query: str, chat_history: Optional[List[ChatMessage]] = None) -> str:
        try:
            messages = self._prepare_messages(query, chat_history)
            response = self.model.chat(messages)
            return self._extract_response(response)
        except Exception as e:
            logger.error(f"Error in {self.provider} chat: {str(e)}")
            raise e

    @retry_on_quota_error()
    async def achat(
        self, query: str, chat_history: Optional[List[ChatMessage]] = None
    ) -> str:
        try:
            messages = self._prepare_messages(query, chat_history)
            response = await self.model.achat(messages)
            return self._extract_response(response)
        except Exception as e:
            logger.error(f"Error in {self.provider} async chat: {str(e)}")
            raise e

    @retry_on_quota_error()
    def stream_chat(
        self, query: str, chat_history: Optional[List[ChatMessage]] = None
    ) -> Generator[str, None, None]:
        try:
            messages = self._prepare_messages(query, chat_history)
            response_stream = self.model.stream_chat(messages)
            for response in response_stream:
                yield self._extract_response(response)
        except Exception as e:
            logger.error(f"Error in {self.provider} stream chat: {str(e)}")
            raise e

    @retry_on_quota_error()
    async def astream_chat(
        self, query: str, chat_history: Optional[List[ChatMessage]] = None
    ) -> AsyncGenerator[str, None]:
        try:
            messages = self._prepare_messages(query, chat_history)
            response = await self.model.astream_chat(messages)

            if asyncio.iscoroutine(response):
                response = await response

            if hasattr(response, "__aiter__"):
                async for chunk in response:
                    yield self._extract_response(chunk)
            else:
                yield self._extract_response(response)

        except Exception as e:
            logger.error(f"Error in {self.provider} async stream chat: {str(e)}")
            raise e

    def _get_provider(self) -> str:
        return self.provider

    def _get_model_config(self) -> dict:
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt,
        }

    @asynccontextmanager
    async def session(self):
        """Context manager để quản lý phiên làm việc với model"""
        try:
            yield self
        finally:
            # Cleanup code if needed
            pass
