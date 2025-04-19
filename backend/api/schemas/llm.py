# src/schemas/llm.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.enums import LLMProviderType


class LLMFoundationBase(BaseModel):
    provider: LLMProviderType
    model_id: str
    description: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None

class LLMFoundationCreate(LLMFoundationBase):
    pass
    
class LLMFoundationUpdate(LLMFoundationBase):
    is_active: Optional[bool] = None

class LLMFoundationResponse(LLMFoundationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

class LLMConfigBase(BaseModel):
    foundation_id: int
    name: str
    temperature: float
    max_tokens: int
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    system_prompt: str
    stop_sequences: Optional[List[str]] = None
    
class LLMConfigCreate(LLMConfigBase):
    pass

class LLMConfigUpdate(LLMConfigBase):
    pass

class LLMConfigResponse(LLMConfigBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]