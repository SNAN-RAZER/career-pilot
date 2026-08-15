from urllib.parse import urlparse

from pydantic import BaseModel


class CompanyApplyPackage(BaseModel):

    job_id: str
    title: str
    company: str
    apply_url: str
    naukri_url: str | None = None
    resume_path: str = ""
    candidate_name: str
    candidate_email: str | None = None
    candidate_phone: str | None = None
    mode: str = "COMPANY_WEBSITE"
    message: str


def naukri_listing_url(job) -> str | None:

    url = getattr(job, "url", None)

    if not url:
        return None

    if url.startswith("http"):
        return url

    return "https://www.naukri.com" + url


def extract_company_apply_url(
    details: dict | None,
    job=None,
) -> str | None:

    urls = []

    if isinstance(details, dict):
        urls.extend(_collect_http_urls(details))

    listing = naukri_listing_url(job) if job is not None else None

    company_urls = [
        url
        for url in urls
        if _is_company_host(url) and not _is_search_url(url)
    ]

    if company_urls:
        return company_urls[0]

    if listing and not _is_search_url(listing):
        return listing

    if job is not None:
        job_id = str(getattr(job, "job_id", "") or "")

        if job_id:
            return (
                "https://www.naukri.com/job-listings-"
                + job_id
            )

    usable = [
        url for url in urls if not _is_search_url(url)
    ]

    return usable[0] if usable else None


def _is_search_url(url: str) -> bool:

    lower = (url or "").lower()
    path = urlparse(url).path.lower() if url else ""

    if any(
        hint in lower
        for hint in (
            "jobsearch",
            "/mnj/search",
            "search?",
            "suggestor",
        )
    ):
        return True

    if "naukri.com" in lower and (
        path in {"", "/", "/mnjuser/homepage"}
        or "jobs-in-" in path
        or path.endswith("/search")
    ):
        return True

    return False


def _is_company_host(url: str) -> bool:

    host = urlparse(url).netloc.lower()

    return bool(host) and "naukri.com" not in host


def _collect_http_urls(value, found=None) -> list[str]:

    if found is None:
        found = []

    if isinstance(value, str):
        if value.startswith("http") and value not in found:
            found.append(value)
        return found

    if isinstance(value, dict):
        preferred_keys = {
            "companyurl",
            "applyurl",
            "applyredirecturl",
            "redirectionurl",
            "companyapplyurl",
            "externalapplyurl",
            "applylink",
        }

        for key, item in value.items():
            if str(key).lower() in preferred_keys:
                _collect_http_urls(item, found)
        for item in value.values():
            _collect_http_urls(item, found)

        return found

    if isinstance(value, list):
        for item in value:
            _collect_http_urls(item, found)

    return found
