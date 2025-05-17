# api/schemas/kb.py
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from backend.src.db.sql import DocumentStatusType, RAGType

class RagConfigBase(BaseModel):
    """Base model for RAG configuration"""
    rag_type: RAGType
    embedding_model: str
    similarity_type: str
    chunk_size: int = Field(ge=1)
    chunk_overlap: int = Field(ge=0)

class RagConfigCreate(RagConfigBase):
    """Create model for RAG configuration"""
    pass

class RagConfigUpdate(RagConfigBase):
    """Update model for RAG configuration"""
    rag_type: Optional[RAGType] = None
    embedding_model: Optional[str] = None
    similarity_type: Optional[str] = None
    chunk_size: Optional[int] = Field(default=None, ge=1)
    chunk_overlap: Optional[int] = Field(default=None, ge=0)

class RagConfigResponse(RagConfigBase):
    """Response model for RAG configuration"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

# Knowledge Base schemas
class KnowledgeBaseBase(BaseModel):
    """Base model for Knowledge Base"""
    name: str
    description: Optional[str] = None
    extra_info: Optional[Dict[str, Any]] = None

class KnowledgeBaseCreate(KnowledgeBaseBase, RagConfigBase):
    """Create model for Knowledge Base with RAG config embedded"""
    pass

class KnowledgeBaseUpdate(BaseModel):
    """Update model for Knowledge Base"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    extra_info: Optional[Dict[str, Any]] = None
    rag_config: Optional[RagConfigUpdate] = None

class KnowledgeBaseResponse(KnowledgeBaseBase):
    """Response model for Knowledge Base"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
    rag_config: Optional[RagConfigResponse]

# Document schemas
class DocumentBase(BaseModel):
    """Base model for Document"""
    knowledge_base_id: int
    name: str
    source: Optional[str] = None
    extension: str
    extra_info: Optional[Dict[str, Any]] = None

class DocumentCreate(DocumentBase):
    """Create model for Document"""
    pass

class DocumentUpdate(BaseModel):
    """Update model for Document"""
    name: Optional[str] = None
    source: Optional[str] = None
    extension: Optional[str] = None
    status: Optional[DocumentStatusType] = None
    extra_info: Optional[Dict[str, Any]] = None

class DocumentResponse(DocumentBase):
    """Response model for Document"""
    id: int
    status: DocumentStatusType
    created_at: datetime
    updated_at: Optional[datetime]

# Query schemas
class QueryRequest(BaseModel):
    """Request model for RAG Query"""
    query: str
    collection_name: str
    limit: Optional[int] = 5