from app.models.job import JobPosting
from app.models.job_match_result import JobMatchResult


def make_job():

    return JobPosting(
        job_id="12345",
        title="Agentic AI Engineer",
        company="Infosys",
        location="Bengaluru",
        url="https://example.com/job/12345",
        description=(
            "Build LLM and RAG applications."
        ),
        source="naukri",
        posted_date="1 Day Ago",
        salary="Not disclosed",
        employment_type="Full-time",
    )


def test_job_match_result_preserves_job_information():

    job = make_job()

    result = JobMatchResult(
        job=job,
        score=91.5,
        recommendation="APPLY",
        missing_requirements=[
            "REST APIs",
        ],
        reasons=[
            "Strong AI/RAG alignment.",
            "Strong project evidence.",
        ],
    )

    assert result.job.job_id == "12345"
    assert result.job.title == "Agentic AI Engineer"
    assert result.job.company == "Infosys"
    assert result.job.location == "Bengaluru"
    assert result.job.url == "https://example.com/job/12345"


def test_job_match_result_contains_match_information():

    job = make_job()

    result = JobMatchResult(
        job=job,
        score=91.5,
        recommendation="APPLY",
        missing_requirements=[],
        reasons=[
            "Strong AI/RAG alignment.",
        ],
    )

    assert result.score == 91.5
    assert result.recommendation == "APPLY"
    assert result.missing_requirements == []
    assert "Strong AI/RAG alignment." in result.reasons


def test_job_match_result_defaults_lists():

    job = make_job()

    result = JobMatchResult(
        job=job,
        score=75.0,
        recommendation="REVIEW",
    )

    assert result.missing_requirements == []
    assert result.reasons == []