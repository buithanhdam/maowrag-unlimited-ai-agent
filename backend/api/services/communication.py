from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime

from src.db import (
    Communication, CommunicationAgentMember, Agent
)
from api.schemas.communication import (
    CommunicationCreate, CommunicationUpdate
)

class CommunicationService:
    @staticmethod
    async def create_communication(db: Session, comm_create: CommunicationCreate) -> Communication:
        try:
            communication = Communication(
                name=comm_create.name,
                description=comm_create.description,
                type=comm_create.type,
                configuration=comm_create.configuration or {}
            )
            db.add(communication)
            db.flush()

            # Add agent members
            for agent_id in comm_create.agent_ids:
                member = CommunicationAgentMember(
                    communication_id=communication.id,
                    agent_id=agent_id,
                )
                db.add(member)

            db.commit()
            db.refresh(communication)
            return communication
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Invalid agent IDs")

    @staticmethod
    async def get_communication(db: Session, communication_id: int) -> Optional[Communication]:
        communication = db.query(Communication).filter(
            Communication.id == communication_id,
            Communication.is_active == True
        ).first()
        if not communication:
            raise HTTPException(status_code=404, detail="Communication not found")
        return communication

    @staticmethod
    async def get_all_communications(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        agent_id: Optional[int] = None
    ) -> List[Communication]:
        query = db.query(Communication)
        if agent_id:
            query = query.join(CommunicationAgentMember)\
                        .filter(CommunicationAgentMember.agent_id == agent_id)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    async def update_communication(
        db: Session,
        communication_id: int,
        comm_update: CommunicationUpdate
    ) -> Communication:
        communication = await CommunicationService.get_communication(db, communication_id)
        update_data = comm_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(communication, field, value)
        db.commit()
        db.refresh(communication)
        return communication

    @staticmethod
    async def delete_communication(db: Session, communication_id: int) -> bool:
        communication = await CommunicationService.get_communication(db, communication_id)
        communication.is_active = False
        db.commit()
        return True

    @staticmethod
    async def get_communication_agents(db: Session, communication_id: int) -> List[Agent]:
        communication = await CommunicationService.get_communication(db, communication_id)
        return communication.agents