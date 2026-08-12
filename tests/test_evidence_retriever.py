from pathlib import Path

from app.knowledge.career_store import (
    CareerKnowledgeStore,
)
from app.matching.evidence_retriever import (
    EvidenceRetriever,
)
from app.models.evidence import (
    EvidenceType,
    SkillEvidence,
)


def test_retrieve_relevant_evidence(tmp_path):

    store = CareerKnowledgeStore(
        path=str(
            Path(tmp_path)
            / "qdrant"
        )
    )

    evidence = [
        SkillEvidence(
            skill="Qdrant",
            evidence_type=(
                EvidenceType.PROJECT
            ),
            source="AI/RAG Project",
            description=(
                "Built a RAG application "
                "using Qdrant vector database."
            ),
            confidence=0.9,
            technologies=[
                "Python",
                "Qdrant",
                "RAG",
            ],
            domains=[
                "Generative AI",
            ],
        ),

        SkillEvidence(
            skill="VxWorks",
            evidence_type=(
                EvidenceType.PROFESSIONAL
            ),
            source="Aerospace Company",
            description=(
                "Developed RTOS software "
                "using VxWorks."
            ),
            confidence=1.0,
            technologies=[
                "VxWorks",
                "RTOS",
            ],
            domains=[
                "Aerospace",
            ],
        ),
    ]

    store.add_evidence(
        evidence
    )

    retriever = EvidenceRetriever(
        store
    )

    results = retriever.retrieve(
        "vector database",
        limit=2,
    )

    assert len(results) == 2

    assert (
        results[0]["payload"]["skill"]
        == "Qdrant"
    )