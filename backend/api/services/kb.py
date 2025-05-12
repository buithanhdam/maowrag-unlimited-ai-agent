import json
import os
from pathlib import Path
import tempfile
from typing import List, Optional, Dict, Any
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from datetime import datetime
from api.schemas.kb import (KnowledgeBaseCreate, KnowledgeBaseResponse, KnowledgeBaseUpdate,DocumentCreate,DocumentResponse)
from src.rag.base import BaseRAG
from src.db.models import (KnowledgeBase,RAGConfig,Document,DocumentChunk)
from src.enums import DocumentStatusType, LLMProviderType
from src.db.qdrant import QdrantVectorDatabase
from src.db.aws import S3Client, get_aws_s3_client
from src.readers import parse_multiple_files, FileExtractor
from src.rag.rag_manager import RAGManager
from src.tasks.document_task import upload_document, TaskResponse
from src.config import global_config
from src.logger import get_formatted_logger

logger = get_formatted_logger(__file__)

class KnowledgeBaseService:
    def __init__(self):
        self.global_config = global_config
        self.file_extractor = FileExtractor()
        self.qdrant_client = QdrantVectorDatabase(url=global_config.QDRANT_URL)
        self.s3_client = get_aws_s3_client()
        
    async def create_knowledge_base(
        self, 
        session: Session, 
        kb_data: KnowledgeBaseCreate
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
                is_active=True
            )
            session.add(rag_config)
            session.flush()  # Get the rag_config.id
            kb_uuid = "kb-" + str(uuid.uuid4())
            # Create the knowledge base
            kb = KnowledgeBase(
                name=kb_data.name,
                description=kb_data.description,
                rag_config_id=rag_config.id,
                extra_info=kb_data.extra_info,
                uuid=kb_uuid,
                is_active=True
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
                raise HTTPException(500, f"Failed to create collection in Qdrant: {str(e)}")
        except HTTPException as e:
            session.rollback()
            raise e
        except Exception as e:
            session.rollback()
            raise e

    async def update_knowledge_base(
        self,
        session: Session,
        kb_id: int,
        kb_data: KnowledgeBaseUpdate
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
        self,
        session: Session,
        skip: int = 0,
        limit: int = 10
    ) -> List[KnowledgeBaseResponse]:
        """List all knowledge bases"""
        return session.query(KnowledgeBase)\
            .offset(skip)\
            .limit(limit)\
            .all()

    async def get_knowledge_base(
        self,
        session: Session,
        kb_id: int
    ) -> KnowledgeBaseResponse:
        """Get a specific knowledge base"""
        kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        return kb

    async def get_documents_by_kb( self,
        session: Session,
        kb_id: int)-> List[DocumentResponse]:
        return session.query(Document).filter(Document.knowledge_base_id == kb_id).all()

    async def get_rag_from_kb(
        self,
        session: Session,
        kb_id: int
     ) -> BaseRAG:
        kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        # Get RAG config
        rag_config :RAGConfig = kb.rag_config
        if not rag_config:
            raise HTTPException(status_code=404, detail="RAG Config not found")
        # Initialize RAG manager
        rag_manager = RAGManager.create_rag(
            rag_type=rag_config.rag_type,
            vector_db_url=self.global_config.QDRANT_URL,
            llm_type=LLMProviderType.GOOGLE,
            chunk_size=rag_config.chunk_size,
            chunk_overlap=rag_config.chunk_overlap,
        )
        return rag_manager
    # working with documents
    async def create_and_upload_document(
        self,
        session: Session,
        kb_id: int,
        doc_data: DocumentCreate,
        file:UploadFile
    ) -> DocumentResponse:
        """Create a new document and store it in S3"""
        try:
            file_content = await file.read()
            filename = file.filename.lower()
  
            kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                raise HTTPException(status_code=404, detail="Knowledge base not found")
                
            task = upload_document.delay(
                    bucket_name= kb.uuid,
                    file_content= file_content,
                    filename=filename
            )
            try:
                task_result: TaskResponse = TaskResponse(
                    **task.get(timeout=30)
                )  # Consider making this async in production
            except Exception as task_error:
                raise HTTPException(
                    status_code=500, detail=f"Task processing failed: {str(task_error)}"
                )
            if task_result.status != "success":
                raise HTTPException(500, f"Task {task_result.task_id} Failed to upload document: {task_result.message}")
            # Create document record
            document = Document(
                knowledge_base_id=kb_id,
                task_id=task_result.task_id,
                name=filename,
                source=task_result.task_info.get("file_source",filename),
                extension=filename.split(".")[-1],
                status=DocumentStatusType.UPLOADED,
                extra_info=doc_data.extra_info,
            )
            
            session.add(document)
            session.commit()
            session.refresh(document)
            
            return document
        except Exception as e:
            session.rollback()
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
        kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
            
        doc = session.query(Document).filter(
            Document.id == doc_id,
            Document.knowledge_base_id == kb_id
        ).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
            
        rag_manager = await self.get_rag_from_kb(session, kb_id)
        
        # Update document status
        doc.status = DocumentStatusType.PENDING
        session.commit()
        
        temp_file = None
        try:
            # Create temp directory
            temp_dir = Path(tempfile.gettempdir()) / "downloads"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=doc.extension,
                dir=temp_dir
            )
            
            # Update status to processing
            doc.status = DocumentStatusType.PROCESSING
            session.commit()
            
            # Download file from S3
            try:
                self.s3_client.download_file(
                    file_url=doc.source,
                    file_path_to_save=temp_file.name
                )
            except Exception as e:
                logger.error(f"S3 download failed: {str(e)}")
                raise HTTPException(500, "Failed to download file from storage")
            
            
            # Extract and process text
            extractor = self.file_extractor.get_extractor_for_file(temp_file.name)
            if not extractor:
                raise HTTPException(400, f"No extractor found for file type: {doc.extension}")
                
            documents = parse_multiple_files(temp_file.name, extractor)
            
            # Process documents and create chunks
            for document in documents:
                chunks = rag_manager.process_document(
                    document=document,
                    document_id=doc.id,
                    collection_name=kb.uuid,
                    metadata={
                        **document.metadata,
                        "file_path": doc.name,
                        "created_at": doc.created_at.isoformat(),
                    }
                )
                
                # Create chunks in database
                for chunk_idx, chunk_data in enumerate(chunks):
                    chunk = DocumentChunk(
                        document_id=doc.id,
                        content=chunk_data.text,
                        chunk_index=chunk_idx,
                        dense_embedding=chunk_data.metadata["dense_embedding"],
                        sparse_embedding=chunk_data.metadata["sparse_embedding"],
                        extra_info=chunk_data.metadata,
                    )
                    session.add(chunk)
            
            # Update document status
            doc.status = DocumentStatusType.PROCESSED
            session.commit()
            session.refresh(doc)
            
            return doc
            
        except Exception as e:
            # Update document status to failed
            doc.status = DocumentStatusType.FAILED
            session.commit()
            
            logger.error(f"Error processing document: {str(e)}")
            raise HTTPException(500, f"Failed to process document: {str(e)}")
            
        finally:
            # Cleanup temp file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {str(e)}")
    async def _delete_document_file_from_s3(self, document: Document) -> None:
        """Helper method to delete a document file from S3"""
        try:
            if document.source:
                self.s3_client.remove_file(
                    object_name=document.source
                )
                logger.info(f"Deleted document file from S3: {document.source}")
        except Exception as e:
            logger.error(f"Error deleting document file from S3: {str(e)}")
            # Continue with deletion process even if S3 deletion fails
    
    async def _delete_document_from_vector_store(self,collection_name: str, document_id: int) -> None:
        """Helper method to delete document vectors from Qdrant"""
        try:
            # Delete vectors by filter
            self.qdrant_client.delete_vector(
                collection_name=collection_name,
                document_id=str(document_id)
            )
            logger.info(f"Deleted document vectors from Qdrant: collection={collection_name}, document_id={document_id}")
        except Exception as e:
            logger.error(f"Error deleting document from vector store: {str(e)}")
            # Continue with deletion process even if vector deletion fails    
    async def delete_document(
        self,
        session: Session,
        kb_id: int,
        document_id: int
    ) -> Dict[str, str]:
        """Delete a document and its chunks from DB, S3, and vector store"""
        # Find the document
        document = session.query(Document)\
            .filter(Document.id == document_id, Document.knowledge_base_id == kb_id)\
            .first()
            
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
        self,
        session: Session,
        kb_id: int
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
                rag_config = session.query(RAGConfig).filter(RAGConfig.id == rag_config_id).first()
                if rag_config:
                    session.delete(rag_config)
            
            session.commit()
            
            return {
                "status": "success", 
                "message": f"Knowledge base '{kb.name}' deleted successfully with all its documents and resources"
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting knowledge base: {str(e)}")
            raise HTTPException(500, f"Failed to delete knowledge base: {str(e)}")