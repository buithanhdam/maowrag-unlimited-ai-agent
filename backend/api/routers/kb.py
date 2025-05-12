import json
from typing import List, Dict
from fastapi import APIRouter,status, Form, UploadFile, File, HTTPException, Depends
from jsonschema import ValidationError
from sqlalchemy.orm import Session
from src.config import global_config
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
    return KnowledgeBaseService()

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
    try:
        extension_allowed = global_config.READER_CONFIG.supported_formats

        if not extension_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No supported file formats configured",
            )

        # Check if filename exists
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename"
            )

        # Convert filename to lowercase for case-insensitive comparison
        filename_lower = file.filename.lower()

        # Check if file extension is supported
        if not any(filename_lower.endswith(ext.lower()) for ext in extension_allowed):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only {', '.join(extension_allowed)} files allowed",
            )
        # Check if file size is within the allowed limit
        if file.size > global_config.READER_CONFIG.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds the allowed limit of {global_config.READER_CONFIG.max_file_size/1024/1024}MB",
            )
        # Parse and validate the JSON string
        try:
            doc_data_dict = json.loads(doc_data)
            doc_data_obj = DocumentCreate(**doc_data_dict)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON format in doc_data")
        except ValidationError as e:
            raise HTTPException(400, f"Invalid document data: {str(e)}")
        
        return await kb_service.create_and_upload_document(
            session=db,
            kb_id=kb_id,
            doc_data=doc_data_obj,
            file=file
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