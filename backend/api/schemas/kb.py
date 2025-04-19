from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from src.db.models import DocumentStatusType, RAGType

class RagConfigResponse(BaseModel):
    id: int
    rag_type: RAGType
    embedding_model: str
    similarity_type: str
    chunk_size: int
    chunk_overlap: int
    created_at: datetime
    updated_at: Optional[datetime]   
    
class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    extra_info: Optional[Dict[str, Any]] = None
    rag_type: RAGType
    embedding_model: str
    similarity_type: str
    chunk_size: int = Field(ge=1)
    chunk_overlap: int = Field(ge=0)

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    extra_info: Optional[Dict[str, Any]] = None
    rag_config: Optional[RagConfigResponse]
    
class KnowledgeBaseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
    extra_info: Optional[Dict[str, Any]]
    rag_config: Optional[RagConfigResponse]

class DocumentCreate(BaseModel):
    knowledge_base_id: int
    name: str
    source: Optional[str] = None
    extension: str
    extra_info: Optional[Dict[str, Any]] = None

class DocumentResponse(BaseModel):
    id: int
    knowledge_base_id: int
    name: str
    source: Optional[str]
    extension: str
    status: DocumentStatusType
    extra_info: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]

class QueryRequest(BaseModel):
    query: str
    collection_name: str
    limit: Optional[int] = 5