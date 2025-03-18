from qdrant_client.http import models
from llama_index.retrievers.bm25 import BM25Retriever
from src.logger import get_formatted_logger
from .base import BaseRAG
import Stemmer

logger = get_formatted_logger(__file__)

class HybridRAG(BaseRAG):
    """
    Hybrid RAG implementation combining vector search and BM25 using Qdrant directly
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
            
            # Step 1: Convert user query to embedding
            query_embedding = self.embedding_model.get_text_embedding(query)
            
            # Step 2: Perform vector search using query embedding
            normal_results = self.qdrant_client.search_vector(
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
            logger.info(normal_results)
            
            # Step 3: BM25 retrieval
            bm25_points = self.qdrant_client.search_vector(
                collection_name=collection_name,
                vector=query_embedding,
                limit=50,
                search_params=models.SearchParams(
                    quantization=models.QuantizationSearchParams(
                        ignore=False,
                        rescore=True,
                        oversampling=2.0,
                    )
                ),
            )
            doc_nodes = self.convert_scored_points_to_nodes(
                bm25_points,
                score_threshold=score_threshold
            )
            if doc_nodes:
                ## Perform BM25 search
                bm25_retriever = BM25Retriever.from_defaults(
                    nodes=doc_nodes,
                    similarity_top_k=limit,
                    stemmer=Stemmer.Stemmer("english"),
                    language="english",
                )
                bm25_results = bm25_retriever.retrieve(query)
                logger.info(bm25_results)
                
                # Step 4: Combine results
                all_texts = set()
                contexts = []
                
                ## Add vector search results
                for result in normal_results:
                    text = result.payload["text"]
                    if text not in all_texts:
                        contexts.append(text)
                        all_texts.add(text)
                
                ## Add BM25 results
                for node in bm25_results:
                    text = node.get_content()
                    if text not in all_texts and len(contexts) < limit:
                        contexts.append(text)
                        all_texts.add(text)
            else:
                contexts = [result.payload["text"] for result in normal_results]
            
            # Step 5: Generate final response
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