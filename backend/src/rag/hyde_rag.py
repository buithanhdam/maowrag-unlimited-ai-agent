from qdrant_client.http import models
from src.logger import get_formatted_logger
from .base import BaseRAG

logger = get_formatted_logger(__file__)

class HyDERAG(BaseRAG):
    """
    HyDE RAG implementation Hybrid Rag and Hypothetical Document Embeddings using Qdrant directly
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def search(
        self,
        query: str,
        collection_name: str = "documents",
        limit: int = 5,
        score_threshold: int =0.5
    ) -> str:
        try:
            # Step 1: Generate hypothetical document using LLM
            hypothetical_prompt = f"""Generate a short summary hypothetical document that could answer the following query:
            Query:{query}
            Hypothetical Document:"""
            hypothetical_document = self.llm.complete(hypothetical_prompt).text.strip()
            logger.info(hypothetical_document)
            
            # Step 2: Convert hypothetical document to embedding
            dense_embedding = self.dense_embedding_model.get_text_embedding(hypothetical_document)
            sparse_embedding = self.sparse_embedding_model.embed(hypothetical_document)
            sparse_embedding = list(sparse_embedding)[0].as_object()
            
            # Step 3: Perform hybrid vector search using dense and sparse embeddings (BM25) with hypothetical embedding
            normal_results = self.qdrant_client.hybrid_search_vector(
                collection_name=collection_name,
                dense_vector=dense_embedding,
                sparse_vector=sparse_embedding,
                limit=limit,
                search_params=models.SearchParams(
                    quantization=models.QuantizationSearchParams(
                        ignore=False,
                        rescore=True,
                        oversampling=2.0,
                    )
                ),
            )
            logger.info(normal_results)
            contexts = [result.payload["text"] for result in normal_results]
            
             # Step 4: Generate final response
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
