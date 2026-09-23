from uuid import uuid4
import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import (
    application_dependencies,
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_workspace(tmp_path, monkeypatch):
    from app.api.dependencies import ApplicationDependencies
    from app.api import applications
    from app.models.candidate import CandidateProfile
    fresh = ApplicationDependencies(store_path=str(tmp_path / 'applications.json'))
    for name, value in vars(fresh).items():
        monkeypatch.setattr(application_dependencies, name, value)
    monkeypatch.setattr(applications, '_load_candidate', lambda: CandidateProfile(
        name='Test Candidate', skills=['Python', 'RAG', 'LLM', 'LangChain'],
        professional_summary='Python developer building RAG applications.'))


def test_get_applications():

    response = client.get(
        "/applications"
    )

    assert response.status_code == 200

    assert isinstance(
        response.json(),
        list,
    )


def test_get_unknown_application():

    response = client.get(
        "/applications/does-not-exist"
    )

    assert response.status_code == 404


def test_application_lifecycle():

    dependencies = (
        application_dependencies
    )

    from app.models.application_recommendation import (
        ApplicationRecommendation,
    )
    from app.models.job import JobPosting

    job_id = f"api-test-100-{uuid4().hex}"

    job = JobPosting(
        job_id=job_id,
        title="AI Engineer",
        company="API Test Company",
        location="Bangalore",
        description="Python RAG LLM",
        source="test",
    )

    recommendation = (
        ApplicationRecommendation(
            job=job,
            match_score=95.0,
            eligibility_score=90.0,
            recommendation="APPLY",
            missing_requirements=[],
            reasons=[
                "Strong API test match."
            ],
            next_action="APPLY",
        )
    )

    dependencies.workflow.enqueue(
        recommendation
    )

    # PENDING
    response = client.get(
        f"/applications/{job_id}"
    )

    assert response.status_code == 200

    assert (
        response.json()["status"]
        == "PENDING"
    )

    # PENDING -> APPLIED
    response = client.post(
        f"/applications/{job_id}/apply"
    )

    assert response.status_code == 200

    assert (
        response.json()["status"]
        == "APPLIED"
    )

    # APPLIED -> INTERVIEW
    response = client.post(
        f"/applications/{job_id}/interview"
    )

    assert response.status_code == 200

    assert (
        response.json()["status"]
        == "INTERVIEW"
    )

    # INTERVIEW -> OFFER
    response = client.post(
        f"/applications/{job_id}/offer"
    )

    assert response.status_code == 200

    assert (
        response.json()["status"]
        == "OFFER"
    )

    assert (
        response.json()["next_action"]
        == "NEGOTIATE"
    )


def test_invalid_application_transition():

    dependencies = (
        application_dependencies
    )

    from app.models.application_recommendation import (
        ApplicationRecommendation,
    )
    from app.models.job import JobPosting

    job_id = f"api-test-200-{uuid4().hex}"

    job = JobPosting(
        job_id=job_id,
        title="Python Engineer",
        company="API Test Company",
        location="Bangalore",
        description="Python",
        source="test",
    )

    recommendation = (
        ApplicationRecommendation(
            job=job,
            match_score=80.0,
            eligibility_score=80.0,
            recommendation="APPLY",
            missing_requirements=[],
            reasons=[],
            next_action="APPLY",
        )
    )

    dependencies.workflow.enqueue(
        recommendation
    )

    # PENDING -> OFFER is invalid.
    response = client.post(
        f"/applications/{job_id}/offer"
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Invalid application status transition: "
        "PENDING -> OFFER"
    )


def test_tailor_application_resume():

    dependencies = (
        application_dependencies
    )

    from app.models.application_recommendation import (
        ApplicationRecommendation,
    )
    from app.models.job import JobPosting

    job_id = f"api-test-tailor-{uuid4().hex}"

    job = JobPosting(
        job_id=job_id,
        title="AI Engineer",
        company="API Test Company",
        location="Bangalore",
        description="Python RAG LLM LangChain",
        source="test",
    )

    recommendation = (
        ApplicationRecommendation(
            job=job,
            match_score=90.0,
            eligibility_score=88.0,
            recommendation="APPLY",
            missing_requirements=[],
            reasons=["Strong match."],
            next_action="APPLY",
        )
    )

    dependencies.workflow.enqueue(
        recommendation
    )

    response = client.post(
        f"/applications/{job_id}/tailor"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ats_score"] is not None
    assert data["tailored_summary"]
    assert "Python" in data["tailored_skills"]
    assert data["resume_path"] is None


def test_download_resume_builds_docx_without_keeping_path():

    dependencies = (
        application_dependencies
    )

    from app.models.application_recommendation import (
        ApplicationRecommendation,
    )
    from app.models.job import JobPosting

    job_id = f"api-test-docx-{uuid4().hex}"

    job = JobPosting(
        job_id=job_id,
        title="AI Engineer",
        company="API Test Company",
        location="Bangalore",
        description="Python RAG LLM LangChain",
        source="test",
    )

    dependencies.workflow.enqueue(
        ApplicationRecommendation(
            job=job,
            match_score=90.0,
            eligibility_score=88.0,
            recommendation="APPLY",
            missing_requirements=[],
            reasons=["Strong match."],
            next_action="APPLY",
        )
    )

    response = client.get(
        f"/applications/{job_id}/resume-file"
    )

    assert response.status_code == 200
    assert (
        "officedocument.wordprocessingml.document"
        in response.headers["content-type"]
    )
    assert response.content[:2] == b"PK"

    stored = dependencies.service.get(job_id)

    assert stored.tailored_resume is not None
    assert stored.resume_path is None


def test_naukri_apply_blocked_without_resume():

    dependencies = (
        application_dependencies
    )

    from app.models.application_recommendation import (
        ApplicationRecommendation,
    )
    from app.models.job import JobPosting

    job_id = f"api-test-naukri-{uuid4().hex}"

    job = JobPosting(
        job_id=job_id,
        title="AI Engineer",
        company="Naukri Co",
        location="Bangalore",
        description="Python RAG LLM",
        source="naukri",
    )

    recommendation = (
        ApplicationRecommendation(
            job=job,
            match_score=90.0,
            eligibility_score=88.0,
            recommendation="APPLY",
            missing_requirements=[],
            reasons=["Strong match."],
            next_action="APPLY",
        )
    )

    dependencies.workflow.enqueue(
        recommendation
    )

    response = client.post(
        f"/applications/{job_id}/apply"
    )

    assert response.status_code == 400

    assert "Tailor a resume" in (
        response.json()["detail"]
    )
