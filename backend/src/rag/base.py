from abc import ABC, abstractmethod
import json
from typing import List, Optional
import uuid
from fastembed import SparseTextEmbedding
from tqdm import tqdm
from qdrant_client.http import models
from llama_index.core import Document, Settings
from llama_index.llms.gemini import Gemini
# from llama_index.embeddings.gemini import GeminiEmbedding
from .embed.gemini_embedding_model import GeminiEmbedding
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.schema import NodeWithScore
from src.db.qdrant import QdrantVectorDatabase
from src.logger import get_formatted_logger
from llama_index.core.node_parser import SentenceSplitter
from src.config import QdrantPayload
logger = get_formatted_logger(__file__)

class BaseRAG(ABC):
    """
    Abstract base class for RAG implementations
    """
    def __init__(
        self,
        qdrant_url: str,
        gemini_api_key: str,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize Gemini models
        self.llm = Gemini(
            api_key=gemini_api_key,
            temperature=0.1
        )
        self.dense_embedding_model = GeminiEmbedding(
            api_key=gemini_api_key,
            model_name="models/text-embedding-004",
           # gemini-embedding-exp-03-07 
            output_dimensionality=768
        )
        self.sparse_embedding_model = SparseTextEmbedding(model_name="Qdrant/bm25",lazy_load=True)
        
        # Set global settings
        Settings.llm = self.llm
        Settings.embed_model = self.dense_embedding_model
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap
        
        # Initialize document parser
        self.parser = SimpleNodeParser.from_defaults()
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantVectorDatabase(url=qdrant_url)
        
        logger.info(f"Initialized {self.__class__.__name__}")
    def split_document(
        self,
        document: Document,
        show_progress: bool = True
    ) -> List[Document]:
        """
        Split document into chunks
        """
        nodes = self.parser.get_nodes_from_documents([document])
        
        chunks = []
        nodes_iter = tqdm(nodes, desc="Splitting...") if show_progress else nodes
        
        for node in nodes_iter:
            chunk_id = str(uuid.uuid4())
            chunk = Document(
                text=node.get_content(),
                metadata={
                    **document.metadata,
                    "chunk_id": chunk_id
                }
            )
            chunks.append(chunk)
            
        return chunks
    def process_document(
        self,
        document: str,
        collection_name: str,
        document_id: Optional[str] | Optional[int] = None,
        metadata: Optional[dict] = None,
        show_progress: bool = True,
    ) -> List[Document]:
        if document_id is None:
            document_id = str(uuid.uuid4())

        try:
            doc = Document(text=document, metadata=metadata or {})
            chunks = self.split_document(doc, show_progress=show_progress)

            # Index chunks
            chunks_iter = tqdm(chunks, desc="Indexing...") if show_progress else chunks
            for chunk in chunks_iter:
                dense_embedding = self.dense_embedding_model.get_text_embedding(chunk.text)
                sparse_embedding = self.sparse_embedding_model.embed(chunk.text)
                sparse_embedding = list(sparse_embedding)[0].as_object()
                # Ensure collection exists
                if chunk == chunks[0]:  # Only check on first chunk
                    self.ensure_collection(collection_name, len(dense_embedding))

                payload = QdrantPayload(
                    document_id=document_id,
                    text=chunk.text,
                    vector_id=chunk.metadata["chunk_id"],
                )

                self.qdrant_client.add_vector(
                    collection_name=collection_name,
                    vector_id=chunk.metadata["chunk_id"],
                    dense_vector=dense_embedding,
                    sparse_vector=sparse_embedding,
                    payload=payload,
                )
                chunk.metadata["dense_embedding"] = json.dumps(dense_embedding)
                chunk.metadata["sparse_embedding"] = json.dumps({key: value.tolist() for key, value in sparse_embedding.items()})

                logger.info(
                    f"Successfully processed document {document_id} with chunk {chunk.metadata['chunk_id']}"
                )
            return chunks_iter

        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise
    def ensure_collection(self, collection_name: str, vector_size: int):
        """
        Ensure collection exists in vector store
        """
        if not self.qdrant_client.check_collection_exists(collection_name):
            self.qdrant_client.create_collection(collection_name, vector_size)
            
    def convert_scored_points_to_nodes(
        self,
        scored_points: List[models.ScoredPoint],
        score_threshold: float = 0.0
    ) -> List[NodeWithScore]:
        """
        Convert Qdrant ScoredPoint results to LlamaIndex NodeWithScore
        
        Args:
            scored_points: List of Qdrant search results
            score_threshold: Minimum score threshold for including results
            
        Returns:
            List of LlamaIndex NodeWithScore objects
        """
        nodes = []
        
        for point in scored_points:
            if point.score < score_threshold:
                continue
                
            # Create node with text and metadata
            doc = Document(
                text=point.payload.get("text", ""),
                metadata={
                    "document_id": point.payload.get("document_id"),
                    "vector_id": point.payload.get("vector_id"),
                    "score": point.score,
                    # Add any other metadata from payload
                    **{k: v for k, v in point.payload.items() 
                    if k not in ["text", "document_id", "vector_id"]}
                }
            )
            
            nodes.append(NodeWithScore(node=doc, score=point.score))
                # initialize node parser
        # splitter = SentenceSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)

        # nodes = splitter.get_nodes_from_documents(docs)
            
        return nodes

    @abstractmethod
    def search(
        self,
        query: str,
        collection_name: str = "documents",
        limit: int = 5,
        score_threshold: int =0.5
    ) -> str:
        """Search for relevant documents and generate response"""
        pass

    def delete_document(
        self,
        collection_name: str,
        document_id: str | int
    ):
        """Delete a document from the system""" 
        self.qdrant_client.delete_vector(
            collection_name=collection_name, document_id=document_id
        )
        logger.info(f"Deleted document {document_id}")
