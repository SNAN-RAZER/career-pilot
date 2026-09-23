from asyncio import run as run_async

from app.application.application_queue import (
    ApplicationQueue,
)
from app.application.bulk_apply import (
    MIN_MATCH_SCORE,
    select_bulk_targets,
    run_bulk_apply,
)
from app.application.exceptions import ApplyBlocked
from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.models.job import JobPosting


def _item(
    queue: ApplicationQueue,
    job_id: str,
    match: float,
    recommendation: str = "APPLY",
    eligibility: float | None = None,
    source: str = "naukri",
    status: str | None = None,
):

    rec = ApplicationRecommendation(
        job=JobPosting(
            job_id=job_id,
            title=f"Role {job_id}",
            company="Acme",
            location="Bangalore",
            description="Python",
            source=source,
        ),
        match_score=match,
        eligibility_score=(
            eligibility if eligibility is not None else match
        ),
        recommendation=recommendation,
        next_action=recommendation,
    )
    item = queue.add(rec)

    if status:
        item.status = status

    return item


def test_bulk_skips_weak_and_review_jobs():

    queue = ApplicationQueue()
    _item(queue, "strong", 92)
    _item(queue, "weak", 54)
    _item(queue, "review", 72, recommendation="REVIEW")
    _item(queue, "reject", 88, recommendation="REJECT")
    _item(
        queue,
        "low-elig",
        91,
        eligibility=40,
    )

    selected, skipped = select_bulk_targets(
        queue.get_all(),
        min_match=MIN_MATCH_SCORE,
    )

    assert [item.recommendation.job.job_id for item in selected] == [
        "strong"
    ]
    reasons = {item.job_id: item.detail for item in skipped}
    assert "weak" in reasons
    assert "review" in reasons
    assert "reject" in reasons
    assert "eligibility" in reasons["low-elig"]


def test_bulk_apply_submits_only_threshold_jobs():

    queue = ApplicationQueue()
    _item(queue, "keep", 88)
    _item(queue, "junk", 41)
    applied_ids = []

    def apply(job_id: str):
        applied_ids.append(job_id)

    report = run_async(
        run_bulk_apply(
            queue.get_all(),
            apply=apply,
            min_match=80,
        )
    )

    assert applied_ids == ["keep"]
    assert report.applied[0].job_id == "keep"
    assert any(item.job_id == "junk" for item in report.skipped)


def test_one_failure_does_not_stop_later_jobs():

    queue = ApplicationQueue()
    _item(queue, "boom", 95)
    _item(queue, "ok", 88)
    applied_ids = []

    def apply(job_id: str):
        if job_id == "boom":
            raise RuntimeError("Naukri timed out")

        applied_ids.append(job_id)

    report = run_async(
        run_bulk_apply(
            queue.get_all(),
            apply=apply,
        )
    )

    assert applied_ids == ["ok"]
    assert report.applied[0].job_id == "ok"
    assert any(item.job_id == "boom" for item in report.skipped)


def test_fallback_runs_when_easy_apply_is_blocked():

    queue = ApplicationQueue()
    _item(queue, "external", 90)
    _item(queue, "easy", 85)
    fallback_ids = []

    def apply(job_id: str):
        if job_id == "external":
            raise ApplyBlocked(
                "Apply on the company website"
            )

    def fallback(job_id: str):
        fallback_ids.append(job_id)
        return "Web agent filled"

    report = run_async(
        run_bulk_apply(
            queue.get_all(),
            apply=apply,
            fallback=fallback,
        )
    )

    assert fallback_ids == ["external"]
    applied = {item.job_id for item in report.applied}
    assert applied == {"easy"}
    assert {item.job_id for item in report.prepared} == {"external"}


def test_failed_fallback_still_applies_next_job():

    queue = ApplicationQueue()
    _item(queue, "external", 91)
    _item(queue, "easy", 84)

    def apply(job_id: str):
        if job_id == "external":
            raise ApplyBlocked("company site")

    def fallback(job_id: str):
        raise RuntimeError("Chrome crashed")

    report = run_async(
        run_bulk_apply(
            queue.get_all(),
            apply=apply,
            fallback=fallback,
        )
    )

    assert report.applied[0].job_id == "easy"
    assert any(item.job_id == "external" for item in report.skipped)
