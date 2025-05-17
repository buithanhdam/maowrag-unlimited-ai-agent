from abc import ABC, abstractmethod
import json
from typing import Any, Generator, List, Optional
from pydantic import BaseModel
from llama_index.core.llms import ChatMessage
from typing import AsyncGenerator
from llama_index.core.tools import FunctionTool
from llama_index.core.program import LLMTextCompletionProgram
from llama_index.core.output_parsers import PydanticOutputParser

from src.logger import get_formatted_logger
from src.agents.design import (
    clean_json_response,
    AgentCallbacks,
    AgentOptions,
    retry_on_json_parse_error
)
from src.llm import BaseLLM


class BaseAgent(ABC):
    """Abstract base class for all agents"""

    def __init__(
        self,
        llm: BaseLLM,
        options: AgentOptions,
        system_prompt: str = "",
        tools: List[FunctionTool] = [],
    ):
        self.llm = llm
        if system_prompt:
            self.llm._set_system_prompt(system_prompt)
        self.system_prompt = self.llm._get_system_prompt()
        self.name = options.name
        self.description = options.description
        self.id = options.id or self._generate_id_from_name(self.name )
        self.region = options.region
        self.save_chat = options.save_chat
        self.callbacks = options.callbacks or AgentCallbacks()
        self.structured_output = options.structured_output
        self.tools = tools
        self.tools_dict = {tool.metadata.name: tool for tool in tools}
        self.logger = get_formatted_logger(__file__)
        # self.logger = logging.getLogger(__name__)
    @staticmethod        
    def _generate_id_from_name(name: str) -> str:
        import re

        # Remove special characters and replace spaces with hyphens
        key = re.sub(r"[^a-zA-Z\s-]", "", name)
        key = re.sub(r"\s+", "-", key)
        return key.lower()
    def _get_output_schema(self) -> str:
        """Get JSON schema of output model if available"""
        if not self.structured_output:
            self.logger.warning(f"Output schema not found")
            return "[No specific output schema]."

        try:
            schema = self.structured_output.model_json_schema()
            self.logger.info(f"Parsed output schema successfully: {schema}")
            return json.dumps(schema, indent=4)
        except Exception as e:
            self.logger.error(f"Error getting output schema: {str(e)}")
            return "[No specific output schema]."
    @retry_on_json_parse_error()
    async def _output_parser(
        self,
        output: str,
        chat_history: List[ChatMessage] = [],
    ) -> str:
        final_output = output
        try:
            if self.structured_output:
                program = LLMTextCompletionProgram.from_defaults(
                    output_parser=PydanticOutputParser(output_cls=self.structured_output),
                    llm=self.llm._get_model(),
                    prompt_template_str=output,
                    verbose=True
                )
                parsed_output = program()

                if isinstance(parsed_output, BaseModel):
                    final_output = parsed_output.model_dump_json()
                elif isinstance(parsed_output, str):
                    parsed_output = clean_json_response(parsed_output)
                    try:
                        final_output = json.dumps(json.loads(parsed_output), indent=4)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse JSON: {parsed_output} with error: {e}")
                        raise e
                else:
                    self.logger.error(f"Unexpected output type: {type(parsed_output)}")
                    final_output = str(parsed_output)
            else:
                final_output = await self.llm.achat(query=output, chat_history=chat_history)
            return final_output
        except Exception as e:
            self.logger.error(f"Error cleaning JSON response: {str(e)}")
            return final_output

   
    def _get_config(self) -> dict[str, Any]:
        """Get detailed config of the agent"""
        return {
            "name": self.name,
            "description": self.description,
            "id": self.id,
            "llm": self.llm._get_model_config(),
            "structured_output": self.structured_output,
        }
    def _log_info(self, message: str) -> None:
        self.logger.info(f"[Agent: {self.name}] - [ID: {self.id}] - {message}")
    def _log_error(self, message: str) -> None:
        self.logger.error(f"[Agent: {self.name}] - [ID: {self.id}] - {message}")
    def _log_debug(self, message: str) -> None:
        self.logger.debug(f"[Agent: {self.name}] - [ID: {self.id}] - {message}")
    def _log_warning(self, message: str) -> None:
        self.logger.warning(f"[Agent: {self.name}] - [ID: {self.id}] - {message}")
    
    def _create_system_message(self, prompt: str) -> ChatMessage:
        """Create a system message with the given prompt"""
        return ChatMessage(role="system", content=prompt)

    def _format_tool_signatures(self) -> str:
        """Format all tool signatures into a string format LLM can understand"""
        if not self.tools:
            return (
                "No tools are available. Respond based on your general knowledge only."
            )

        tool_descriptions = []
        for tool in self.tools:
            metadata = tool.metadata
            parameters = metadata.get_parameters_dict()

            tool_descriptions.append(
                f"""
                Function: {metadata.name}
                Description: {metadata.description}
                Parameters: {json.dumps(parameters, indent=2)}
                """
            )

        return "\n".join(tool_descriptions)

    async def _execute_tool(
        self, tool_name: str, description: str, requires_tool: bool
    ) -> Optional[Any]:
        """Execute a tool with better error handling"""
        if not requires_tool or not tool_name:
            return None

        tool = self.tools_dict.get(tool_name)
        if not tool:
            return None

        prompt = f"""
        Generate parameters to call this tool:
        Step Desciption: {description}
        Tool: {tool_name}
        Tool description: {tool.metadata.description}
        
        Tool specification:
        {json.dumps(tool.metadata.get_parameters_dict(), indent=2)}
        
        Response format:
        {{
            "arguments": {{
                // parameter names and values matching the specification exactly
            }}
        }}
        """

        try:
            response = await self.llm.achat(query=prompt)
            response = clean_json_response(response)
            params = json.loads(response)

            result = await tool.acall(**params["arguments"])
            return result

        except Exception as e:
            if requires_tool:
                raise
            return None

    @abstractmethod
    def chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        *args,
        **kwargs,
    ) -> str:
        pass

    @abstractmethod
    async def achat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: List[ChatMessage] = [],
        *args,
        **kwargs,
    ) -> str:
        """Main execution method that must be implemented by all agents"""
        pass

    @abstractmethod
    def stream_chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: Optional[List[ChatMessage]] = None,
        *args,
        **kwargs,
    ) -> Generator[str, None, None]:
        pass

    @abstractmethod
    async def astream_chat(
        self,
        query: str,
        verbose: bool = False,
        chat_history: Optional[List[ChatMessage]] = None,
        *args,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        pass

    def is_streaming_enabled(self) -> bool:
        return True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass