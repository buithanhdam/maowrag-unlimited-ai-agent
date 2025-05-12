from typing import List, Dict
from llama_index.core import Document
from qdrant_client.http import models
from src.logger import get_formatted_logger
from .base import BaseRAG
logger = get_formatted_logger(__file__)

class NaiveRAG(BaseRAG):
    """
    Standard RAG implementation using vector search
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document_store: Dict[str, List[Document]] = {}

    def search(
        self,
        query: str,
        collection_name: str = "documents",
        limit: int = 5,
        score_threshold: int =0.5
    ) -> str:
        try:
            
            # Step 1: Convert user query to embedding
            logger.info("[Normal Search] - Step 1: Convert user query to embedding")
            query_embedding = self.dense_embedding_model.get_text_embedding(query)
            
            # Step 2: Perform vector search using query embedding
            logger.info("[Normal Search] - Step 2: Perform vector search using query embedding")
            results = self.qdrant_client.search_vector(
                collection_name=collection_name,
                vector=query_embedding,
                limit=limit,
                search_params=models.SearchParams(
                    quantization=models.QuantizationSearchParams(
                        ignore=False,
                        rescore=True,
                        oversampling=2.0,
                    )
                ),
            )
            
            # Step 3: Filter results based on score threshold
            logger.info("[Normal Search] - Step 3: Filter results based on score threshold")
            contexts = [
                result.payload["text"]
                for result in results
                if result.score >= score_threshold
            ] or [result.payload["text"] for result in results]
            
            # Step 4: Generate final response
            logger.info("[Normal Search] - Step 4: Generate final response")
            prompt = f"""Given the following context and question, provide a comprehensive answer based solely on the provided context. If the context doesn't contain relevant information, say so.

Context:
{' '.join(contexts)}

Question:
{query}

Answer:"""
            
            response = self.llm.complete(prompt).text
            return response
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            raise