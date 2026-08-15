from pathlib import Path

from app.models.candidate import CandidateProfile
from app.models.job import JobPosting
from app.models.tailored_resume import TailoredResume
from app.resume.temp_resume import (
    delete_temp_resume,
    write_temp_resume,
)


def test_temp_resume_is_deleted_after_use():

    path = write_temp_resume(
        CandidateProfile(name="Nayaab Ahmed N"),
        JobPosting(
            job_id="temp-1",
            title="Embedded Engineer",
            company="Acme",
            location="Bangalore",
            description="Python",
            source="test",
        ),
        TailoredResume(
            summary="Embedded software developer.",
            skills=["Python"],
        ),
    )

    assert Path(path).exists()
    assert path.endswith(".docx")

    delete_temp_resume(path)

    assert not Path(path).exists()
