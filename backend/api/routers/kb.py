import json
from typing import List, Dict
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, Depends
from jsonschema import ValidationError
from sqlalchemy.orm import Session

from src.config import Settings
from src.db.mysql import get_db
from api.services.kb import KnowledgeBaseService
from api.schemas.kb import (
    QueryRequest,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    DocumentCreate,
    DocumentResponse
)

kb_router = APIRouter(prefix="/kb", tags=["kb"])

# Dependency to get KB service
async def get_kb_service():
    settings = Settings()
    return KnowledgeBaseService(settings)

@kb_router.post("/", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """Create a new knowledge base with RAG configuration"""
    return await kb_service.create_knowledge_base(db, kb_data)

@kb_router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: int,
    kb_data: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """Update an existing knowledge base"""
    return await kb_service.update_knowledge_base(db, kb_id, kb_data)

@kb_router.get("/", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """List all knowledge bases"""
    return await kb_service.list_knowledge_bases(db, skip, limit)

@kb_router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: int,
    db: Session = Depends(get_db),
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """Get a specific knowledge base"""
    return await kb_service.get_knowledge_base(db, kb_id)

@kb_router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: int,
    db: Session = Depends(get_db),
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """Delete a knowledge base and all its documents"""
    return await kb_service.delete_knowledge_base(db, kb_id)

@kb_router.get("/{kb_id}/documents", response_model=List[DocumentResponse])
async def get_documents(
    kb_id: int,
    db: Session = Depends(get_db),
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """Get all documents for a specific knowledge base"""
    return await kb_service.get_documents_by_kb(db, kb_id)

@kb_router.post("/{kb_id}/documents", response_model=DocumentResponse)
async def upload_document(
    kb_id: int,
    doc_data: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """Upload a document for a specific knowledge base"""
    # Validate file type and size
    allowed_extensions = ('.pdf', '.txt', '.doc', '.docx')
    max_file_size = 50 * 1024 * 1024  # 50MB limit
    
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(400, f"Unsupported file type. Allowed types: {allowed_extensions}")
    
    # Check file size
    file_size = 0
    content = bytearray()
    
    # Read file in chunks to handle large files
    chunk_size = 1024 * 1024  # 1MB chunks
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_size += len(chunk)
        if file_size > max_file_size:
            raise HTTPException(400, f"File too large. Maximum size: {max_file_size/1024/1024}MB")
        content.extend(chunk)
        
    try:
        # Parse and validate the JSON string
        try:
            doc_data_dict = json.loads(doc_data)
            doc_data_obj = DocumentCreate(**doc_data_dict)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON format in doc_data")
        except ValidationError as e:
            raise HTTPException(400, f"Invalid document data: {str(e)}")
        
        return await kb_service.create_document(
            session=db,
            kb_id=kb_id,
            doc_data=doc_data_obj,
            file_content=bytes(content),
            filename=file.filename
        )
            
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(500, "Internal server error during document upload")

@kb_router.post("/{kb_id}/documents/{doc_id}/process", response_model=DocumentResponse)
async def process_document(
    kb_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """Process an uploaded document"""
    try:
        return await kb_service.process_document(kb_id, doc_id, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(500, "Internal server error during document processing")

@kb_router.delete("/{kb_id}/documents/{document_id}")
async def delete_document(
    kb_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """Delete a document from a knowledge base"""
    try:
        return await kb_service.delete_document(
            session=db,
            kb_id=kb_id,
            document_id=document_id
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(500, str(e))