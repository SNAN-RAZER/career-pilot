from app.models.application_record import ApplicationRecord
from app.models.job import JobPosting
from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.store.application_store import ApplicationStore


def make_job(
    job_id: str,
    title: str,
) -> JobPosting:

    return JobPosting(
        job_id=job_id,
        title=title,
        company="Test Company",
        location="Bangalore",
        description="Python RAG LLM",
        source="test",
    )


def make_recommendation(
    job_id: str,
    title: str,
    recommendation: str,
) -> ApplicationRecommendation:

    return ApplicationRecommendation(
        job=make_job(
            job_id,
            title,
        ),
        match_score=90.0,
        eligibility_score=90.0,
        recommendation=recommendation,
        missing_requirements=[],
        reasons=["Good candidate alignment."],
        next_action=recommendation,
    )


def persist_recommendation(
    store: ApplicationStore,
    recommendation: ApplicationRecommendation,
):
    if recommendation.recommendation == "REJECT":
        return

    record = ApplicationRecord(
        job=recommendation.job,
        status="PENDING",
        match_score=recommendation.match_score,
        eligibility_score=recommendation.eligibility_score,
        recommendation=recommendation.recommendation,
        missing_requirements=(
            recommendation.missing_requirements
        ),
        reasons=recommendation.reasons,
    )

    store.save(record)


def test_apply_recommendation_is_persisted(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    recommendation = make_recommendation(
        "1",
        "AI Engineer",
        "APPLY",
    )

    persist_recommendation(
        store,
        recommendation,
    )

    application = store.get("1")

    assert application is not None
    assert application.status == "PENDING"
    assert application.recommendation == "APPLY"
    assert application.job.title == "AI Engineer"


def test_review_recommendation_is_persisted(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    recommendation = make_recommendation(
        "2",
        "RAG Engineer",
        "REVIEW",
    )

    persist_recommendation(
        store,
        recommendation,
    )

    application = store.get("2")

    assert application is not None
    assert application.status == "PENDING"
    assert application.recommendation == "REVIEW"


def test_rejected_recommendation_is_not_persisted(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    recommendation = make_recommendation(
        "3",
        "Java Developer",
        "REJECT",
    )

    persist_recommendation(
        store,
        recommendation,
    )

    assert store.get("3") is None
    assert store.load() == []


def test_repeated_persistence_does_not_duplicate_job(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    recommendation = make_recommendation(
        "4",
        "AI Engineer",
        "APPLY",
    )

    persist_recommendation(
        store,
        recommendation,
    )

    persist_recommendation(
        store,
        recommendation,
    )

    applications = store.load()

    assert len(applications) == 1
    assert applications[0].job.job_id == "4"