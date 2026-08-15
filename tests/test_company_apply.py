from app.application.company_apply import (
    extract_company_apply_url,
    naukri_listing_url,
)
from app.models.job import JobPosting


def test_extracts_company_host_not_naukri():

    details = {
        "job": {
            "responseManager": "companyUrl",
            "companyUrl": (
                "https://careers.accenture.com/apply/123"
            ),
            "jobUrl": (
                "https://www.naukri.com/job-listings-1"
            ),
        }
    }

    url = extract_company_apply_url(details)

    assert "accenture.com" in url


def test_falls_back_to_naukri_listing():

    job = JobPosting(
        job_id="1",
        title="AI Engineer",
        company="Accenture",
        location="Bangalore",
        description="Python",
        source="naukri",
        url="/job-listings-ai-engineer-1",
    )

    url = extract_company_apply_url(
        {"job": {}},
        job,
    )

    assert url == (
        "https://www.naukri.com"
        "/job-listings-ai-engineer-1"
    )


def test_naukri_listing_url_keeps_absolute():

    job = JobPosting(
        job_id="1",
        title="AI Engineer",
        company="Accenture",
        location="Bangalore",
        description="Python",
        source="naukri",
        url="https://www.naukri.com/job-listings-1",
    )

    assert naukri_listing_url(job) == job.url


def test_ignores_naukri_search_urls():

    job = JobPosting(
        job_id="abc123",
        title="AI Engineer",
        company="Accenture",
        location="Bangalore",
        description="Python",
        source="naukri",
        url="https://www.naukri.com/mnj/search?q=ai",
    )

    url = extract_company_apply_url(
        {
            "job": {
                "jobUrl": (
                    "https://www.naukri.com/jobsearch/jobs"
                )
            }
        },
        job,
    )

    assert "search" not in url.lower()
    assert "abc123" in url
