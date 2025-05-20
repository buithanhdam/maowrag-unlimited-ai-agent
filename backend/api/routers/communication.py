from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from src.db import get_session
from api.services.communication import CommunicationService
from api.schemas.communication import (
    CommunicationCreate, CommunicationUpdate,
    CommunicationResponse
)
from api.schemas.chat import ConversationResponse, MessageResponse
from api.schemas.agent import AgentResponse

communication_router = APIRouter(prefix="/communication", tags=["communication"])

@communication_router.post("/create", response_model=CommunicationResponse)
async def create_communication(
    comm_create: CommunicationCreate,
    db: Session = Depends(get_session)
):
    return await CommunicationService.create_communication(db, comm_create)

@communication_router.get("/{communication_id}", response_model=CommunicationResponse)
async def get_communication(communication_id: int, db: Session = Depends(get_session)):
    return await CommunicationService.get_communication(db, communication_id)

@communication_router.get("/", response_model=List[CommunicationResponse])
async def get_all_communications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_session)
):
    return await CommunicationService.get_all_communications(db, skip, limit)

@communication_router.put("/{communication_id}", response_model=CommunicationResponse)
async def update_communication(
    communication_id: int,
    comm_update: CommunicationUpdate,
    db: Session = Depends(get_session)
):
    return await CommunicationService.update_communication(db, communication_id, comm_update)

@communication_router.delete("/{communication_id}", response_model=bool)
async def delete_communication(communication_id: int, db: Session = Depends(get_session)):
    return await CommunicationService.delete_communication(db, communication_id)

@communication_router.get("/{communication_id}/agents", response_model=List[AgentResponse])
async def get_communication_agents(communication_id: int, db: Session = Depends(get_session)):
    return await CommunicationService.get_communication_agents(db, communication_id)