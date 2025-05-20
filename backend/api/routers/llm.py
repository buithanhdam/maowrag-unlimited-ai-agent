# src/routers/llm.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from src.db import get_session
from api.services.llm import LLMService
from api.schemas.llm import (
    LLMFoundationCreate,
    LLMFoundationUpdate,
    LLMFoundationResponse,
    LLMConfigCreate,
    LLMConfigUpdate,
    LLMConfigResponse
)
from src.enums import LLMProviderType

llm_router = APIRouter(prefix="/llm", tags=["llm"])

# LLM Foundation endpoints
@llm_router.post("/foundations/create", response_model=LLMFoundationResponse)
async def create_llm_foundation(
    foundation: LLMFoundationCreate,
    db: Session = Depends(get_session)
):
    """Create a new LLM Foundation"""
    return await LLMService.create_foundation(db, foundation)

@llm_router.get("/foundations/get", response_model=List[LLMFoundationResponse])
async def get_llm_foundations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    provider: Optional[LLMProviderType] = None,
    db: Session = Depends(get_session)
):
    """Get all LLM Foundations with optional filtering by provider"""
    return await LLMService.get_all_foundations(db, skip, limit, provider)

@llm_router.get("/foundations/get/{foundation_id}", response_model=LLMFoundationResponse)
async def get_llm_foundation(
    foundation_id: int,
    db: Session = Depends(get_session)
):
    """Get a specific LLM Foundation by ID"""
    return await LLMService.get_foundation(db, foundation_id)

@llm_router.put("/foundations/update/{foundation_id}", response_model=LLMFoundationResponse)
async def update_llm_foundation(
    foundation_id: int,
    foundation: LLMFoundationUpdate,
    db: Session = Depends(get_session)
):
    """Update an existing LLM Foundation"""
    return await LLMService.update_foundation(db, foundation_id, foundation)

@llm_router.delete("/foundations/delete/{foundation_id}")
async def delete_llm_foundation(
    foundation_id: int,
    db: Session = Depends(get_session)
):
    """Delete an LLM Foundation"""
    await LLMService.delete_foundation(db, foundation_id)
    return {"message": "Foundation deleted successfully"}

# LLM Config endpoints
@llm_router.post("/configs/create", response_model=LLMConfigResponse)
async def create_llm_config(
    config: LLMConfigCreate,
    db: Session = Depends(get_session)
):
    """Create a new LLM Config"""
    return await LLMService.create_config(db, config)

@llm_router.get("/configs/get/{config_id}", response_model=LLMConfigResponse)
async def get_llm_config(
    config_id: int,
    db: Session = Depends(get_session)
):
    """Get a specific LLM Config by ID"""
    return await LLMService.get_config(db, config_id)

@llm_router.get("/foundations/{foundation_id}/configs", response_model=List[LLMConfigResponse])
async def get_configs_by_foundation(
    foundation_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_session)
):
    """Get all LLM Configs for a specific foundation"""
    return await LLMService.get_configs_by_foundation(db, foundation_id, skip, limit)

@llm_router.put("/configs/update/{config_id}", response_model=LLMConfigResponse)
async def update_llm_config(
    config_id: int,
    config: LLMConfigUpdate,
    db: Session = Depends(get_session)
):
    """Update an existing LLM Config"""
    return await LLMService.update_config(db, config_id, config)

@llm_router.delete("/configs/delete/{config_id}")
async def delete_llm_config(
    config_id: int,
    db: Session = Depends(get_session)
):
    """Delete an LLM Config"""
    await LLMService.delete_config(db, config_id)
    return {"message": "Config deleted successfully"}