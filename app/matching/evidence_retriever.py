from app.knowledge.career_store import (
    CareerKnowledgeStore,
)


class EvidenceRetriever:

    def __init__(
        self,
        store: CareerKnowledgeStore | None = None,
    ):

        self.store = (
            store
            or CareerKnowledgeStore()
        )

    def retrieve(
        self,
        requirement: str,
        limit: int = 5,
    ) -> list[dict]:

        return self.store.search(
            query=requirement,
            limit=limit,
        )