from qdrant_client.http import models
from .base import BaseRAG


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
        score_threshold: int = 0.5,
    ) -> str:
        try:

            # Step 1: Convert user query to embedding
            self.logger.info(
                "[Hybrid Search] - Step 1: Convert user query to embedding"
            )
            dense_embedding = self.dense_embedding_model.get_text_embedding(query)
            sparse_embedding = self.sparse_embedding_model.embed(query)
            sparse_embedding = list(sparse_embedding)[0].as_object()

            # Step 2: Perform hybrid vector search using dense and sparse embeddings (BM25)
            self.logger.info(
                "[Hybrid Search] - Step 2: Perform hybrid vector search using dense and sparse embeddings (BM25)"
            )
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
            self.logger.info(normal_results)
            # Step 3: Filter results based on score threshold
            self.logger.info(
                "[Hybrid Search] - Step 3: Filter results based on score threshold"
            )
            contexts = [
                result.payload["text"]
                for result in normal_results
                if result.score >= score_threshold
            ] or [result.payload["text"] for result in normal_results]

            # Step 4: Generate final response
            self.logger.info("[Hybrid Search] - Step 4: Generate final response")
            prompt = f"""Given the following context and question, provide a comprehensive answer based solely on the provided context. If the context doesn't contain relevant information, say so.

            Context:
            {' '.join(contexts)}

            Question:
            {query}

            Answer:"""

            response = self.llm.complete(prompt).text
            return response

        except Exception as e:
            self.logger.error(f"Error during search: {str(e)}")
            raise
