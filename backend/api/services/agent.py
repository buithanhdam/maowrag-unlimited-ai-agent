from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.db import Agent, AgentKnowledgeBase, KnowledgeBase, LLMConfig, LLMFoundation, AgentConversation
from api.schemas.agent import AgentCreate, AgentUpdate, AgentResponse

class AgentService:
    @staticmethod
    async def create_agent(db: Session, agent_create: AgentCreate) -> Agent:
        try:
            # Create new agent instance
            agent = Agent(
                name=agent_create.name,
                agent_type=agent_create.agent_type,
                description=agent_create.description,
                configuration=agent_create.configuration or {},
                tools=agent_create.tools or []
            )
            
            # If foundation_id is provided, verify it exists
            if agent_create.foundation_id:
                foundation = db.query(LLMFoundation).filter(
                    LLMFoundation.id == agent_create.foundation_id,
                    LLMFoundation.is_active == True
                ).first()
                if not foundation:
                    raise HTTPException(status_code=404, detail="LLM Foundation not found")
                agent.foundation_id = agent_create.foundation_id
            
            # If config_id is provided, verify it exists
            if agent_create.config_id:
                config = db.query(LLMConfig).filter(
                    LLMConfig.id == agent_create.config_id
                ).first()
                if not config:
                    raise HTTPException(status_code=404, detail="LLM Config not found")
                agent.config_id = agent_create.config_id

                # Check if all knowledge base IDs exist
            if agent_create.kb_ids and len(agent_create.kb_ids) > 0:
                kb_count = db.query(KnowledgeBase).filter(
                    KnowledgeBase.id.in_(agent_create.kb_ids),
                    KnowledgeBase.is_active == True
                ).count()
                
                if kb_count != len(agent_create.kb_ids):
                    raise HTTPException(status_code=404, detail="One or more Knowledge Bases not found")
             
            db.add(agent)
            db.flush()   
            # Now add relationships to knowledge bases
            if agent_create.kb_ids and len(agent_create.kb_ids) > 0:
                for kb_id in agent_create.kb_ids:
                    agent_kb = AgentKnowledgeBase(
                        agent_id=agent.id,
                        knowledge_base_id=kb_id
                    )
                    db.add(agent_kb)
                    
            db.commit()
            db.refresh(agent)
            return agent
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail="Invalid data provided")
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_agent(db: Session, agent_id: int) -> Optional[AgentResponse]:
        agent = db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.is_active == True
        ).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    @staticmethod
    async def get_all_agents(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[Agent]:
        query = db.query(Agent)
        if not include_inactive:
            query = query.filter(Agent.is_active == True)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    async def update_agent(db: Session, agent_id: int, agent_update: AgentUpdate) -> Agent:
        try:
            agent = await AgentService.get_agent(db, agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            update_data = agent_update.dict(exclude_unset=True)

            # Kiểm tra foundation_id nếu có
            if 'foundation_id' in update_data:
                foundation = db.query(LLMFoundation).filter(
                    LLMFoundation.id == update_data['foundation_id'],
                    LLMFoundation.is_active == True
                ).first()
                if not foundation:
                    raise HTTPException(status_code=404, detail="LLM Foundation not found")

            # Kiểm tra config_id nếu có
            if 'config_id' in update_data:
                config = db.query(LLMConfig).filter(
                    LLMConfig.id == update_data['config_id']
                ).first()
                if not config:
                    raise HTTPException(status_code=404, detail="LLM Config not found")

            # Xử lý cập nhật kb_ids
            if 'kb_ids' in update_data:
                new_kb_ids = set(update_data.pop('kb_ids'))
                
                # Xóa tất cả các bản ghi cũ
                db.query(AgentKnowledgeBase).filter(AgentKnowledgeBase.agent_id == agent_id).delete()

                # Thêm các bản ghi mới
                for kb_id in new_kb_ids:
                    db.add(AgentKnowledgeBase(agent_id=agent_id, knowledge_base_id=kb_id))

            # Cập nhật các trường còn lại
            for field, value in update_data.items():
                setattr(agent, field, value)

            db.commit()
            db.refresh(agent)
            return agent

        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Invalid data provided")
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_agent(db: Session, agent_id: int) -> bool:
        try:
            agent = await AgentService.get_agent(db, agent_id)
            agent.is_active = False  # Soft delete
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def hard_delete_agent(db: Session, agent_id: int) -> bool:
        try:
            agent = await AgentService.get_agent(db, agent_id)
            # Delete related conversations
            db.query(AgentConversation).filter(
                AgentConversation.agent_id == agent_id
            ).delete()
            
            db.delete(agent)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    @staticmethod
    async def get_agent_conversations(db: Session, agent_id: int) -> List[AgentConversation]:
        agent = await AgentService.get_agent(db, agent_id)
        return agent.conversations