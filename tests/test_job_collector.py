from app.models.job import JobPosting
from app.sources.job_collector import (
    JobCollector,
)


class FakeSource:

    def search(
        self,
        keyword,
        location,
        page,
        experience,
        job_age,
    ):

        if keyword == "AI Engineer":

            return [
                JobPosting(
                    job_id="1",
                    title="AI Engineer",
                    company="Company A",
                    description="Python AI",
                    source="test",
                ),
                JobPosting(
                    job_id="2",
                    title="RAG Engineer",
                    company="Company B",
                    description="RAG",
                    source="test",
                ),
            ]

        return [
            JobPosting(
                job_id="2",
                title="RAG Engineer",
                company="Company B",
                description="RAG",
                source="test",
            ),
            JobPosting(
                job_id="3",
                title="LLM Engineer",
                company="Company C",
                description="LLM",
                source="test",
            ),
        ]


def test_job_collector_deduplicates():

    collector = JobCollector(
        FakeSource()
    )

    jobs = collector.collect(
        queries=[
            "AI Engineer",
            "RAG Engineer",
        ],
    )

    assert len(jobs) == 3

    ids = {
        job.job_id
        for job in jobs
    }

    assert ids == {
        "1",
        "2",
        "3",
    }