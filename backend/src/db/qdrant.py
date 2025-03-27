import sys
from src.logger import get_formatted_logger
from pathlib import Path
import logging
from abc import ABC, abstractmethod
from qdrant_client.http import models
from qdrant_client import QdrantClient
from typing import List, Dict, Any, Optional
from fastembed.common.types import NumpyArray
from qdrant_client.http.exceptions import ResponseHandlingException
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    after_log,
    before_sleep_log,
    retry_if_exception_type,
)

sys.path.append(str(Path(__file__).parent.parent.parent))
from qdrant_client.models import ScoredPoint
from src.config import QdrantPayload
from src.logger import get_formatted_logger
logger = get_formatted_logger(__file__)


class BaseVectorDatabase(ABC):
    @abstractmethod
    def check_collection_exists(self, collection_name: str):
        """
        Check if the collection exists

        Args:
            collection_name (str): Collection name to check
        """
        pass

    @abstractmethod
    def test_connection(self):
        """
        Test the connection with the server.
        """
        pass

    @abstractmethod
    def create_collection(self, collection_name: str, vector_size: int):
        """
        Create a new collection

        Args:
            collection_name (str): Collection name
            vector_size (int): Vector size
        """
        pass

    @abstractmethod
    def add_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: List[float],
        payload: Dict[str, Any],
    ):
        """
        Add a vector to the collection

        Args:
            collection_name (str): Collection name to add
            vector_id (str): Vector ID
            vector (List[float]): Vector embedding
            payload (Dict[str, Any]): Payload for the vector
        """
        pass


class QdrantVectorDatabase(BaseVectorDatabase):
    """
    QdrantVectorDatabase client
    """

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_fixed(5),
        after=after_log(logger, logging.DEBUG),
        before_sleep=before_sleep_log(logger, logging.DEBUG),
        retry=retry_if_exception_type(ConnectionError),
    )
    def __init__(self, url: str, distance: str = models.Distance.COSINE) -> None:
        self.url = url
        self.client = QdrantClient(url)
        self.distance = distance
        self.test_connection()

        logger.info("Qdrant client initialized successfully !!!")

    def test_connection(self):
        """
        Test the connection with the Qdrant server.
        """
        try:
            self.client.get_collections()
        except ResponseHandlingException:
            raise ConnectionError("Qdrant connection failed")

    def check_collection_exists(self, collection_name: str):
        return self.client.collection_exists(collection_name)

    def create_collection(self, collection_name: str, vector_size: int = 768):
        if not self.client.collection_exists(collection_name):
            logger.info(f"Creating collection {collection_name}")
            self.client.create_collection(
                collection_name,
                vectors_config={
                    "dense": models.VectorParams(
                        size=vector_size,
                        distance=self.distance
                        ),
                    "late-interaction": models.VectorParams(
                        size=vector_size,
                        distance=self.distance,
                        multivector_config=models.MultiVectorConfig(
                            comparator=models.MultiVectorComparator.MAX_SIM
                        ),
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(
                        index=models.SparseIndexParams(
                            on_disk=False,
                        )
                    )
                },
                optimizers_config=models.OptimizersConfigDiff(
                    default_segment_number=5,
                    indexing_threshold=0,
                ),
                quantization_config=models.BinaryQuantization(
                    binary=models.BinaryQuantizationConfig(always_ram=True),
                ),
            )

    def add_vector(
        self,
        collection_name: str,
        vector_id: str,
        dense_vector: List[float],
        sparse_vector:dict[str, NumpyArray],
        payload: QdrantPayload,
    ):
        """
        Add a vector to the collection

        Args:
            collection_name (str): Collection name to add
            vector_id (str): Vector ID
            dense_vector (List[float]): Dense vector
            sparse_vector (dict[str, NumpyArray]): Sparse vector
            payload (QdrantPayload): Payload for the vector
        """
        if not self.check_collection_exists(collection_name):
            self.create_collection(collection_name, len(dense_vector))

        self.client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=vector_id,
                    payload=payload.model_dump(),
                    vector={
                        "dense":dense_vector,
                        "sparse": models.SparseVector(
                        indices=sparse_vector.get("indices",[]), values=sparse_vector.get("values",[])
                    )
                    },
                )
            ],
        )

    def delete_vector(self, collection_name: str, document_id: str|int):
        """
        Delete a vector from the collection

        Args:
            collection_name (str): Collection name to delete
            document_id (str | int): Document ID to delete
        """

        if not self.check_collection_exists(collection_name):
            logger.debug(f"Collection {collection_name} does not exist")
            return

        logger.debug(
            "collection_name: %s - document_id: %s", collection_name, document_id
        )
        try:
            self.client.delete(
                collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
        except Exception as e:
            logger.error(f"Error deleting vector: {str(e)}")
            raise e

    def delete_collection(self, collection_name: str):
        """
        Delete a collection

        Args:
            collection_name (str): Collection name to delete
        """
        if not self.check_collection_exists(collection_name):
            logger.debug(f"Collection {collection_name} does not exist")
            return
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Collection {collection_name} deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise e

    
    def search_vector(
        self,
        collection_name: str,
        vector: list[float],
        search_params: models.SearchParams,
        limit :int = 5,
        using="dense"
    ) -> List[ScoredPoint]:
        """
        Search for a vector in the collection
        Args:
            collection_name (str): Collection name to search
            vector (list[float]): Vector embedding
            search_params (models.SearchParams): Search parameters
        Returns:
            List[models.PointStruct]: List of points
        """
        
        return self.client.query_points(
            collection_name=collection_name,
            query=vector,
            search_params=search_params,
            with_payload=True,
            using=using,
            limit=limit
        ).points
    
    def hybrid_search_vector(
        self,
        collection_name: str,
        dense_vector: List[float],
        sparse_vector:dict[str, NumpyArray],
        search_params: models.SearchParams,
        limit :int = 5,
    ) -> List[ScoredPoint]:
        """
        Hybrid Search for a vector in the collection
        Args:
            collection_name (str): Collection name to search
            dense_vector (List[float]): Dense vector
            sparse_vector (dict[str, NumpyArray]): Sparse vector
            search_params (models.SearchParams): Search parameters
        Returns:
            List[models.PointStruct]: List of points
        """
        return self.client.query_points(
            collection_name=collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=limit,
                ),
                # Here we just add another 25 documents using the sparse
                # vectors only.
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_vector.get("indices",[]),
                        values=sparse_vector.get("values",[])
                    ),
                    using="sparse",
                    limit=limit,
                ),
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF,
            ),
            search_params=search_params,
            with_payload=True,
            limit=limit
        ).points
        
    def hybrid_search_multi_vector(
        self,
        collection_name: str,
        dense_vectors: List[List[float]],
        sparse_vectors:List[dict[str, NumpyArray]],
        search_params: models.SearchParams,
        limit :int = 5,
    ) -> List[ScoredPoint]:
        """
        Hybrid Search for multi vector in the collection
        Args:
            collection_name (str): Collection name to search
            dense_vectors (List[List[float]]): List Dense vector
            sparse_vectors (List[dict[str, NumpyArray]]): List Sparse vector
            search_params (models.SearchParams): Search parameters
        Returns:
            List[models.PointStruct]: List of points
        """
        prefetchs = []
        for dense_vector, sparse_vector in zip(dense_vectors, sparse_vectors):
            prefetchs.append(
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=limit,
                )
            )
            prefetchs.append(
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_vector.get("indices",[]),
                        values=sparse_vector.get("values",[])
                    ),
                    using="sparse",
                    limit=limit,
                )
            )
        return self.client.query_points(
            collection_name=collection_name,
            prefetch=prefetchs,
            query=models.FusionQuery(
                fusion=models.Fusion.RRF,
            ),
            search_params=search_params,
            with_payload=True,
            limit=limit
        ).points