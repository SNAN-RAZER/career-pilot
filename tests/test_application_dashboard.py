from app.application.application_dashboard import (
    ApplicationDashboard,
)
from app.application.application_service import (
    ApplicationService,
)
from app.application.application_queue import (
    ApplicationQueue,
)
from app.application.application_workflow import (
    ApplicationWorkflow,
)
from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.models.application_summary import (
    ApplicationSummary,
)
from app.models.job import JobPosting
from app.store.application_store import (
    ApplicationStore,
)


def make_recommendation(
    job_id="100",
    score=95.0,
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
        match_score=score,
        eligibility_score=90.0,
        recommendation="APPLY",
        missing_requirements=[],
        reasons=[
            "Strong candidate alignment."
        ],
        next_action="APPLY",
    )


def make_dashboard(tmp_path):

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

    service = ApplicationService(
        queue=queue,
        store=store,
        workflow=workflow,
    )

    return ApplicationDashboard(
        service
    ), workflow


def test_dashboard_returns_application_summary(
    tmp_path,
):

    dashboard, workflow = make_dashboard(
        tmp_path
    )

    workflow.enqueue(
        make_recommendation()
    )

    applications = (
        dashboard.get_applications()
    )

    assert len(applications) == 1

    summary = applications[0]

    assert isinstance(
        summary,
        ApplicationSummary,
    )

    assert summary.job_id == "100"
    assert summary.title == "AI Engineer"
    assert summary.company == "Test Company"
    assert summary.location == "Bangalore"

    assert summary.status == "PENDING"

    assert summary.match_score == 95.0
    assert summary.eligibility_score == 90.0

    assert (
        summary.recommendation
        == "APPLY"
    )

    assert summary.notes_count == 0

    assert summary.next_action == "TAILOR"


def test_dashboard_gets_application_by_job_id(
    tmp_path,
):

    dashboard, workflow = make_dashboard(
        tmp_path
    )

    workflow.enqueue(
        make_recommendation("200")
    )

    summary = (
        dashboard.get_application("200")
    )

    assert summary is not None

    assert summary.job_id == "200"
    assert summary.title == "AI Engineer"


def test_dashboard_returns_none_for_unknown_job(
    tmp_path,
):

    dashboard, workflow = make_dashboard(
        tmp_path
    )

    result = dashboard.get_application(
        "does-not-exist"
    )

    assert result is None


def test_dashboard_counts_notes(
    tmp_path,
):

    dashboard, workflow = make_dashboard(
        tmp_path
    )

    workflow.enqueue(
        make_recommendation("300")
    )

    workflow.add_note(
        "300",
        "Recruiter contacted me.",
    )

    workflow.add_note(
        "300",
        "Interview scheduled.",
    )

    summary = (
        dashboard.get_application("300")
    )

    assert summary is not None

    assert summary.notes_count == 2


def test_dashboard_reflects_application_status(
    tmp_path,
):

    dashboard, workflow = make_dashboard(
        tmp_path
    )

    workflow.enqueue(
        make_recommendation("400")
    )

    workflow.apply("400")

    summary = (
        dashboard.get_application("400")
    )

    assert summary is not None

    assert summary.status == "APPLIED"
    assert summary.next_action == "WAIT"


def test_dashboard_reflects_interview_status(
    tmp_path,
):

    dashboard, workflow = make_dashboard(
        tmp_path
    )

    workflow.enqueue(
        make_recommendation("500")
    )

    workflow.apply("500")

    workflow.move_to_interview(
        "500"
    )

    summary = (
        dashboard.get_application("500")
    )

    assert summary is not None

    assert summary.status == "INTERVIEW"
    assert (
        summary.next_action
        == "FOLLOW_UP"
    )


def test_dashboard_reflects_offer_status(
    tmp_path,
):

    dashboard, workflow = make_dashboard(
        tmp_path
    )

    workflow.enqueue(
        make_recommendation("600")
    )

    workflow.apply("600")

    workflow.move_to_interview(
        "600"
    )

    workflow.mark_offer("600")

    summary = (
        dashboard.get_application("600")
    )

    assert summary is not None

    assert summary.status == "OFFER"
    assert (
        summary.next_action
        == "NEGOTIATE"
    )


def test_dashboard_reflects_rejected_status(
    tmp_path,
):

    dashboard, workflow = make_dashboard(
        tmp_path
    )

    workflow.enqueue(
        make_recommendation("700")
    )

    workflow.reject("700")

    summary = (
        dashboard.get_application("700")
    )

    assert summary is not None

    assert summary.status == "REJECTED"
    assert summary.next_action == "CLOSED"