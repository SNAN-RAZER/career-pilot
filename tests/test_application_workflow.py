from app.application.application_queue import (
    ApplicationQueue,
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
    next_action="APPLY",
):

    job = JobPosting(
        job_id=job_id,
        title="AI Engineer",
        company="Test Company",
        location="Bangalore",
        description="Python RAG LLM",
        source="test",
    )

    recommendation = (
        "REJECT"
        if next_action == "REJECT"
        else "REVIEW"
        if next_action == "REVIEW"
        else "APPLY"
    )

    return ApplicationRecommendation(
        job=job,
        match_score=90.0,
        eligibility_score=90.0,
        recommendation=recommendation,
        next_action=next_action,
    )


def test_workflow_enqueues_apply_recommendation():

    queue = ApplicationQueue()

    workflow = ApplicationWorkflow(
        queue
    )

    recommendation = make_recommendation(
        "100",
        "APPLY",
    )

    result = workflow.enqueue(
        recommendation
    )

    assert result is not None

    assert (
        result.recommendation.job.job_id
        == "100"
    )

    assert result.status == "PENDING"


def test_workflow_enqueues_rejected_recommendation():

    queue = ApplicationQueue()

    workflow = ApplicationWorkflow(
        queue
    )

    recommendation = make_recommendation(
        "100",
        "REJECT",
    )

    result = workflow.enqueue(
        recommendation
    )

    assert result is not None
    assert result.status == "PENDING"
    assert (
        result.recommendation.recommendation
        == "REJECT"
    )
    assert len(queue.get_all()) == 1


def test_workflow_enqueues_review_recommendation():

    queue = ApplicationQueue()

    workflow = ApplicationWorkflow(
        queue
    )

    recommendation = make_recommendation(
        "100",
        "REVIEW",
    )

    result = workflow.enqueue(
        recommendation
    )

    assert result is not None
    assert result.status == "PENDING"


def test_workflow_applies_application():

    queue = ApplicationQueue()
    workflow = ApplicationWorkflow(queue)

    workflow.enqueue(
        make_recommendation("100")
    )

    result = workflow.apply("100")

    assert result is not None
    assert result.status == "APPLIED"


def test_workflow_moves_application_to_interview():

    queue = ApplicationQueue()
    workflow = ApplicationWorkflow(queue)

    workflow.enqueue(
        make_recommendation("100")
    )

    workflow.apply("100")

    result = workflow.move_to_interview("100")

    assert result is not None
    assert result.status == "INTERVIEW"


def test_workflow_marks_application_as_offer():

    queue = ApplicationQueue()
    workflow = ApplicationWorkflow(queue)

    workflow.enqueue(
        make_recommendation("100")
    )

    workflow.apply("100")
    workflow.move_to_interview("100")

    result = workflow.mark_offer("100")

    assert result is not None
    assert result.status == "OFFER"


def test_workflow_rejects_application():

    queue = ApplicationQueue()
    workflow = ApplicationWorkflow(queue)

    workflow.enqueue(
        make_recommendation("100")
    )

    result = workflow.reject("100")

    assert result is not None
    assert result.status == "REJECTED"


def test_workflow_adds_application_note():

    queue = ApplicationQueue()
    workflow = ApplicationWorkflow(queue)

    workflow.enqueue(
        make_recommendation("100")
    )

    result = workflow.add_note(
        "100",
        "Recruiter contacted me.",
    )

    assert result is not None
    assert result.notes == [
        "Recruiter contacted me."
    ]

def test_workflow_persists_application_on_enqueue(
    tmp_path,
):

    queue = ApplicationQueue()

    store = ApplicationStore(
        str(
            tmp_path / "applications.json"
        )
    )

    workflow = ApplicationWorkflow(
        queue,
        store,
    )

    workflow.enqueue(
        make_recommendation("100")
    )

    stored = store.get("100")

    assert stored is not None

    assert stored.job.title == "AI Engineer"
    assert stored.status == "PENDING"
    assert stored.recommendation == "APPLY"


def test_workflow_persists_status_changes(
    tmp_path,
):

    queue = ApplicationQueue()

    store = ApplicationStore(
        str(
            tmp_path / "applications.json"
        )
    )

    workflow = ApplicationWorkflow(
        queue,
        store,
    )

    workflow.enqueue(
        make_recommendation("100")
    )

    workflow.apply("100")

    stored = store.get("100")

    assert stored is not None
    assert stored.status == "APPLIED"

    workflow.move_to_interview("100")

    stored = store.get("100")

    assert stored is not None
    assert stored.status == "INTERVIEW"

    workflow.mark_offer("100")

    stored = store.get("100")

    assert stored is not None
    assert stored.status == "OFFER"


def test_workflow_persists_rejection(
    tmp_path,
):

    queue = ApplicationQueue()

    store = ApplicationStore(
        str(
            tmp_path / "applications.json"
        )
    )

    workflow = ApplicationWorkflow(
        queue,
        store,
    )

    workflow.enqueue(
        make_recommendation("100")
    )

    workflow.reject("100")

    stored = store.get("100")

    assert stored is not None
    assert stored.status == "REJECTED"


def test_workflow_persists_application_note(
    tmp_path,
):

    queue = ApplicationQueue()

    store = ApplicationStore(
        str(
            tmp_path / "applications.json"
        )
    )

    workflow = ApplicationWorkflow(
        queue,
        store,
    )

    workflow.enqueue(
        make_recommendation("100")
    )

    workflow.add_note(
        "100",
        "Recruiter contacted me.",
    )

    stored = store.get("100")

    assert stored is not None

    assert (
        "Recruiter contacted me."
        in stored.notes
    )