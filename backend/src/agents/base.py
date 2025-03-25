from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import datetime
from enum import Enum
import json
from typing import Any, Dict, Generator, List, Optional, Union
from src.agents.utils import clean_json_response
from src.llm import BaseLLM
from llama_index.core.llms import ChatMessage
from typing import AsyncGenerator
from llama_index.core.tools import FunctionTool

# Base Types and Data Classes
class AgentType(Enum):
    DEFAULT = "DEFAULT"
    CODING = "CODING"
    PLANNING = "PLANNING"
    REFLECTION = "REFLECTION"

@dataclass
class AgentProcessingResult:
    user_input: str
    agent_id: str
    agent_name: str
    user_id: str
    session_id: str
    additional_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentResponse:
    metadata: AgentProcessingResult
    output: Union[Any, str]
    streaming: bool
    
class AgentCallbacks:
    def on_llm_new_token(self, token: str) -> None:
        pass
    
    def on_agent_start(self, agent_name: str) -> None:
        pass
    
    def on_agent_end(self, agent_name: str) -> None:
        pass

@dataclass
class AgentOptions:
    name: str
    description: str
    id: Optional[str] = None
    region: Optional[str] = None
    save_chat: bool = True
    callbacks: Optional[AgentCallbacks] = None
    
@dataclass
class Message:
    role: str
    content: List[Dict[str, str]]
    timestamp: datetime = field(default_factory=datetime.datetime.now)
    
class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, llm: BaseLLM, options: AgentOptions, system_prompt:str = "", tools: List[FunctionTool] = []):
        self.llm = llm
        self.system_prompt=system_prompt
        self.name = options.name
        self.description = options.description
        self.id = options.id
        self.region = options.region
        self.save_chat = options.save_chat
        self.callbacks = options.callbacks or AgentCallbacks()
        self.tools = tools
        self.tools_dict = {tool.metadata.name: tool for tool in tools}
        
    @staticmethod
    def generate_key_from_name(name: str) -> str:
        import re
        # Remove special characters and replace spaces with hyphens
        key = re.sub(r'[^a-zA-Z\s-]', '', name)
        key = re.sub(r'\s+', '-', key)
        return key.lower()

    def _create_system_message(self, prompt: str) -> ChatMessage:
        """Create a system message with the given prompt"""
        return ChatMessage(role="system", content=prompt)
    
    def _format_tool_signatures(self) -> str:
        """Format all tool signatures into a string format LLM can understand"""
        if not self.tools:
            return "No tools are available. Respond based on your general knowledge only."
            
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
    
    async def _execute_tool(self, tool_name: str, description: str,requires_tool: bool) -> Optional[Any]:
        """Execute a tool with better error handling"""
        if not requires_tool or not tool_name:
            return None
  
        tool = self.tools_dict.get(tool_name)
        if not tool:
            return None
            
        prompt = f"""
        Generate parameters to call this tool:
        Step: {description}
        Tool: {tool_name}
        
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
            
            result = await tool.acall(**params['arguments'])
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
        chat_history:List[ChatMessage] = [],
        *args,
        **kwargs
    ) -> str:
        pass
    
    @abstractmethod
    async def achat(
        self,
        query: str,
        verbose: bool = False,
        chat_history:List[ChatMessage] = [],
        *args,
        **kwargs
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
        **kwargs
    ) -> Generator[str, None, None]:
        pass
    
    @abstractmethod
    async def astream_chat(
        self, 
        query: str, 
        verbose: bool = False,
        chat_history: Optional[List[ChatMessage]] = None,
        *args,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        pass
    
    def is_streaming_enabled(self) -> bool:
        return True
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass