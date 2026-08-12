from types import SimpleNamespace

from app.sources.naukri_adapter import (
    NaukriAdapter,
)


class FakeNaukriClient:

    def search_jobs(
        self,
        **kwargs,
    ):

        return [
            SimpleNamespace(
                job_id="123",
                title="Generative AI Engineer",
                company="Test AI",
                location="Bangalore",
                experience="3-5 years",
                salary="10-20 LPA",
                posted_date="1 day ago",
                apply_link=(
                    "https://www.naukri.com/"
                    "job-listings-123"
                ),
                description=(
                    "Python, LLM, RAG, "
                    "Qdrant and LangChain."
                ),
                tags=[
                    "Python",
                    "LLM",
                    "RAG",
                    "Qdrant",
                    "LangChain",
                ],
            )
        ]

    def get_recommended_jobs(self):

        return self.search_jobs()


def test_naukri_search_adapter():

    adapter = NaukriAdapter(
        FakeNaukriClient()
    )

    jobs = adapter.search(
        keyword="AI Engineer",
        location="Bangalore",
    )

    assert len(jobs) == 1

    job = jobs[0]

    assert job.job_id == "123"

    assert (
        job.title
        == "Generative AI Engineer"
    )

    assert job.company == "Test AI"

    assert job.source == "naukri"

    assert "Python" in (
        job.raw_data["tags"]
    )


def test_naukri_recommended_adapter():

    adapter = NaukriAdapter(
        FakeNaukriClient()
    )

    jobs = adapter.recommended()

    assert len(jobs) == 1
    assert jobs[0].job_id == "123"