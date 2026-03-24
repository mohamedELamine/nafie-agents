from typing import list


class ThemeDocRetriever:
    def __init__(self, qdrant_client: QdrantClient):
        self.qdrant = qdrant_client

    def retrieve_theme(self, query: str) -> list[dict]:
        results = self.qdrant.retrieve_knowledge(query=query, category="theme", limit=3)
        return results


class GeneralFaqsRetriever:
    def __init__(self, qdrant_client: QdrantClient):
        self.qdrant = qdrant_client

    def retrieve_faq(self, query: str) -> list[dict]:
        results = self.qdrant.retrieve_knowledge(
            query=query, category="general", limit=3
        )
        return results


class ResolvedTicketsRetriever:
    def __init__(self, qdrant_client: QdrantClient):
        self.qdrant = qdrant_client

    def retrieve_resolved(self, query: str) -> list[dict]:
        results = self.qdrant.retrieve_knowledge(
            query=query, category="resolved", limit=3
        )
        return results
