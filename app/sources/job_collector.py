from app.models.job import JobPosting


class JobCollector:

    def __init__(self, source):
        self.source = source

    def collect(
        self,
        queries: list[str],
        location: str = "",
        pages: int = 1,
        experience: int = 2,
        job_age: int = 3,
    ) -> list[JobPosting]:
        jobs_by_id: dict[
            str,
            JobPosting,
        ] = {}

        for query in queries:

            for page in range(
                1,
                pages + 1,
            ):

                jobs = self.source.search(
                    keyword=query,
                    location=location,
                    page=page,
                    experience=experience,
                    job_age=job_age,
                )

                for job in jobs:

                    if job.job_id:
                        jobs_by_id[
                            job.job_id
                        ] = job

        return list(
            jobs_by_id.values()
        )