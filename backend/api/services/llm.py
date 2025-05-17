# src/services/llm_service.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.src.db.sql import LLMFoundation, LLMConfig
from api.schemas.llm import (
    LLMFoundationCreate, 
    LLMFoundationUpdate,
    LLMConfigCreate,
    LLMConfigUpdate
)
from fastapi import HTTPException
from typing import List, Optional

class LLMService:
    @staticmethod
    async def create_foundation(db: Session, foundation: LLMFoundationCreate) -> LLMFoundation:
        try:
            db_foundation = LLMFoundation(
                provider=foundation.provider,
                model_id=foundation.model_id,
                description=foundation.description,
                capabilities=foundation.capabilities
            )
            db.add(db_foundation)
            db.commit()
            db.refresh(db_foundation)
            return db_foundation
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Model ID already exists")

    @staticmethod
    async def get_foundation(db: Session, foundation_id: int) -> Optional[LLMFoundation]:
        foundation = db.query(LLMFoundation).filter(LLMFoundation.id == foundation_id).first()
        if not foundation:
            raise HTTPException(status_code=404, detail="LLM Foundation not found")
        return foundation

    @staticmethod
    async def get_all_foundations(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        provider: Optional[str] = None
    ) -> List[LLMFoundation]:
        query = db.query(LLMFoundation)
        if provider:
            query = query.filter(LLMFoundation.provider == provider)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    async def update_foundation(
        db: Session,
        foundation_id: int,
        foundation_update: LLMFoundationUpdate
    ) -> LLMFoundation:
        db_foundation = await LLMService.get_foundation(db, foundation_id)
        
        update_data = foundation_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_foundation, field, value)
        
        try:
            db.commit()
            db.refresh(db_foundation)
            return db_foundation
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Update failed due to constraint violation")

    @staticmethod
    async def delete_foundation(db: Session, foundation_id: int) -> bool:
        db_foundation = await LLMService.get_foundation(db, foundation_id)
        db.delete(db_foundation)
        db.commit()
        return True

    # LLM Config methods
    @staticmethod
    async def create_config(db: Session, config: LLMConfigCreate) -> LLMConfig:
        # Verify foundation exists
        await LLMService.get_foundation(db, config.foundation_id)
        
        db_config = LLMConfig(**config.dict())
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        return db_config

    @staticmethod
    async def get_config(db: Session, config_id: int) -> Optional[LLMConfig]:
        config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="LLM Config not found")
        return config

    @staticmethod
    async def get_configs_by_foundation(
        db: Session,
        foundation_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[LLMConfig]:
        return db.query(LLMConfig)\
            .filter(LLMConfig.foundation_id == foundation_id)\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    async def update_config(
        db: Session,
        config_id: int,
        config_update: LLMConfigUpdate
    ) -> LLMConfig:
        db_config = await LLMService.get_config(db, config_id)
        
        update_data = config_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_config, field, value)
        
        db.commit()
        db.refresh(db_config)
        return db_config

    @staticmethod
    async def delete_config(db: Session, config_id: int) -> bool:
        db_config = await LLMService.get_config(db, config_id)
        db.delete(db_config)
        db.commit()
        return True