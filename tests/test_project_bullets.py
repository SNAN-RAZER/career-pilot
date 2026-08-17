from app.models.candidate import CandidateProfile, Project
from app.resume.docx_exporter import ResumeExporter
from app.resume.project_bullets import project_bullets
from app.resume.resume_tailor import ResumeTailor


DESCRIPTION = (
    "Developed an agentic AI RAG system for Honda Aircraft "
    "requirements-to-test-case traceability. Implemented a "
    "multi-agent workflow using Python, LangChain, and Qdrant. "
    "Containerized RAG and AI services with Docker."
)


def test_project_description_becomes_sentence_bullets():

    bullets = project_bullets(DESCRIPTION)

    assert bullets[0].startswith("Developed an agentic AI")
    assert any(
        item.startswith("Implemented a multi-agent")
        for item in bullets
    )
    assert not any(
        item.lower().startswith("stack")
        for item in bullets
    )
    assert len(bullets) == 3


def test_tailor_keeps_project_name_and_bullets_apart():

    candidate = CandidateProfile(
        name="Nayaab Ahmed N",
        skills=["Python", "RAG"],
        projects=[
            Project(
                name="AI / RAG / KNOWLEDGE GRAPH PROJECT",
                description=DESCRIPTION,
                technologies=["Python", "LangChain", "Qdrant"],
                domains=["RAG"],
            )
        ],
    )
    from app.models.job import JobPosting

    resume = ResumeTailor().tailor(
        candidate,
        JobPosting(
            job_id="1",
            title="AI Engineer",
            company="Test",
            location="Bangalore",
            description="Python RAG LangChain",
            source="test",
        ),
    )

    highlight = resume.project_highlights[0]
    lines = highlight.splitlines()
    assert lines[0] == "AI / RAG / KNOWLEDGE GRAPH PROJECT"
    assert lines[1].startswith("Developed")
    assert "Stack (6)" not in highlight
    assert "Tools:" in highlight
    name, bullets = ResumeExporter._project_parts(highlight)
    assert name == "AI / RAG / KNOWLEDGE GRAPH PROJECT"
    assert len(bullets) >= 3
