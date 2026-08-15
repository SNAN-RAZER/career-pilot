from app.models.candidate import CandidateProfile
from app.profile.evidence_builder import EvidenceBuilder
from app.models.evidence import EvidenceType


def test_evidence_builder():

    candidate = CandidateProfile(
        name="Test Candidate",

        total_experience_years=4,

        skills=[
            "Python",
            "C",
            "VxWorks",
            "RAG",
        ],

        experiences=[
            {
                "company": "Example Aerospace",
                "role": "Embedded Engineer",
                "technologies": [
                    "C",
                    "VxWorks",
                ],
                "description": [
                    "Developed embedded software."
                ],
                "domains": [
                    "Aerospace",
                    "Embedded Systems",
                ],
            }
        ],

        projects=[
            {
                "name": "AI RAG Project",
                "description": (
                    "Built a local RAG application."
                ),
                "technologies": [
                    "Python",
                    "RAG",
                ],
                "domains": [
                    "Generative AI",
                ],
            }
        ],
    )

    builder = EvidenceBuilder()

    evidence = builder.build(candidate)

    professional = [
        item
        for item in evidence
        if item.evidence_type
        == EvidenceType.PROFESSIONAL
    ]

    project = [
        item
        for item in evidence
        if item.evidence_type
        == EvidenceType.PROJECT
    ]

    assert len(professional) == 2
    assert len(project) == 2

    assert any(
        item.skill == "VxWorks"
        for item in professional
    )

    assert any(
        item.skill == "RAG"
        for item in project
    )
    assert any(
        item.skill == "Python"
        and item.evidence_type == EvidenceType.DECLARED
        for item in evidence
    )