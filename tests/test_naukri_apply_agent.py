from app.application.application_queue import (
    ApplicationQueue,
)
from app.application.application_workflow import (
    ApplicationWorkflow,
)
from app.application.exceptions import ApplyBlocked
from app.application.naukri_apply_agent import (
    NaukriApplyAgent,
)
from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.models.job import JobPosting
from app.models.tailored_resume import (
    ATSResult,
    TailoredResume,
)


class FakeNaukriApplyClient:

    def __init__(
        self,
        external: bool = False,
        questionnaire: bool = False,
    ):
        self.external = external
        self.questionnaire = questionnaire
        self.applied: list[str] = []

    def is_external_apply(self, job_id: str):
        return self.external

    def apply_job(self, job, **kwargs):
        self.applied.append(job.job_id)

        if self.questionnaire:
            return {
                "jobs": [
                    {
                        "questionnaire": [
                            {"q": "Why us?"}
                        ]
                    }
                ]
            }

        return {"jobs": [{"applied": True}]}


def make_item(
    queue: ApplicationQueue,
    job_id: str = "naukri-1",
    source: str = "naukri",
    ready: bool = True,
):

    job = JobPosting(
        job_id=job_id,
        title="AI Engineer",
        company="Naukri Co",
        location="Bangalore",
        description="Python RAG LLM",
        source=source,
        raw_data={
            "tags": ["Python", "RAG", "LLM"],
        },
        url="https://www.naukri.com/job-listings-naukri-1",
    )

    recommendation = ApplicationRecommendation(
        job=job,
        match_score=90.0,
        eligibility_score=88.0,
        recommendation="APPLY",
        next_action="APPLY",
    )

    item = queue.add(recommendation)

    if ready:
        item.tailored_resume = TailoredResume(
            summary="Python RAG engineer.",
            skills=["Python", "RAG", "LLM"],
        )
        item.ats = ATSResult(
            score=82.0,
            passed=True,
        )

    return item


def test_track_only_for_non_naukri_jobs():

    queue = ApplicationQueue()
    make_item(queue, source="test", ready=False)

    client = FakeNaukriApplyClient()
    workflow = ApplicationWorkflow(
        queue,
        apply_agent=NaukriApplyAgent(
            client=client
        ),
    )

    result = workflow.apply("naukri-1")

    assert result.status == "APPLIED"
    assert result.applied_via == "TRACKED"
    assert client.applied == []


def test_naukri_easy_apply_submits():

    queue = ApplicationQueue()
    make_item(queue)

    client = FakeNaukriApplyClient()
    workflow = ApplicationWorkflow(
        queue,
        apply_agent=NaukriApplyAgent(
            client=client
        ),
    )

    result = workflow.apply("naukri-1")

    assert result.status == "APPLIED"
    assert result.applied_via == (
        "NAUKRI_EASY_APPLY"
    )
    assert client.applied == ["naukri-1"]


def test_naukri_apply_requires_tailored_resume():

    queue = ApplicationQueue()
    make_item(queue, ready=False)

    workflow = ApplicationWorkflow(
        queue,
        apply_agent=NaukriApplyAgent(
            client=FakeNaukriApplyClient()
        ),
    )

    try:
        workflow.apply("naukri-1")
        raise AssertionError(
            "Expected ApplyBlocked"
        )
    except ApplyBlocked as exc:
        assert "Tailor a resume" in str(exc)

    assert (
        queue.get_by_job_id("naukri-1").status
        == "PENDING"
    )


def test_skips_external_apply():

    queue = ApplicationQueue()
    make_item(queue)

    workflow = ApplicationWorkflow(
        queue,
        apply_agent=NaukriApplyAgent(
            client=FakeNaukriApplyClient(
                external=True
            )
        ),
    )

    try:
        workflow.apply("naukri-1")
        raise AssertionError(
            "Expected ApplyBlocked"
        )
    except ApplyBlocked as exc:
        assert "external" in str(exc).lower()

    assert (
        queue.get_by_job_id("naukri-1").status
        == "PENDING"
    )


def test_skips_questionnaire():

    queue = ApplicationQueue()
    make_item(queue)

    workflow = ApplicationWorkflow(
        queue,
        apply_agent=NaukriApplyAgent(
            client=FakeNaukriApplyClient(
                questionnaire=True
            )
        ),
    )

    try:
        workflow.apply("naukri-1")
        raise AssertionError(
            "Expected ApplyBlocked"
        )
    except ApplyBlocked as exc:
        assert "questionnaire" in str(exc).lower()
        assert "naukri.com" in str(exc).lower()

    assert (
        queue.get_by_job_id("naukri-1").status
        == "PENDING"
    )


def test_unconfirmed_naukri_response_is_not_applied():

    queue = ApplicationQueue()
    make_item(queue)

    class UnconfirmedClient(FakeNaukriApplyClient):

        def apply_job(self, job, **kwargs):
            self.applied.append(job.job_id)
            return {"jobs": [{}]}

    workflow = ApplicationWorkflow(
        queue,
        apply_agent=NaukriApplyAgent(
            client=UnconfirmedClient()
        ),
    )

    try:
        workflow.apply("naukri-1")
        raise AssertionError(
            "Expected ApplyBlocked"
        )
    except ApplyBlocked as exc:
        assert "did not confirm" in str(exc)

    assert (
        queue.get_by_job_id("naukri-1").status
        == "PENDING"
    )
