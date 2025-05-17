# api/schemas/agent.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.enums import AgentType
from api.schemas.kb import KnowledgeBaseResponse

class AgentBase(BaseModel):
    """Base model for Agent"""
    name: str
    agent_type: AgentType
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None

class AgentCreate(AgentBase):
    """Create model for Agent"""
    foundation_id: Optional[int] = None
    config_id: Optional[int] = None
    kb_ids: Optional[List[int]] = None

class AgentUpdate(BaseModel):
    """Update model for Agent"""
    name: Optional[str] = None
    foundation_id: Optional[int] = None
    agent_type: Optional[AgentType] = None
    config_id: Optional[int] = None
    kb_ids: Optional[List[int]] = None
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None
    is_active: Optional[bool] = None

class AgentResponse(AgentBase):
    """Response model for Agent"""
    id: int
    foundation_id: int
    config_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
    knowledge_bases: Optional[List[KnowledgeBaseResponse]]