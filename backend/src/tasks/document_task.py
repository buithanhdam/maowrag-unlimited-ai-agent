#src/tasks/document_task.py
import os
import tempfile
from pathlib import Path
import uuid
from datetime import datetime
import celery
from src.celery import celery_app
from src.db.mysql import get_db_session_local
from src.db.models import Document, KnowledgeBase
from src.enums import DocumentStatusType
from src.db.qdrant import QdrantVectorDatabase
from src.db.aws import get_aws_s3_client
from src.readers import parse_multiple_files, FileExtractor
from src.rag.rag_manager import RAGManager
from src.config import global_config
from src.logger import get_formatted_logger

logger = get_formatted_logger(__file__)

# Initialize services that will be used by tasks
file_extractor = FileExtractor()
qdrant_client = QdrantVectorDatabase(url=global_config.QDRANT_URL)
s3_client = get_aws_s3_client()

@celery_app.task(name="document.upload",bind=True)
def upload_document(
    self: celery.Task,
    bucket_name: str,
    file_content: bytes,
    filename: str
    ):
    temp_file = None
    try:
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100})
        # Create temp directory if it doesn't exist
        temp_dir = Path(tempfile.gettempdir()) / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        original_filename = Path(filename)
        extension = original_filename.suffix.lower()
        
        # Create temp file with unique name
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension,
            dir=temp_dir
        )
        
        # Write content to temp file
        with open(temp_file.name, 'wb') as f:
            f.write(file_content)
        self.update_state(state="PROGRESS", meta={"current": 50, "total": 100})
        # Generate S3 path
        date_path = datetime.now().strftime("%Y/%m/%d")
        file_name = f"{uuid.uuid4()}_{filename}"
        
        # Upload to S3
        try:
            file_path_in_s3 = s3_client.upload_file(
                bucket_name=bucket_name,
                object_name=os.path.join(date_path, file_name),
                file_path=str(temp_file.name),
            )
            self.update_state(state="PROGRESS", meta={"current": 100, "total": 100})
        except Exception as e:
            logger.error(f"S3 upload failed: {str(e)}")
            return {
                "status":"error",
                "task_id":self.request.id,
                "message": f"Failed to upload file to storage {str(e)}"
                }
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {str(e)}")
        return {
            "status": "success",
            "task_id":self.request.id,
            "file_path_in_s3":file_path_in_s3,
            "file_name":file_name,
            "message": "Document uploaded successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating document: {str(e)}")
        return {"status": "error","task_id":self.request.id, "message": f"Failed to create document: {str(e)}"}

# @celery_app.task(name="document.process")
# def process_document(kb_id: int, doc_id: int):
#     """
#     Celery task to process document content and create embeddings
    
#     Args:
#         kb_id: Knowledge base ID
#         doc_id: Document ID
#     """
#     session = get_db_session()
#     temp_file = None
    
#     try:
#         # Get knowledge base and document
#         kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
#         if not kb:
#             logger.error(f"Knowledge base not found: {kb_id}")
#             return {"status": "error", "message": "Knowledge base not found"}
            
#         doc = session.query(Document).filter(
#             Document.id == doc_id,
#             Document.knowledge_base_id == kb_id
#         ).first()
#         if not doc:
#             logger.error(f"Document not found: kb_id={kb_id}, doc_id={doc_id}")
#             return {"status": "error", "message": "Document not found"}
        
#         # Get RAG config
#         rag_config = kb.rag_config
#         if not rag_config:
#             logger.error(f"RAG Config not found for kb_id={kb_id}")
#             return {"status": "error", "message": "RAG Config not found"}
        
#         # Initialize RAG manager
#         rag_manager = RAGManager.create_rag(
#             rag_type=rag_config.rag_type,
#             vector_db_url=global_config.QDRANT_URL,
#             llm_type=rag_config.llm_type if hasattr(rag_config, 'llm_type') else None,
#             chunk_size=rag_config.chunk_size,
#             chunk_overlap=rag_config.chunk_overlap,
#         )
        
#         # Update document status
#         doc.status = DocumentStatusType.PENDING
#         session.commit()
        
#         # Create temp directory
#         temp_dir = Path(tempfile.gettempdir()) / "downloads"
#         temp_dir.mkdir(parents=True, exist_ok=True)
        
#         # Create temp file
#         temp_file = tempfile.NamedTemporaryFile(
#             delete=False,
#             suffix=doc.extension,
#             dir=temp_dir
#         )
        
#         # Update status to processing
#         doc.status = DocumentStatusType.PROCESSING
#         session.commit()
        
#         # Download file from S3
#         try:
#             s3_client.download_file(
#                 file_url=doc.source,
#                 file_path_to_save=temp_file.name
#             )
#         except Exception as e:
#             logger.error(f"S3 download failed: {str(e)}")
#             doc.status = DocumentStatusType.FAILED
#             session.commit()
#             return {"status": "error", "message": "Failed to download file from storage"}
        
#         # Extract and process text
#         extractor = file_extractor.get_extractor_for_file(temp_file.name)
#         if not extractor:
#             doc.status = DocumentStatusType.FAILED
#             session.commit()
#             logger.error(f"No extractor found for file type: {doc.extension}")
#             return {"status": "error", "message": f"No extractor found for file type: {doc.extension}"}
            
#         documents = parse_multiple_files(temp_file.name, extractor)
        
#         # Process documents and create chunks
#         for document in documents:
#             chunks = rag_manager.process_document(
#                 document=document,
#                 document_id=doc.id,
#                 collection_name=kb.specific_id,
#                 metadata={
#                     **document.metadata,
#                     "file_path": doc.name,
#                     "created_at": doc.created_at.isoformat(),
#                 }
#             )
            
#             # Create chunks in database
#             from src.db.models import DocumentChunk
            
#             for chunk_idx, chunk_data in enumerate(chunks):
#                 chunk = DocumentChunk(
#                     document_id=doc.id,
#                     content=chunk_data.text,
#                     chunk_index=chunk_idx,
#                     dense_embedding=chunk_data.metadata.get("dense_embedding"),
#                     sparse_embedding=chunk_data.metadata.get("sparse_embedding"),
#                     extra_info=chunk_data.metadata,
#                 )
#                 session.add(chunk)
        
#         # Update document status
#         doc.status = DocumentStatusType.PROCESSED
#         session.commit()
        
#         return {"status": "success", "message": "Document processed successfully", "document_id": doc.id}
        
#     except Exception as e:
#         # Update document status to failed
#         if 'doc' in locals() and doc:
#             doc.status = DocumentStatusType.FAILED
#             session.commit()
        
#         logger.error(f"Error processing document: {str(e)}")
#         return {"status": "error", "message": f"Failed to process document: {str(e)}"}
        
#     finally:
#         # Cleanup temp file
#         if temp_file and os.path.exists(temp_file.name):
#             try:
#                 os.unlink(temp_file.name)
#             except Exception as e:
#                 logger.warning(f"Failed to delete temp file: {str(e)}")
        
#         session.close()

# @celery_app.task(name="document.delete")
# def delete_document(kb_id: int, document_id: int):
#     """
#     Celery task to delete a document and its chunks from DB, S3, and vector store
    
#     Args:
#         kb_id: Knowledge base ID
#         document_id: Document ID
#     """
#     session = get_db_session()
    
#     try:
#         # Find the document
#         document = session.query(Document)\
#             .filter(Document.id == document_id, Document.knowledge_base_id == kb_id)\
#             .first()
                
#         if not document:
#             logger.error(f"Document not found: kb_id={kb_id}, document_id={document_id}")
#             return {"status": "error", "message": "Document not found"}
        
#         # Get the knowledge base
#         kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
#         if not kb:
#             logger.error(f"Knowledge base not found: {kb_id}")
#             return {"status": "error", "message": "Knowledge base not found"}
        
#         # Step 1: Delete from S3
#         try:
#             if document.source:
#                 s3_client.remove_file(object_name=document.source)
#                 logger.info(f"Deleted document file from S3: {document.source}")
#         except Exception as e:
#             logger.error(f"Error deleting document file from S3: {str(e)}")
#             # Continue with deletion process even if S3 deletion fails
        
#         # Step 2: Delete from vector store
#         try:
#             qdrant_client.delete_vector(
#                 collection_name=kb.specific_id,
#                 document_id=str(document_id)
#             )
#             logger.info(f"Deleted document vectors from Qdrant: collection={kb.specific_id}, document_id={document_id}")
#         except Exception as e:
#             logger.error(f"Error deleting document from vector store: {str(e)}")
#             # Continue with deletion process even if vector deletion fails
        
#         # Step 3: Delete from database (this will cascade to document chunks)
#         session.delete(document)
#         session.commit()
        
#         return {"status": "success", "message": "Document deleted successfully"}
        
#     except Exception as e:
#         session.rollback()
#         logger.error(f"Error deleting document: {str(e)}")
#         return {"status": "error", "message": f"Failed to delete document: {str(e)}"}
#     finally:
#         session.close()

# @celery_app.task(name="document.download")
# def download_document(kb_id: int, document_id: int, destination_path: str = None):
#     """
#     Celery task to download a document from S3
    
#     Args:
#         kb_id: Knowledge base ID
#         document_id: Document ID
#         destination_path: Optional path to save the file
#     """
#     session = get_db_session()
    
#     try:
#         # Find the document
#         document = session.query(Document)\
#             .filter(Document.id == document_id, Document.knowledge_base_id == kb_id)\
#             .first()
                
#         if not document:
#             logger.error(f"Document not found: kb_id={kb_id}, document_id={document_id}")
#             return {"status": "error", "message": "Document not found"}
        
#         # Create temp directory if destination path is not provided
#         if not destination_path:
#             temp_dir = Path(tempfile.gettempdir()) / "downloads"
#             temp_dir.mkdir(parents=True, exist_ok=True)
#             destination_path = str(temp_dir / f"{document.name}")
        
#         # Download file from S3
#         try:
#             s3_client.download_file(
#                 file_url=document.source,
#                 file_path_to_save=destination_path
#             )
#             logger.info(f"Downloaded document file from S3: {document.source} to {destination_path}")
#         except Exception as e:
#             logger.error(f"S3 download failed: {str(e)}")
#             return {"status": "error", "message": "Failed to download file from storage"}
        
#         return {
#             "status": "success", 
#             "message": "Document downloaded successfully",
#             "file_path": destination_path
#         }
        
#     except Exception as e:
#         logger.error(f"Error downloading document: {str(e)}")
#         return {"status": "error", "message": f"Failed to download document: {str(e)}"}
#     finally:
#         session.close()

# @celery_app.task(name="kb.delete")
# def delete_knowledge_base(kb_id: int):
#     """
#     Celery task to delete a knowledge base and all its associated resources
    
#     Args:
#         kb_id: Knowledge base ID
#     """
#     session = get_db_session()
    
#     try:
#         # Find the knowledge base
#         kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
#         if not kb:
#             logger.error(f"Knowledge base not found: {kb_id}")
#             return {"status": "error", "message": "Knowledge base not found"}
        
#         # Step 1: Delete the Qdrant collection for this KB
#         try:
#             qdrant_client.delete_collection(kb.specific_id)
#             logger.info(f"Deleted Qdrant collection: {kb.specific_id}")
#         except Exception as e:
#             logger.error(f"Error deleting Qdrant collection: {str(e)}")
                       
#         # Step 2: Delete the S3 bucket for this KB
#         try:
#             s3_client.remove_bucket(kb.specific_id)
#             logger.info(f"Deleted S3 bucket: {kb.specific_id}")
#         except Exception as e:
#             logger.error(f"Error deleting S3 bucket: {str(e)}")
        
#         # Step 3: Delete the KB and its RAG config from the database
#         # This will cascade delete documents and chunks
#         rag_config_id = kb.rag_config_id  # Store before deleting KB
        
#         # Delete the KB first (this should cascade to documents and chunks)
#         session.delete(kb)
#         session.flush()
        
#         # Delete the RAG config if it exists
#         if rag_config_id:
#             from src.db.models import RAGConfig
#             rag_config = session.query(RAGConfig).filter(RAGConfig.id == rag_config_id).first()
#             if rag_config:
#                 session.delete(rag_config)
        
#         session.commit()
        
#         return {
#             "status": "success", 
#             "message": f"Knowledge base '{kb.name}' deleted successfully with all its documents and resources"
#         }
        
#     except Exception as e:
#         session.rollback()
#         logger.error(f"Error deleting knowledge base: {str(e)}")
#         return {"status": "error", "message": f"Failed to delete knowledge base: {str(e)}"}
#     finally:
#         session.close()

