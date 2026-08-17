from uuid import uuid4

from app.models.candidate import CandidateProfile
from app.models.job import JobPosting
from app.models.job_ranking import JobRanking
from app.models.target_profile import TargetProfile
from app.pipeline.job_search_pipeline import (
    PipelineResult,
)
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import (
    application_dependencies,
)


client = TestClient(app)


class FakeJobSearchPipeline:

    def run(
        self,
        candidate: CandidateProfile,
        target_profile: TargetProfile,
        queries: list[str],
        location: str = "",
        pages: int = 1,
        experience: int = 2,
        job_age: int = 3,
    ) -> PipelineResult:

        from app.models.application_recommendation import (
            ApplicationRecommendation,
        )

        job = JobPosting(
            job_id=f"search-test-{uuid4().hex}",
            title="AI Engineer",
            company="Search Test Co",
            location=location or "Bangalore",
            description="Python RAG LLM",
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

        application_dependencies.workflow.enqueue(
            recommendation
        )

        return PipelineResult(
            collected_jobs=5,
            relevant_jobs=1,
            rejected_by_target=2,
            rejected_by_candidate_fit=2,
            rankings=[
                JobRanking(
                    rank=1,
                    job_id=job.job_id,
                    title=job.title,
                    company=job.company,
                    score=90.0,
                    recommendation="APPLY",
                    missing_requirements=[],
                    reasons=["Strong match."],
                )
            ],
            match_results=[],
            application_recommendations=[
                recommendation
            ],
            application_queue=(
                application_dependencies
                .queue.get_all()
            ),
        )


def test_search_jobs_endpoint():

    original = (
        application_dependencies
        ._job_search_pipeline
    )

    application_dependencies._job_search_pipeline = (
        FakeJobSearchPipeline()
    )

    try:

        response = client.post(
            "/jobs/search",
            json={
                "queries": [
                    "AI Engineer",
                ],
                "location": "Bangalore",
                "pages": 1,
                "experience": 2,
                "job_age": 3,
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["collected_jobs"] == 5
        assert data["relevant_jobs"] == 1
        assert data["applications_queued"] == 1
        assert len(data["rankings"]) == 1
        assert (
            data["rankings"][0]["title"]
            == "AI Engineer"
        )
        job_id = data["rankings"][0]["job_id"]
        assert job_id.startswith("search-test-")

        app_response = client.get(
            f"/applications/{job_id}"
        )

        assert app_response.status_code == 200

        assert (
            app_response.json()["status"]
            == "PENDING"
        )

    finally:

        application_dependencies._job_search_pipeline = (
            original
        )


def test_search_jobs_returns_real_error_detail():

    original = (
        application_dependencies
        ._job_search_pipeline
    )

    class BoomPipeline:
        def run(self, **kwargs):
            raise RuntimeError(
                "Could not extract job requirements."
            )

    application_dependencies._job_search_pipeline = (
        BoomPipeline()
    )

    try:
        response = client.post(
            "/jobs/search",
            json={
                "queries": ["AI Engineer"],
                "location": "Bangalore",
            },
        )
        assert response.status_code == 502
        assert "job-description analyzer" in (
            response.json()["detail"].lower()
        )
    finally:
        application_dependencies._job_search_pipeline = (
            original
        )


def test_search_jobs_requires_queries():

    response = client.post(
        "/jobs/search",
        json={
            "queries": [],
            "location": "Bangalore",
        },
    )

    assert response.status_code == 422
