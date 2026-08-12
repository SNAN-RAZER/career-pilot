from pathlib import Path

from app.knowledge.career_store import (
    CareerKnowledgeStore,
)
from app.models.evidence import (
    EvidenceType,
    SkillEvidence,
)

def test_stable_evidence_ids():

    evidence = SkillEvidence(
        skill="Qdrant",
        evidence_type=EvidenceType.PROJECT,
        source="CareerPilot AI Project",
        description=(
            "Built a RAG system using "
            "Qdrant as the vector database."
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
    )

    id_one = CareerKnowledgeStore._evidence_id(
        evidence
    )

    id_two = CareerKnowledgeStore._evidence_id(
        evidence
    )

    assert id_one == id_two