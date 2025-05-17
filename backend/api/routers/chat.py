from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from src.db import get_session
from api.services.chat import ChatService
from api.schemas.chat import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    MessageCreate, MessageResponse,CommunicationConversationCreate
)

chat_router = APIRouter(prefix="/chat", tags=["chat"])

@chat_router.post("/conversations/agent/create", response_model=ConversationResponse)
async def create_conversation(conv_create: ConversationCreate, db: Session = Depends(get_session)):
    return await ChatService.create_conversation(db, conv_create)

@chat_router.get("/conversations/agent/get-all", response_model=List[ConversationResponse])
async def get_all_conversations(skip: int = 0, limit: int = 100, agent_id: Optional[int] = None, db: Session = Depends(get_session)):
    return await ChatService.get_all_conversations(db, skip, limit, agent_id)

@chat_router.post("/conversations/communication/create", response_model=ConversationResponse)
async def create_communication_conversation(
    conv_create: CommunicationConversationCreate,
    db: Session = Depends(get_session)
):
    return await ChatService.create_communication_conversation(db, conv_create)

@chat_router.get("/conversations/communication/get-all", response_model=List[ConversationResponse])
async def get_all_communication_conversations(skip: int = 0, limit: int = 100, communication_id: Optional[int] = None, db: Session = Depends(get_session)):
    return await ChatService.get_all_communication_conversations(db, skip, limit, communication_id)


@chat_router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: int, db: Session = Depends(get_session)):
    return await ChatService.get_conversation(db, conversation_id)

@chat_router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(conversation_id: int, conv_update: ConversationUpdate, db: Session = Depends(get_session)):
    return await ChatService.update_conversation(db, conversation_id, conv_update)

@chat_router.delete("/conversations/{conversation_id}", response_model=bool)
async def delete_conversation(conversation_id: int, db: Session = Depends(get_session)):
    return await ChatService.delete_conversation(db, conversation_id)

@chat_router.post("/chat", response_model=MessageResponse)
async def add_message(message: MessageCreate, db: Session = Depends(get_session)):
    return await ChatService.chat(db, message)