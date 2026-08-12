from typing import Any

from app.models.job import JobPosting


class NaukriAdapter:

    def __init__(self, naukri_job_client):
        self.client = naukri_job_client

    def search(
        self,
        keyword: str,
        location: str = "",
        page: int = 1,
        job_age: int = 3,
        experience: int = 2,
        results_per_page: int = 20,
    ) -> list[JobPosting]:

        jobs = self.client.search_jobs(
            keyword=keyword,
            location=location,
            page=page,
            job_age=job_age,
            experience=experience,
            results_per_page=results_per_page,
        )

        return [
            self._convert_job(job)
            for job in jobs
        ]

    def recommended(self) -> list[JobPosting]:

        jobs = self.client.get_recommended_jobs()

        return [
            self._convert_job(job)
            for job in jobs
        ]

    @staticmethod
    def _normalize_salary(
        salary: Any,
    ) -> str | None:

        if salary is None:
            return None

        if isinstance(salary, str):
            return salary

        if isinstance(salary, dict):

            minimum = salary.get(
                "minimumSalary"
            )

            maximum = salary.get(
                "maximumSalary"
            )

            currency = salary.get(
                "currency",
                "INR",
            )

            if minimum and maximum:
                return (
                    f"{currency} "
                    f"{minimum} - {maximum}"
                )

            if minimum:
                return (
                    f"{currency} "
                    f"{minimum}+"
                )

            if maximum:
                return (
                    f"Up to {currency} "
                    f"{maximum}"
                )

            return "Not disclosed"

        return str(salary)

    @staticmethod
    def _convert_job(job) -> JobPosting:

        return JobPosting(
            job_id=str(job.job_id),

            title=job.title,

            company=job.company,

            location=job.location,

            url=job.apply_link,

            description=job.description,

            source="naukri",

            posted_date=job.posted_date,

            salary=NaukriAdapter._normalize_salary(
                job.salary
            ),

            raw_data={
                "experience": job.experience,
                "tags": job.tags,
                "salary_raw": job.salary,
            },
        )