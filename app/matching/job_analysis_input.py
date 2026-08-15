from app.models.job import JobPosting
from app.matching.job_text import strip_job_html


def build_job_analysis_input(
    job: JobPosting,
) -> str:

    description = strip_job_html(
        job.description or ""
    )[:8000]

    return f"""
JOB TITLE:
{job.title}

COMPANY:
{job.company}

LOCATION:
{job.location or "Not specified"}

POSTED DATE:
{job.posted_date or "Not specified"}

SALARY:
{job.salary or "Not disclosed"}

EMPLOYMENT TYPE:
{job.employment_type or "Not specified"}

JOB DESCRIPTION:
{description}
""".strip()