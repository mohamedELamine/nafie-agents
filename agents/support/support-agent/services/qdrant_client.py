import logging
from typing import Any, Dict, List, Optional

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from ..logging_config import get_logger

logger = get_logger("services.qdrant_client")


class QdrantClient:
    """Client for Qdrant vector database."""

    def __init__(self, url: str):
        self.client = QdrantClient(url=url)
        self.collections = {
            "theme_docs": "theme_docs_collection",
            "general_faqs": "general_faqs_collection",
            "resolved_tickets": "resolved_tickets_collection",
        }
        self.vector_size = 1536
        self._create_collections()

    def _create_collections(self) -> None:
        """Create collections if they don't exist."""
        try:
            collection_names = self.collections.values()

            for name in collection_names:
                if not self.client.collection_exists(name):
                    self.client.create_collection(
                        collection_name=name,
                        vectors_config={
                            "size": self.vector_size,
                            "distance": "Cosine",
                        },
                    )
                    logger.info(f"Created collection: {name}")

                logger.info(f"Collection {name} exists")

        except Exception as e:
            logger.error(f"Error creating collections: {e}")

    def search(
        self,
        query: str,
        collection_name: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents in a collection."""
        try:
            # Convert query to embedding (using a simple placeholder for now)
            # In production, you'd use a proper embedding model
            embeddings = self._encode_text(query)

            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=embeddings,
                limit=limit,
                query_filter=self._build_filter(filters),
                with_payload=True,
            )

            return [
                {
                    "id": hit.id,
                    "text": hit.payload.get("text", "") if hit.payload else "",
                    "score": hit.score,
                    "metadata": hit.payload or {},
                }
                for hit in search_result
            ]
        except Exception as e:
            logger.error(f"Error searching collection {collection_name}: {e}")
            return []

    def upsert_document(
        self,
        collection_name: str,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Upsert a document into a collection."""
        try:
            embeddings = self._encode_text(text)

            self.client.upsert(
                collection_name=collection_name,
                points=[
                    {
                        "id": doc_id,
                        "vector": embeddings,
                        "payload": {
                            "text": text,
                            "metadata": metadata or {},
                            "created_at": datetime.utcnow().isoformat(),
                        },
                    }
                ],
            )

            logger.info(f"Upserted document {doc_id} into {collection_name}")
        except Exception as e:
            logger.error(f"Error upserting document: {e}")

    def search_parallel(
        self,
        queries: List[str],
        collections: List[str],
        limit: int = 3,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search multiple collections in parallel with multiple queries."""
        results = {}

        for collection in collections:
            collection_results = []

            for query in queries:
                collection_results.extend(
                    self.search(query, collection, limit=limit // len(queries))
                )

            results[collection] = collection_results[:limit]

        return results

    def _encode_text(self, text: str) -> List[float]:
        """Encode text to embeddings (placeholder)."""
        # Placeholder for actual embedding
        # In production, use a proper embedding model like OpenAI or SentenceTransformers
        import hashlib

        # Simple hash-based embedding for demonstration
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [hash_val % 10000 / 10000.0] * self.vector_size

    def _build_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
        """Build Qdrant filter from dict."""
        if not filters:
            return None

        conditions = []
        for key, value in filters.items():
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
            )

        if conditions:
            return Filter(must=conditions)
        return None


def get_qdrant_client(url: str) -> QdrantClient:
    """Get Qdrant client instance."""
    return QdrantClient(url=url)
