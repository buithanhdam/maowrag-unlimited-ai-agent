from typing import Any, List, Optional
from llama_index.core.llms import ChatMessage
from dataclasses import dataclass, field
import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel
# Base Types and Data Classes
class AgentType(Enum):
    DEFAULT = "DEFAULT"
    CODING = "CODING"
    REACT = "REACT"
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
    structured_output: Optional[Type[BaseModel]] = None


@dataclass
class Message:
    role: str
    content: List[Dict[str, str]]
    timestamp: datetime = field(default_factory=datetime.datetime.now)
class ChatHistory:
    def __init__(self, initial_messages: List[ChatMessage], max_length: int):
        self.messages = initial_messages
        self.max_length = max_length

    def add(self, role: str, content: str):
        self.messages.append(ChatMessage(role=role, content=content))
        if len(self.messages) > self.max_length:
            self.messages = [self.messages[0]] + self.messages[-(self.max_length-1):]

    def get_messages(self) -> List[ChatMessage]:
        return self.messages
    
class PlanStep:
    def __init__(self, description: str, requires_tool: bool = False, tool_name: str = None):
        self.description = description
        self.requires_tool = requires_tool
        self.tool_name = tool_name
        self.completed = False
        self.result = None

class ExecutionPlan:
    def __init__(self):
        self.steps: List[PlanStep] = []
        self.current_step = 0
        
    def add_step(self, step: PlanStep):
        self.steps.append(step)
        
    def get_current_step(self) -> Optional[PlanStep]:
        if self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None
        
    def mark_current_complete(self, result: Any = None):
        if self.current_step < len(self.steps):
            self.steps[self.current_step].completed = True
            self.steps[self.current_step].result = result
            self.current_step += 1
            
    def is_complete(self) -> bool:
        return self.current_step >= len(self.steps)
    
    def get_progress(self) -> str:
        completed = sum(1 for step in self.steps if step.completed)
        return f"Progress: {completed}/{len(self.steps)} steps completed"
class PlanContext:
    def __init__(self):
        self.memory = {}
        self.results = []
        
    def add_result(self, step_name: str, result: Any):
        self.results.append(result)
        self.memory[step_name] = result
        
    def get_context(self) -> str:
        # Tạo ngữ cảnh cho bước tiếp theo dựa trên memory
        return "context_string"