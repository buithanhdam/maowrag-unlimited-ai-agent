from typing import List, Union, Any
from fastembed import (
    TextEmbedding, 
    SparseTextEmbedding, 
    LateInteractionTextEmbedding, 
    ImageEmbedding, 
    LateInteractionMultimodalEmbedding
)
from fastembed.rerank.cross_encoder import TextCrossEncoder
import numpy as np

class FastEmbedManager:
    def __init__(self):
        """
        Initialize the FastEmbedManager with methods for different embedding models.
        """
        self.text_embedding_model = None
        self.sparse_text_embedding_model = None
        self.late_interaction_text_model = None
        self.image_embedding_model = None
        self.late_interaction_multimodal_model = None
        self.reranker_model = None

    def init_dense_text_embedding(
        self, 
        model_name: str = "BAAI/bge-small-en-v1.5"
    ) -> List[np.ndarray]:
        """
        Initialize and generate dense text embeddings.
        
        :param model_name: Name of the dense text embedding model
        :return: List of embedding vectors
        """
        self.text_embedding_model = TextEmbedding(model_name=model_name)
        return self.text_embedding_model

    def init_sparse_text_embedding(
        self, 
        model_name: str = "Qdrant/bm25"
    ) -> SparseTextEmbedding:
        """
        Initialize sparse text embedding model.
        
        :param model_name: Name of the sparse text embedding model
        :return: Sparse text embedding model
        """
        self.sparse_text_embedding_model = SparseTextEmbedding(model_name=model_name)
        return self.sparse_text_embedding_model


    def init_late_interaction_embedding(
        self, 
        model_name: str = "colbert-ir/colbertv2.0"
    ) -> LateInteractionTextEmbedding:
        """
        Initialize late interaction text embedding model.
        
        :param model_name: Name of the late interaction model
        :return: Late interaction text embedding model
        """
        self.late_interaction_text_model = LateInteractionTextEmbedding(model_name=model_name)
        return self.late_interaction_text_model

    def init_image_embedding(
        self, 
        model_name: str = "Qdrant/clip-ViT-B-32-vision"
    ) -> ImageEmbedding:
        """
        Initialize image embedding model.
        
        :param model_name: Name of the image embedding model
        :return: Image embedding model
        """
        self.image_embedding_model = ImageEmbedding(model_name=model_name)
        return self.image_embedding_model

    def init_late_interaction_multimodal(
        self, 
        model_name: str = "Qdrant/colpali-v1.3-fp16"
    ) -> LateInteractionMultimodalEmbedding:
        """
        Initialize late interaction multimodal embedding model.
        
        :param model_name: Name of the multimodal embedding model
        :return: Late interaction multimodal embedding model
        """
        self.late_interaction_multimodal_model = LateInteractionMultimodalEmbedding(model_name=model_name)
        return self.late_interaction_multimodal_model

    def init_reranker(
        self, 
        model_name: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    ) -> TextCrossEncoder:
        """
        Initialize text cross-encoder reranker model.
        
        :param model_name: Name of the reranker model
        :return: Text cross-encoder model
        """
        self.reranker_model = TextCrossEncoder(model_name=model_name)
        return self.reranker_model

    def embed_text(
        self, 
        documents: str | List[str], 
        model_type: str = "dense"
    ) -> Union[List[np.ndarray], List[Any]]:
        """
        Generate embeddings for text documents.
        
        :param documents: List of text documents to embed
        :param model_type: Type of embedding model (dense, sparse, late)
        :return: List of embeddings
        """
        if model_type == "dense":
            if not self.text_embedding_model:
                self.init_dense_text_embedding()
            return list(self.text_embedding_model.embed(documents))
        
        elif model_type == "sparse":
            if not self.sparse_text_embedding_model:
                self.init_sparse_text_embedding()
            return list(self.sparse_text_embedding_model.embed(documents))
        
        elif model_type == "late":
            if not self.late_interaction_text_model:
                self.init_late_interaction_embedding()
            return list(self.late_interaction_text_model.embed(documents))
        
        raise ValueError(f"Unsupported model type: {model_type}")

    def embed_image(
        self, 
        images: List[str], 
        model_type: str = "standard"
    ) -> List[np.ndarray]:
        """
        Generate embeddings for images.
        
        :param images: List of image file paths
        :param model_type: Type of image embedding model
        :return: List of image embeddings
        """
        if model_type == "standard":
            if not self.image_embedding_model:
                self.init_image_embedding()
            return list(self.image_embedding_model.embed(images))
        
        elif model_type == "multimodal":
            if not self.late_interaction_multimodal_model:
                self.init_late_interaction_multimodal()
            return list(self.late_interaction_multimodal_model.embed_image(images))
        
        raise ValueError(f"Unsupported image model type: {model_type}")

    def rerank(
        self, 
        query: str, 
        documents: List[str]
    ) -> List[float]:
        """
        Rerank documents based on a query.
        
        :param query: Search query
        :param documents: List of documents to rerank
        :return: List of reranking scores
        """
        if not self.reranker_model:
            self.init_reranker()
        
        return list(self.reranker_model.rerank(query, documents))

    @classmethod
    def add_custom_model(
        cls, 
        model_type: str, 
        model_name: str, 
        **kwargs
    ):
        """
        Add a custom model to the respective embedding or reranking class.
        
        :param model_type: Type of model (text, sparse, late, reranker)
        :param model_name: Name of the custom model
        :param kwargs: Additional model configuration parameters
        """
        if model_type == "text":
            TextEmbedding.add_custom_model(model=model_name, **kwargs)
        elif model_type == "sparse":
            SparseTextEmbedding.add_custom_model(model=model_name, **kwargs)
        elif model_type == "late":
            LateInteractionTextEmbedding.add_custom_model(model=model_name, **kwargs)
        elif model_type == "reranker":
            TextCrossEncoder.add_custom_model(model=model_name, **kwargs)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

# Example usage
if __name__ == "__main__":
    # Initialize the manager
    manager = FastEmbedManager()

    # Example documents
    documents = [
        "This is built to be faster and lighter than other embedding libraries.",
        "fastembed is supported by and maintained by Qdrant."
    ]

    # Dense text embedding
    # dense_embeddings = manager.embed_text(documents, model_type="dense")
    # print("Dense Embeddings:", len(dense_embeddings[0]))

    # Sparse text embedding
    sparse_embeddings = manager.embed_text(documents, model_type="sparse")
    print("Sparse Embeddings:", sparse_embeddings)

    # Reranking
    query = "Who maintains Qdrant?"
    rerank_scores = manager.rerank(query, documents)
    print("Rerank Scores:", rerank_scores)