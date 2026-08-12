from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.llm.lmstudio_client import LMStudioClient
from app.models.evidence import SkillEvidence
import hashlib

class CareerKnowledgeStore:

    COLLECTION_NAME = "career_evidence"

    def __init__(
        self,
        path: str = "data/qdrant",
        client: QdrantClient | None = None,
        llm_client: LMStudioClient | None = None,
    ):
        Path(path).mkdir(
            parents=True,
            exist_ok=True,
        )

        self.client = (
            client
            or QdrantClient(path=path)
        )

        self.llm_client = (
            llm_client
            or LMStudioClient()
        )

        self._ensure_collection()

    @staticmethod
    def _evidence_id(
        evidence: SkillEvidence,
    ) -> str:

        identity = "|".join(
            [
                evidence.skill.strip().lower(),
                evidence.evidence_type.value,
                evidence.source.strip().lower(),
                evidence.description.strip().lower(),
            ]
        )

        digest = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

        # Qdrant accepts integer IDs or UUIDs.
        # Use the first 32 hexadecimal characters
        # as a deterministic UUID.
        return (
            f"{digest[:8]}-"
            f"{digest[8:12]}-"
            f"{digest[12:16]}-"
            f"{digest[16:20]}-"
            f"{digest[20:32]}"
        )
    
    def _ensure_collection(self):

        collections = (
            self.client.get_collections()
        )

        existing = {
            collection.name
            for collection
            in collections.collections
        }

        if self.COLLECTION_NAME in existing:
            return

        sample_vector = (
            self.llm_client.embed(
                "career evidence"
            )
        )

        self.client.create_collection(
            collection_name=self.COLLECTION_NAME,
            vectors_config=VectorParams(
                size=len(sample_vector),
                distance=Distance.COSINE,
            ),
        )

    def add_evidence(
        self,
        evidence: list[SkillEvidence],
    ):

        points = []

        for item in evidence:

            text = self._evidence_text(
                item
            )

            vector = self.llm_client.embed(
                text
            )

            points.append(
                PointStruct(
                    id=self._evidence_id(item),
                    vector=vector,
                    payload={
                        "skill": item.skill,
                        "evidence_type": (
                            item.evidence_type.value
                        ),
                        "source": item.source,
                        "description": (
                            item.description
                        ),
                        "confidence": (
                            item.confidence
                        ),
                        "technologies": (
                            item.technologies
                        ),
                        "domains": (
                            item.domains
                        ),
                        "years": item.years,
                    },
                )
            )

        if points:

            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points,
            )

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:

        vector = self.llm_client.embed(
            query
        )

        results = self.client.query_points(
            collection_name=self.COLLECTION_NAME,
            query=vector,
            limit=limit,
            with_payload=True,
        )

        return [
            {
                "score": point.score,
                "payload": point.payload,
            }
            for point in results.points
        ]

    @staticmethod
    def _evidence_text(
        evidence: SkillEvidence,
    ) -> str:

        return (
            f"Skill: {evidence.skill}\n"
            f"Type: {evidence.evidence_type.value}\n"
            f"Source: {evidence.source}\n"
            f"Evidence: {evidence.description}\n"
            f"Technologies: "
            f"{', '.join(evidence.technologies)}\n"
            f"Domains: "
            f"{', '.join(evidence.domains)}"
        )

    def clear(self):

        collections = (
            self.client.get_collections()
        )

        existing = {
            collection.name
            for collection
            in collections.collections
        }

        if self.COLLECTION_NAME in existing:

            self.client.delete_collection(
                self.COLLECTION_NAME
            )

        self._ensure_collection()

    def rebuild(
        self,
        evidence: list[SkillEvidence],
    ):

        self.clear()

        self.add_evidence(
            evidence
        )