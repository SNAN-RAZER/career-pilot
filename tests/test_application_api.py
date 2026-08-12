from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import (
    application_dependencies,
)


client = TestClient(app)


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