from os import close
from pathlib import Path
from tempfile import mkstemp

from app.models.candidate import CandidateProfile
from app.models.job import JobPosting
from app.models.tailored_resume import TailoredResume
from app.resume.docx_exporter import ResumeExporter


def write_temp_resume(
    candidate: CandidateProfile,
    job: JobPosting,
    resume: TailoredResume,
) -> str:

    handle, name = mkstemp(
        prefix="career-pilot-",
        suffix=".docx",
    )
    close(handle)
    path = Path(name)
    ResumeExporter(output_dir=str(path.parent)).export(
        candidate,
        job,
        resume,
        dest=path,
    )
    return str(path)


def delete_temp_resume(path: str | None) -> None:

    if not path:
        return

    file_path = Path(path)

    if file_path.exists():
        file_path.unlink()
