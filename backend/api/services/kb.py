import os
from pathlib import Path
import tempfile
from typing import List, Dict
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from datetime import datetime
from api.schemas.kb import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    DocumentCreate,
    DocumentResponse,
)
from src.rag.base import BaseRAG
from src.db import (
    KnowledgeBase,
    RAGConfig,
    Document,
    DocumentChunk,
    Task,
    QdrantVectorDatabase,
    get_aws_s3_client,
)
from src.enums import DocumentStatusType, LLMProviderType, TaskStatusType, TaskType
from src.readers import parse_multiple_files, FileExtractor
from src.rag.rag_manager import RAGManager
from src.tasks.document_task import upload_document,parse_document
from src.config import global_config
from src.logger import get_formatted_logger

logger = get_formatted_logger(__file__)


class KnowledgeBaseService:
    def __init__(self):
        self.global_config = global_config
        self.file_extractor = FileExtractor()
        self.qdrant_client = QdrantVectorDatabase(url=global_config.QDRANT_URL)
        self.s3_client = get_aws_s3_client()

    async def create_and_upload_document(
        self, session: Session, kb_id: int, doc_data: DocumentCreate, file: UploadFile
    ) -> DocumentResponse:
        """Create a new document and store it in S3"""
        doc_uuid = str(uuid.uuid4())
        task_uuid = str(uuid.uuid4())
        try:
            file_content = await file.read()
            filename = file.filename.lower()

            kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                raise HTTPException(status_code=404, detail="Knowledge base not found")
            
            task = Task(
                id=task_uuid,
                status=TaskStatusType.PENDING,
                type=TaskType.UPLOAD_DOCUMENT,
                extra_info={
                    "knowledge_base_id": kb_id,
                    "document_uuid": doc_uuid,
                },
            )
            session.add(task)
            session.flush()
            session.refresh(task)
            
            document = Document(
                knowledge_base_id=kb_id,
                task_id=task_uuid,
                uuid=doc_uuid,
                name=filename,
                source=filename,
                extension=filename.split(".")[-1],
                status=DocumentStatusType.PENDING,
                extra_info=doc_data.extra_info,
            )
            session.add(document)
            session.flush()

            upload_document.apply_async(
                args=[
                    kb.uuid,
                    file_content,
                    filename,
                ],
                task_id=task_uuid,
            )
            task.status = TaskStatusType.PROCESSING
            session.add(task)
            session.commit()
            session.refresh(document)
            return document
        except Exception as e:
            session.rollback()
            if task_uuid:
                task = Task(
                    id=task_uuid,
                    status=TaskStatusType.FAILED,
                    type=TaskType.UPLOAD_DOCUMENT,
                    extra_info={
                        "knowledge_base_id": kb_id,
                        "document_uuid": doc_uuid,
                    },
                    message=f"Failed to create document: {str(e)}"
                )
                session.add(task)
                session.commit()
                
            logger.error(f"Error creating document: {str(e)}")
            raise HTTPException(500, f"Failed to create document: {str(e)}")

    async def process_document(
        self,
        kb_id: int,
        doc_id: int,
        session: Session,
    ) -> DocumentResponse:
        """Process document content and create embeddings"""
        # Get knowledge base and document
        task_uuid = str(uuid.uuid4())
        doc = None
        try:
            kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                raise HTTPException(status_code=404, detail="Knowledge base not found")
            
            doc = (
                session.query(Document)
                .filter(Document.id == doc_id, Document.knowledge_base_id == kb_id)
                .first()
            )
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            
            task = Task(
                id=task_uuid,
                status=TaskStatusType.PENDING,
                type=TaskType.PARSE_DOCUMENT,
                extra_info={
                    "knowledge_base_id": kb_id,
                    "document_uuid": doc.uuid,
                },
            )

            # Update document status
            doc.status = DocumentStatusType.PROCESSING
            doc.task_id = task_uuid  # Update document with new task ID
            
            session.add(task)
            session.add(doc)
            session.flush()
            
            parse_document.apply_async(
                args=[
                    kb.uuid,
                ],
                task_id=task_uuid,
            )
            session.commit()
            session.refresh(doc)

            return doc

        except Exception as e:
            session.rollback()
            
            if doc:
                # Update document status to failed
                doc.status = DocumentStatusType.FAILED
                session.add(doc)
                
                task = Task(
                    id=task_uuid,
                    status=TaskStatusType.FAILED,
                    type=TaskType.PARSE_DOCUMENT,  # Fixed: Changed from UPLOAD_DOCUMENT to PARSE_DOCUMENT
                    extra_info={
                        "knowledge_base_id": kb_id,
                        "document_uuid": doc.uuid,
                        "file_path": doc.source,
                        "documents": [],
                        "total_tokens": 0,
                        "document_count": 0,
                    },
                    message=f"Failed to process document: {str(e)}"
                )
                session.add(task)
                session.commit()
                
            logger.error(f"Error processing document: {str(e)}")
            raise HTTPException(500, f"Failed to process document: {str(e)}")

    async def create_knowledge_base(
        self, session: Session, kb_data: KnowledgeBaseCreate
    ) -> KnowledgeBaseResponse:
        """Create a new knowledge base with RAG configuration"""

        # First create the RAG config
        try:
            rag_config = RAGConfig(
                rag_type=kb_data.rag_type,
                embedding_model=kb_data.embedding_model,
                similarity_type=kb_data.similarity_type,
                chunk_size=kb_data.chunk_size,
                chunk_overlap=kb_data.chunk_overlap,
                configuration={},  # Add any additional config here
                is_active=True,
            )
            session.add(rag_config)
            session.flush()  # Get the rag_config.id
            kb_uuid = kb_data.name.replace(" ", "-").lower() + str(uuid.uuid4())
            # Create the knowledge base
            kb = KnowledgeBase(
                name=kb_data.name,
                description=kb_data.description,
                rag_config_id=rag_config.id,
                extra_info=kb_data.extra_info,
                uuid=kb_uuid,
                is_active=True,
            )
            session.add(kb)
            session.flush()

            try:
                self.qdrant_client.create_collection(kb_uuid, vector_size=768)
                self.s3_client.create_bucket(kb_uuid)
                session.commit()
                session.refresh(kb)
                return kb
            except Exception as e:
                session.rollback()
                raise HTTPException(
                    500, f"Failed to create collection in Qdrant: {str(e)}"
                )
        except HTTPException as e:
            session.rollback()
            raise e
        except Exception as e:
            session.rollback()
            raise e

    async def update_knowledge_base(
        self, session: Session, kb_id: int, kb_data: KnowledgeBaseUpdate
    ) -> KnowledgeBaseResponse:
        """Update an existing knowledge base"""
        kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        # Lấy RAG config nếu tồn tại
        rag_config = kb.rag_config
        if not rag_config:
            raise HTTPException(status_code=404, detail="RAG Config not found")

        # Nếu có cập nhật RAG config, chỉ update các field có giá trị
        if kb_data.rag_config:
            rag_update_data = kb_data.rag_config.dict(exclude_unset=True)
            for key, value in rag_update_data.items():
                setattr(rag_config, key, value)
            session.commit()
            session.refresh(rag_config)

        # Cập nhật các field của Knowledge Base (ngoại trừ `rag_config`)
        update_data = kb_data.dict(exclude={"rag_config"}, exclude_unset=True)
        for key, value in update_data.items():
            setattr(kb, key, value)

        kb.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(kb)
        return kb

    async def list_knowledge_bases(
        self, session: Session, skip: int = 0, limit: int = 10
    ) -> List[KnowledgeBaseResponse]:
        """List all knowledge bases"""
        return session.query(KnowledgeBase).offset(skip).limit(limit).all()

    async def get_knowledge_base(
        self, session: Session, kb_id: int
    ) -> KnowledgeBaseResponse:
        """Get a specific knowledge base"""
        kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        return kb

    async def get_documents_by_kb(
        self, session: Session, kb_id: int
    ) -> List[DocumentResponse]:
        return session.query(Document).filter(Document.knowledge_base_id == kb_id).all()

    async def _delete_document_file_from_s3(self, document: Document) -> None:
        """Helper method to delete a document file from S3"""
        try:
            if document.source:
                self.s3_client.remove_file(object_name=document.source)
                logger.info(f"Deleted document file from S3: {document.source}")
        except Exception as e:
            logger.error(f"Error deleting document file from S3: {str(e)}")
            # Continue with deletion process even if S3 deletion fails

    async def _delete_document_from_vector_store(
        self, collection_name: str, document_id: int
    ) -> None:
        """Helper method to delete document vectors from Qdrant"""
        try:
            # Delete vectors by filter
            self.qdrant_client.delete_vector(
                collection_name=collection_name, document_id=str(document_id)
            )
            logger.info(
                f"Deleted document vectors from Qdrant: collection={collection_name}, document_id={document_id}"
            )
        except Exception as e:
            logger.error(f"Error deleting document from vector store: {str(e)}")
            # Continue with deletion process even if vector deletion fails

    async def delete_document(
        self, session: Session, kb_id: int, document_id: int
    ) -> Dict[str, str]:
        """Delete a document and its chunks from DB, S3, and vector store"""
        # Find the document
        document = (
            session.query(Document)
            .filter(Document.id == document_id, Document.knowledge_base_id == kb_id)
            .first()
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get the knowledge base to access kb_uuid for collection name
        kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        try:
            # Step 1: Delete from S3
            await self._delete_document_file_from_s3(document)

            # Step 2: Delete from vector store
            await self._delete_document_from_vector_store(kb.uuid, document_id)

            # Step 3: Delete from database (this cascades to document chunks)
            session.delete(document)
            session.commit()

            return {"status": "success", "message": "Document deleted successfully"}

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting document: {str(e)}")
            raise HTTPException(500, f"Failed to delete document: {str(e)}")

    async def delete_knowledge_base(
        self, session: Session, kb_id: int
    ) -> Dict[str, str]:
        """Delete a knowledge base and all its associated resources"""
        # Find the knowledge base
        kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        try:
            # Step 1: Delete the Qdrant collection for this KB
            try:
                self.qdrant_client.delete_collection(kb.uuid)
                logger.info(f"Deleted Qdrant collection: {kb.uuid}")
            except Exception as e:
                logger.error(f"Error deleting Qdrant collection: {str(e)}")

            # Step 2: Delete the S3 bucket for this KB
            try:
                self.s3_client.remove_bucket(kb.uuid)
                logger.info(f"Deleted S3 bucket: {kb.uuid}")
            except Exception as e:
                logger.error(f"Error deleting S3 bucket: {str(e)}")

            # Step 3: Delete the KB and its RAG config from the database
            # This will cascade delete documents and chunks
            rag_config_id = kb.rag_config_id  # Store before deleting KB

            # Delete the KB first (this should cascade to documents and chunks)
            session.delete(kb)
            session.flush()

            # Delete the RAG config if it exists
            if rag_config_id:
                rag_config = (
                    session.query(RAGConfig)
                    .filter(RAGConfig.id == rag_config_id)
                    .first()
                )
                if rag_config:
                    session.delete(rag_config)

            session.commit()

            return {
                "status": "success",
                "message": f"Knowledge base '{kb.name}' deleted successfully with all its documents and resources",
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting knowledge base: {str(e)}")
            raise HTTPException(500, f"Failed to delete knowledge base: {str(e)}")
