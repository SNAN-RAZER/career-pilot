from app.application.application_queue import (
    ApplicationQueue,
)
from app.application.application_service import (
    ApplicationService,
)
from app.application.application_workflow import (
    ApplicationWorkflow,
)
from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.models.job import JobPosting
from app.store.application_store import (
    ApplicationStore,
)


def make_recommendation(
    job_id="100",
):

    job = JobPosting(
        job_id=job_id,
        title="AI Engineer",
        company="Test Company",
        location="Bangalore",
        description="Python RAG LLM",
        source="test",
    )

    return ApplicationRecommendation(
        job=job,
        match_score=95.0,
        eligibility_score=90.0,
        recommendation="APPLY",
        next_action="APPLY",
    )


def make_service(
    tmp_path,
):

    queue = ApplicationQueue()

    store = ApplicationStore(
        str(
            tmp_path
            / "applications.json"
        )
    )

    workflow = ApplicationWorkflow(
        queue,
        store,
    )

    return (
        ApplicationService(
            queue=queue,
            store=store,
            workflow=workflow,
        ),
        queue,
        store,
    )


def test_service_get_all(
    tmp_path,
):

    service, queue, store = make_service(
        tmp_path
    )

    recommendation = make_recommendation()

    service.workflow.enqueue(
        recommendation
    )

    applications = service.get_all()

    assert len(applications) == 1

    assert (
        applications[0].job.job_id
        == "100"
    )


def test_service_get_application(
    tmp_path,
):

    service, queue, store = make_service(
        tmp_path
    )

    service.workflow.enqueue(
        make_recommendation("100")
    )

    application = service.get("100")

    assert application is not None

    assert (
        application.job.job_id
        == "100"
    )


def test_service_get_unknown_application(
    tmp_path,
):

    service, queue, store = make_service(
        tmp_path
    )

    result = service.get(
        "does-not-exist"
    )

    assert result is None


def test_service_get_pending(
    tmp_path,
):

    service, queue, store = make_service(
        tmp_path
    )

    service.workflow.enqueue(
        make_recommendation("100")
    )

    pending = service.get_pending()

    assert len(pending) == 1

    assert (
        pending[0]
        .recommendation
        .job
        .job_id
        == "100"
    )


def test_service_apply(
    tmp_path,
):

    service, queue, store = make_service(
        tmp_path
    )

    service.workflow.enqueue(
        make_recommendation("100")
    )

    result = service.apply("100")

    assert result is not None

    assert result.status == "APPLIED"


def test_service_move_to_interview(
    tmp_path,
):

    service, queue, store = make_service(
        tmp_path
    )

    service.workflow.enqueue(
        make_recommendation("100")
    )

    service.apply("100")

    result = service.move_to_interview(
        "100"
    )

    assert result is not None

    assert (
        result.status
        == "INTERVIEW"
    )


def test_service_mark_offer(
    tmp_path,
):

    service, queue, store = make_service(
        tmp_path
    )

    service.workflow.enqueue(
        make_recommendation("100")
    )

    service.apply("100")

    service.move_to_interview(
        "100"
    )

    result = service.mark_offer(
        "100"
    )

    assert result is not None

    assert result.status == "OFFER"


def test_service_reject(
    tmp_path,
):

    service, queue, store = make_service(
        tmp_path
    )

    service.workflow.enqueue(
        make_recommendation("100")
    )

    result = service.reject("100")

    assert result is not None

    assert result.status == "REJECTED"


def test_service_add_note(
    tmp_path,
):

    service, queue, store = make_service(
        tmp_path
    )

    service.workflow.enqueue(
        make_recommendation("100")
    )

    result = service.add_note(
        "100",
        "Recruiter contacted me.",
    )

    assert result is not None

    assert (
        "Recruiter contacted me."
        in result.notes
    )