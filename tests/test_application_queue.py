from app.application.application_queue import (
    ApplicationQueue,
)
from app.models.application_recommendation import (
    ApplicationRecommendation,
)

from app.models.application_record import (
    ApplicationRecord,
)
from app.models.job import JobPosting
import pytest

def make_recommendation(
    job_id="100",
):

    job = JobPosting(
        job_id=job_id,
        title="AI Engineer",
        company="Test Company",
        location="Bangalore",
        description="Python RAG LLM",
        source="test",
    )

    return ApplicationRecommendation(
        job=job,
        match_score=90.0,
        eligibility_score=90.0,
        recommendation="APPLY",
        next_action="APPLY",
    )


def test_queue_adds_application():

    queue = ApplicationQueue()

    recommendation = make_recommendation()

    item = queue.add(
        recommendation
    )

    assert item.recommendation.job.job_id == "100"
    assert item.status == "PENDING"
    assert item.priority == "NORMAL"


def test_queue_returns_pending_items():

    queue = ApplicationQueue()

    queue.add(
        make_recommendation("100")
    )

    queue.add(
        make_recommendation("200")
    )

    pending = queue.get_pending()

    assert len(pending) == 2


def test_queue_prevents_duplicate_jobs():

    queue = ApplicationQueue()

    first = queue.add(
        make_recommendation("100")
    )

    second = queue.add(
        make_recommendation("100")
    )

    assert first is second
    assert len(queue.get_all()) == 1


def test_queue_gets_application_by_job_id():

    queue = ApplicationQueue()

    queue.add(
        make_recommendation("100")
    )

    result = queue.get_by_job_id("100")

    assert result is not None
    assert (
        result.recommendation.job.job_id
        == "100"
    )


def test_queue_returns_none_for_unknown_job():

    queue = ApplicationQueue()

    result = queue.get_by_job_id(
        "does-not-exist"
    )

    assert result is None


def test_queue_removes_application():

    queue = ApplicationQueue()

    queue.add(
        make_recommendation("100")
    )

    removed = queue.remove("100")

    assert removed is True
    assert queue.get_all() == []


def test_queue_remove_unknown_job():

    queue = ApplicationQueue()

    removed = queue.remove(
        "does-not-exist"
    )

    assert removed is False


def test_queue_allows_valid_status_transition():

    queue = ApplicationQueue()

    queue.add(
        make_recommendation("100")
    )

    item = queue.update_status(
        "100",
        "APPLIED",
    )

    assert item is not None
    assert item.status == "APPLIED"


def test_queue_rejects_invalid_status_transition():

    queue = ApplicationQueue()

    queue.add(
        make_recommendation("100")
    )

    # PENDING -> INTERVIEW is invalid.
    with pytest.raises(ValueError):

        queue.update_status(
            "100",
            "INTERVIEW",
        )


def test_queue_supports_application_lifecycle():

    queue = ApplicationQueue()

    queue.add(
        make_recommendation("100")
    )

    queue.update_status(
        "100",
        "APPLIED",
    )

    queue.update_status(
        "100",
        "INTERVIEW",
    )

    queue.update_status(
        "100",
        "OFFER",
    )

    item = queue.get_by_job_id("100")

    assert item is not None
    assert item.status == "OFFER"


def test_queue_returns_none_when_updating_unknown_job():

    queue = ApplicationQueue()

    result = queue.update_status(
        "does-not-exist",
        "APPLIED",
    )

    assert result is None



def test_queue_item_converts_to_application_record():

    queue = ApplicationQueue()

    item = queue.add(
        make_recommendation("100")
    )

    record = item.to_application_record()

    assert isinstance(
        record,
        ApplicationRecord,
    )

    assert record.job.job_id == "100"
    assert record.job.title == "AI Engineer"

    assert record.status == "PENDING"

    assert record.match_score == 90.0
    assert record.eligibility_score == 90.0

    assert record.recommendation == "APPLY"