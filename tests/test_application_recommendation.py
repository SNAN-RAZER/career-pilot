from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.models.job import JobPosting


def make_job():
    return JobPosting(
        job_id="123",
        title="AI Engineer",
        company="AI Company",
        location="Bangalore",
        description="Python, RAG and LLM",
        source="naukri",
    )


def test_application_recommendation_preserves_job():

    job = make_job()

    result = ApplicationRecommendation(
        job=job,
        match_score=94.5,
        eligibility_score=94.5,
        recommendation="APPLY",
        missing_requirements=[],
        reasons=[
            "Strong candidate alignment."
        ],
        next_action="APPLY",
    )

    assert result.job is job
    assert result.job.title == "AI Engineer"
    assert result.job.company == "AI Company"


def test_application_recommendation_contains_decision():

    result = ApplicationRecommendation(
        job=make_job(),
        match_score=66.5,
        eligibility_score=56.5,
        recommendation="REVIEW",
        missing_requirements=[
            "REST APIs"
        ],
        reasons=[
            "Some professional experience aligns."
        ],
        next_action="REVIEW_MISSING_REQUIREMENTS",
    )

    assert result.match_score == 66.5
    assert result.eligibility_score == 56.5
    assert result.recommendation == "REVIEW"
    assert "REST APIs" in result.missing_requirements


def test_application_recommendation_defaults_lists():

    result = ApplicationRecommendation(
        job=make_job(),
        match_score=90,
        eligibility_score=90,
        recommendation="APPLY",
        next_action="APPLY",
    )

    assert result.missing_requirements == []
    assert result.reasons == []