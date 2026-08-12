import pytest

from app.models.application_record import (
    ApplicationRecord,
)
from app.models.job import JobPosting
from app.services.application_notes import (
    ApplicationNotes,
)


def make_application():

    return ApplicationRecord(
        job=JobPosting(
            job_id="1",
            title="AI Engineer",
            company="Test Company",
            location="Bangalore",
            description="Python RAG",
            source="test",
        ),
        match_score=90,
        eligibility_score=90,
        recommendation="APPLY",
        next_action="APPLY",
    )


def test_add_note():

    application = make_application()

    ApplicationNotes.add(
        application,
        "Recruiter contacted me.",
    )

    assert (
        application.notes
        == ["Recruiter contacted me."]
    )


def test_add_multiple_notes():

    application = make_application()

    ApplicationNotes.add(
        application,
        "Applied through referral.",
    )

    ApplicationNotes.add(
        application,
        "Waiting for recruiter response.",
    )

    assert len(
        application.notes
    ) == 2


def test_empty_note_is_rejected():

    application = make_application()

    with pytest.raises(ValueError):

        ApplicationNotes.add(
            application,
            "   ",
        )