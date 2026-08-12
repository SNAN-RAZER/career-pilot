from app.matching.evidence_judge import EvidenceJudge
from app.models.evidence import (
    EvidenceType,
    SkillEvidence,
)


def test_professional_vxworks_evidence():

    evidence = SkillEvidence(
        skill="VxWorks",

        evidence_type=EvidenceType.PROFESSIONAL,

        source="Aeronautical Development Agency",

        description=(
            "Developed RTOS drivers and embedded "
            "software using VxWorks."
        ),

        confidence=1.0,

        technologies=[
            "VxWorks",
            "RTOS",
            "Embedded C"
        ],

        domains=[
            "Aerospace",
            "Embedded Systems"
        ]
    )

    judge = EvidenceJudge()

    result = judge.judge(
        "VxWorks experience",
        evidence
    )

    print("\nVxWorks judgment:")
    print(result.model_dump())

    assert result.supported is True
    assert result.confidence > 0.7


def test_tensorflow_not_supported_by_rag():

    evidence = SkillEvidence(
        skill="RAG",

        evidence_type=EvidenceType.PROJECT,

        source="AI/RAG Engineering Project",

        description=(
            "Built a local RAG application using "
            "Python, LangChain, Qdrant and Ollama."
        ),

        confidence=0.8,

        technologies=[
            "Python",
            "LangChain",
            "Qdrant",
            "Ollama"
        ],

        domains=[
            "Generative AI",
            "RAG"
        ]
    )

    judge = EvidenceJudge()

    result = judge.judge(
        "TensorFlow experience",
        evidence
    )

    print("\nTensorFlow judgment:")
    print(result.model_dump())

    assert result.supported is False