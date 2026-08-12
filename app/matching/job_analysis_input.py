from app.models.job import JobPosting


def build_job_analysis_input(
    job: JobPosting,
) -> str:

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
{job.description}
""".strip()