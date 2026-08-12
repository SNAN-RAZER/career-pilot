from app.models.application_queue_item import (
    ApplicationQueueItem,
)
from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.models.job import JobPosting


def make_recommendation():

    job = JobPosting(
        job_id="123",
        title="AI Engineer",
        company="AI Company",
        location="Bangalore",
        description="Python, RAG and LLM",
        source="naukri",
    )

    return ApplicationRecommendation(
        job=job,
        match_score=90.0,
        eligibility_score=90.0,
        recommendation="APPLY",
        missing_requirements=[],
        reasons=[
            "Strong candidate alignment."
        ],
        next_action="APPLY",
    )


def test_queue_item_preserves_recommendation():

    recommendation = make_recommendation()

    item = ApplicationQueueItem(
        recommendation=recommendation,
    )

    assert (
        item.recommendation
        is recommendation
    )

    assert item.recommendation.job.title == (
        "AI Engineer"
    )


def test_queue_item_defaults_to_pending():

    item = ApplicationQueueItem(
        recommendation=make_recommendation(),
    )

    assert item.status == "PENDING"
    assert item.priority == "NORMAL"
    assert item.notes == []


def test_queue_item_can_track_application_progress():

    item = ApplicationQueueItem(
        recommendation=make_recommendation(),
        status="IN_PROGRESS",
        priority="HIGH",
        notes=[
            "Tailor resume before applying."
        ],
    )

    assert item.status == "IN_PROGRESS"
    assert item.priority == "HIGH"

    assert (
        "Tailor resume before applying."
        in item.notes
    )