from typing import List
from qdrant_client.http import models
from .base import BaseRAG
from llama_index.core import PromptTemplate
from llama_index.core.schema import NodeWithScore


class FusionRAG(BaseRAG):
    """
    Fusion RAG implementation using vector search, generate sub-queries and re-rank document score
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def fuse_rerank(
        self, nodes_with_scores: List[NodeWithScore], similarity_top_k: int = 2
    ):
        """Fuse results."""
        k = 60.0  # `k` is a parameter used to control the impact of outlier rankings.
        fused_scores = {}
        text_to_node = {}

        # compute reciprocal rank scores
        for rank, node_with_score in enumerate(
            sorted(nodes_with_scores, key=lambda x: x.score or 0.0, reverse=True)
        ):
            text = node_with_score.node.get_content()
            text_to_node[text] = node_with_score
            if text not in fused_scores:
                fused_scores[text] = 0.0
            fused_scores[text] += 1.0 / (rank + k)

        # sort results
        reranked_results = dict(
            sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        )

        # adjust node scores
        reranked_nodes: List[NodeWithScore] = []
        for text, score in reranked_results.items():
            reranked_nodes.append(text_to_node[text])
            reranked_nodes[-1].score = score

        return reranked_nodes[:similarity_top_k]

    def search(
        self,
        query: str,
        collection_name: str = "documents",
        limit: int = 5,
        score_threshold: int = 0.5,
    ) -> str:
        try:
            # Step 1: Generate sub-queries from user query
            self.logger.info(
                "[Fuse Search] - Step 1: Generate sub-queries from user query"
            )
            query_gen_prompt_str = (
                "You are a helpful assistant that generates multiple search queries based on a "
                "single input query for rag business system. Generate {num_queries} search queries, one on each line, "
                "related to the following input query:\n"
                "Query: {query}\n"
                "Queries:\n"
            )
            query_gen_prompt = PromptTemplate(query_gen_prompt_str)
            fmt_prompt = query_gen_prompt.format(num_queries=2, query=query)
            response = self.llm.complete(fmt_prompt)
            queries = response.text.split("\n")
            queries.remove("")  # Remove empty string
            queries.append(query)
            self.logger.info(f"Generated sub-queries: {queries}")

            # Step 2: Convert sub-queries and user query to embeddings
            self.logger.info(
                "[Fuse Search] - Step 2: Convert sub-queries and user query to embeddings"
            )
            dense_embeddings = self.dense_embedding_model.get_text_embedding_batch(
                queries
            )

            batch_sparse_embeddings = self.sparse_embedding_model.embed(queries)
            batch_sparse_embeddings = list(batch_sparse_embeddings)
            sparse_embeddings = [
                sparse_embedding.as_object()
                for sparse_embedding in batch_sparse_embeddings
            ]

            # Step 3: Perform multi-vector search using query embedding and bm25
            self.logger.info(
                "[Fuse Search] - Step 3: Perform multi-vector search using query embedding and bm25"
            )
            sub_query_results = self.qdrant_client.hybrid_search_multi_vector(
                dense_vectors=dense_embeddings,
                sparse_vectors=sparse_embeddings,
                collection_name=collection_name,
                limit=limit,
                search_params=models.SearchParams(
                    quantization=models.QuantizationSearchParams(
                        ignore=False,
                        rescore=True,
                        oversampling=2.0,
                    )
                ),
            )
            self.logger.info(sub_query_results)
            # Step 4: Rerank and Filter results based on score threshold
            self.logger.info(
                "[Fuse Search] - Step 4: Rerank and Filter results based on score threshold"
            )
            doc_nodes = self.convert_scored_points_to_nodes(
                sub_query_results, score_threshold=score_threshold
            )

            contexts = self.fuse_rerank(doc_nodes, similarity_top_k=limit)
            self.logger.info(f"contexts: {contexts}")

            # Step 5: Generate final response
            self.logger.info("[Fuse Search] - Step 5: Generate final response")
            prompt = f"""Given the following context and question, provide a comprehensive answer based solely on the provided context. If the context doesn't contain relevant information, say so.

            Context:
            {' '.join([node.node.get_content() for node in contexts])}

            Question:
            {query}

            Answer:"""

            response = self.llm.complete(prompt).text
            return response

        except Exception as e:
            self.logger.error(f"Error during search: {str(e)}")
            raise
