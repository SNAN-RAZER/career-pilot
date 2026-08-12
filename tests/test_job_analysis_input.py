from app.models.job import JobPosting

from app.matching.job_analysis_input import (
    build_job_analysis_input,
)


def make_job():
    return JobPosting(
        job_id="123",
        title="Generative AI Engineer",
        company="AI Company",
        location="Bangalore",
        description=(
            "Build LLM applications using Python, "
            "RAG, LangChain and Qdrant."
        ),
        source="naukri",
        posted_date="1 Day Ago",
        salary="10-20 LPA",
        employment_type="Full-time",
    )


def test_job_analysis_input_contains_job_context():

    job = make_job()

    text = build_job_analysis_input(job)

    assert "Generative AI Engineer" in text
    assert "AI Company" in text
    assert "Bangalore" in text
    assert "1 Day Ago" in text
    assert "10-20 LPA" in text
    assert "Full-time" in text


def test_job_analysis_input_contains_description():

    job = make_job()

    text = build_job_analysis_input(job)

    assert "Python" in text
    assert "RAG" in text
    assert "LangChain" in text
    assert "Qdrant" in text


def test_job_analysis_input_handles_missing_optional_fields():

    job = JobPosting(
        job_id="456",
        title="AI Engineer",
        company="AI Company",
        description="Build AI applications.",
        source="test",
    )

    text = build_job_analysis_input(job)

    assert "AI Engineer" in text
    assert "AI Company" in text
    assert "Build AI applications." in text
    assert "Not specified" in text
    assert "Not disclosed" in text