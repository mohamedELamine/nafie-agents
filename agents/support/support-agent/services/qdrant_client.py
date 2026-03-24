import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from qdrant_client import QdrantClient as ExternalQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from ..logging_config import get_logger

logger = get_logger("services.qdrant_client")


class QdrantClient:
    """Client for Qdrant vector database."""

    def __init__(self, url: str):
        self.client = ExternalQdrantClient(url=url)
        self.embedding_provider = (
            os.environ.get("SUPPORT_EMBEDDING_PROVIDER")
            or ("openai" if os.environ.get("OPENAI_API_KEY") else "deterministic")
        ).lower()
        self.embedding_model = os.environ.get(
            "SUPPORT_EMBEDDING_MODEL", "text-embedding-3-small"
        )
        self.embedding_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.embedding_base_url = os.environ.get(
            "SUPPORT_EMBEDDING_BASE_URL", "https://api.openai.com/v1/embeddings"
        )
        self.collections = {
            "theme_docs": "theme_docs_collection",
            "general_faqs": "general_faqs_collection",
            "resolved_tickets": "resolved_tickets_collection",
        }
        self.vector_size = int(
            os.environ.get("SUPPORT_EMBEDDING_VECTOR_SIZE", "1536")
        )
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
                            "created_at": datetime.now(timezone.utc).isoformat(),
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

    def retrieve_knowledge(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve support knowledge in the shape expected by support nodes."""
        category_map = {
            "technical": ["theme_docs"],
            "license": ["theme_docs"],
            "billing": ["general_faqs", "resolved_tickets"],
            "general": ["general_faqs"],
            "resolved": ["resolved_tickets"],
            "theme": ["theme_docs"],
        }
        collections = category_map.get(category or "", ["theme_docs", "general_faqs"])

        results: List[Dict[str, Any]] = []
        for collection_key in collections:
            collection_name = self.collections[collection_key]
            for hit in self.search(query=query, collection_name=collection_name, limit=limit):
                metadata = hit.get("metadata", {})
                nested_metadata = metadata.get("metadata", {})
                source = nested_metadata.get("source") or metadata.get("source") or collection_name
                answer = (
                    metadata.get("answer")
                    or nested_metadata.get("answer")
                    or hit.get("text", "")
                )
                results.append(
                    {
                        "answer": answer,
                        "score": hit.get("score", 0.0),
                        "source": source,
                        "text": hit.get("text", ""),
                        "collection": collection_name,
                        "metadata": metadata,
                    }
                )

        results.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return results[:limit]

    def _encode_text(self, text: str) -> List[float]:
        """Encode text to embeddings using the configured provider."""
        if self.embedding_provider == "openai" and self.embedding_api_key:
            return self._encode_with_openai(text)
        if self.embedding_provider not in {"deterministic", "openai"}:
            logger.warning(
                "Unknown embedding provider %s; using deterministic fallback",
                self.embedding_provider,
            )
        return self._encode_deterministic(text)

    def _encode_with_openai(self, text: str) -> List[float]:
        """Encode text using an OpenAI-compatible embeddings endpoint."""
        try:
            response = httpx.post(
                self.embedding_base_url,
                headers={
                    "Authorization": f"Bearer {self.embedding_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": text,
                    "model": self.embedding_model,
                },
                timeout=20.0,
            )
            response.raise_for_status()
            payload = response.json()
            embeddings = payload["data"][0]["embedding"]
            if embeddings:
                self.vector_size = len(embeddings)
            return embeddings
        except Exception as exc:
            logger.warning(
                "OpenAI embedding request failed; using deterministic fallback: %s",
                exc,
            )
            return self._encode_deterministic(text)

    def _encode_deterministic(self, text: str) -> List[float]:
        """Encode text with a deterministic fallback for local development."""
        import hashlib

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


def get_qdrant_client(url: Optional[str] = None) -> QdrantClient:
    """Get Qdrant client instance."""
    return QdrantClient(url=url or os.environ.get("QDRANT_URL", "http://localhost:6333"))
