# api/schemas/chat.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.src.db.sql import MessageType

class ConversationBase(BaseModel):
    """Base model for Conversation"""
    title: Optional[str] = None

class ConversationCreate(ConversationBase):
    """Create model for Conversation"""
    agent_id: int

class CommunicationConversationCreate(ConversationBase):
    """Create model for Communication Conversation"""
    communication_id: int

class ConversationUpdate(BaseModel):
    """Update model for Conversation"""
    title: Optional[str] = None
    is_active: Optional[bool] = None

class MessageBase(BaseModel):
    """Base model for Message"""
    conversation_id: int
    role: str
    content: str

class MessageCreate(MessageBase):
    """Create model for Message"""
    type: MessageType

class MessageUpdate(BaseModel):
    """Update model for Message"""
    content: Optional[str] = None
    type: Optional[MessageType] = None

class MessageResponse(MessageBase):
    """Response model for Message"""
    id: int
    created_at: datetime
    type: MessageType

class ConversationResponse(ConversationBase):
    """Response model for Conversation"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
    messages: List[MessageResponse]

# This enables the forward reference to MessageResponse inside ConversationResponse
ConversationResponse.update_forward_refs()