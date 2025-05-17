# api/schemas/communication.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.enums import MultiAgentType
from .agent import AgentResponse

class CommunicationBase(BaseModel):
    """Base model for Communication"""
    name: str
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    type: Optional[MultiAgentType] =MultiAgentType.ROUTER

class CommunicationCreate(CommunicationBase):
    """Create model for Communication"""
    agent_ids: List[int]  # List of agent IDs to include in communication

class CommunicationUpdate(BaseModel):
    """Update model for Communication"""
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[MultiAgentType] =MultiAgentType.ROUTER
    configuration: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class CommunicationResponse(CommunicationBase):
    """Response model for Communication"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
    agents: List[AgentResponse]  # Reuse existing AgentResponse

class CommunicationMemberBase(BaseModel):
    """Base model for Communication Member"""
    communication_id: int
    agent_id: int

class CommunicationMemberCreate(CommunicationMemberBase):
    """Create model for Communication Member"""
    pass

class CommunicationMemberUpdate(BaseModel):
    """Update model for Communication Member"""
    pass

class CommunicationMemberResponse(CommunicationMemberBase):
    """Response model for Communication Member"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

class CommunicationMessageCreate(BaseModel):
    """Create model for Communication Message"""
    conversation_id: int
    content: str
    communication_id: int  # Added to identify the communication context