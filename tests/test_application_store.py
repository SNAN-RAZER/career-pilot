from app.models.application_record import ApplicationRecord
from app.models.job import JobPosting
from app.store.application_store import ApplicationStore
import pytest

from app.services.application_state_machine import (
    InvalidApplicationTransition,
)

def make_application(
    job_id="123",
    title="AI Engineer",
):
    job = JobPosting(
        job_id=job_id,
        title=title,
        company="Test Company",
        location="Bangalore",
        description="Python RAG LLM",
        source="test",
    )

    return ApplicationRecord(
        job=job,
        match_score=92.5,
        eligibility_score=92.5,
        recommendation="APPLY",
        missing_requirements=[],
        reasons=[
            "Strong candidate alignment."
        ],
    )


def test_store_saves_and_loads_application(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    application = make_application()

    store.save(application)

    applications = store.load()

    assert len(applications) == 1

    assert (
        applications[0].job.job_id
        == "123"
    )

    assert (
        applications[0].job.title
        == "AI Engineer"
    )

    assert (
        applications[0].match_score
        == 92.5
    )


def test_store_gets_application_by_job_id(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    store.save(
        make_application(
            job_id="123"
        )
    )

    result = store.get("123")

    assert result is not None

    assert (
        result.job.job_id
        == "123"
    )


def test_store_returns_none_for_unknown_job(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    result = store.get("does-not-exist")

    assert result is None


def test_store_updates_application_status(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    store.save(
        make_application(
            job_id="123"
        )
    )

    updated = store.update_status(
        "123",
        "APPLIED",
    )

    assert updated is not None

    assert (
        updated.status
        == "APPLIED"
    )

    stored = store.get("123")

    assert stored is not None

    assert (
        stored.status
        == "APPLIED"
    )


def test_store_updates_existing_application(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    store.save(
        make_application(
            job_id="123",
            title="AI Engineer",
        )
    )

    store.save(
        make_application(
            job_id="123",
            title="Senior AI Engineer",
        )
    )

    applications = store.load()

    assert len(applications) == 1

    assert (
        applications[0].job.title
        == "Senior AI Engineer"
    )

def test_store_allows_valid_status_transition(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    store.save(
        make_application(
            job_id="100"
        )
    )

    result = store.update_status(
        "100",
        "APPLIED",
    )

    assert result is not None
    assert result.status == "APPLIED"


def test_store_rejects_invalid_status_transition(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    store.save(
        make_application(
            job_id="101"
        )
    )

    with pytest.raises(
        InvalidApplicationTransition
    ):

        store.update_status(
            "101",
            "OFFER",
        )


def test_store_supports_full_application_lifecycle(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    store.save(
        make_application(
            job_id="102"
        )
    )

    store.update_status(
        "102",
        "APPLIED",
    )

    store.update_status(
        "102",
        "INTERVIEW",
    )

    store.update_status(
        "102",
        "OFFER",
    )

    application = store.get("102")

    assert application is not None

    assert (
        application.status
        == "OFFER"
    )
def test_store_adds_and_persists_note(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    store.save(
        make_application(
            job_id="200"
        )
    )

    result = store.add_note(
        "200",
        "Recruiter contacted me.",
    )

    assert result is not None

    assert result.notes == [
        "Recruiter contacted me."
    ]

    stored = store.get("200")

    assert stored is not None

    assert stored.notes == [
        "Recruiter contacted me."
    ]


def test_store_rejects_empty_note(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    store.save(
        make_application(
            job_id="201"
        )
    )

    with pytest.raises(ValueError):

        store.add_note(
            "201",
            "   ",
        )


def test_store_add_note_unknown_job(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    result = store.add_note(
        "does-not-exist",
        "Some note",
    )

    assert result is None