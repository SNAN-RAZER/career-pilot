from inspect import isawaitable

from pydantic import BaseModel, Field

from app.matching.decision_engine import DecisionEngine
from app.models.application_queue_item import (
    ApplicationQueueItem,
)


MIN_MATCH_SCORE = DecisionEngine.AUTO_APPLY_SCORE


class BulkApplyItem(BaseModel):

    job_id: str
    title: str
    company: str
    match_score: float
    status: str
    detail: str = ""


class BulkApplyReport(BaseModel):

    min_match: float
    applied: list[BulkApplyItem] = Field(
        default_factory=list
    )
    skipped: list[BulkApplyItem] = Field(
        default_factory=list
    )
    failed: list[BulkApplyItem] = Field(
        default_factory=list
    )
    message: str = ""


def job_meets_apply_threshold(
    item: ApplicationQueueItem,
    min_match: float = MIN_MATCH_SCORE,
) -> str | None:

    if item.status != "PENDING":
        return f"status is {item.status}"

    rec = item.recommendation
    job = rec.job

    if getattr(job, "source", "") == "test":
        return "test job"

    if rec.recommendation != "APPLY":
        return (
            f"recommendation is {rec.recommendation}, "
            "not APPLY"
        )

    if rec.match_score < min_match:
        return (
            f"match {rec.match_score:.0f}% is below "
            f"{min_match:.0f}%"
        )

    if rec.eligibility_score < min_match:
        return (
            f"eligibility {rec.eligibility_score:.0f}% "
            f"is below {min_match:.0f}%"
        )

    return None


def select_bulk_targets(
    items: list[ApplicationQueueItem],
    min_match: float = MIN_MATCH_SCORE,
    limit: int | None = None,
) -> tuple[list[ApplicationQueueItem], list[BulkApplyItem]]:

    selected = []
    skipped = []

    for item in items:
        rec = item.recommendation
        job = rec.job
        reason = job_meets_apply_threshold(
            item,
            min_match,
        )

        if reason is None:
            selected.append(item)
            continue

        if item.status != "PENDING":
            continue

        if getattr(job, "source", "") == "test":
            continue

        skipped.append(
            _item_from(item, "skipped", reason)
        )

    selected.sort(
        key=lambda item: item.recommendation.match_score,
        reverse=True,
    )

    if limit is not None:
        overflow = selected[limit:]
        selected = selected[:limit]

        for item in overflow:
            skipped.append(
                _item_from(
                    item,
                    "skipped",
                    f"over the {limit}-job bulk cap",
                )
            )

    return selected, skipped


def _item_from(
    item: ApplicationQueueItem,
    status: str,
    detail: str,
) -> BulkApplyItem:

    rec = item.recommendation
    job = rec.job

    return BulkApplyItem(
        job_id=job.job_id,
        title=job.title,
        company=job.company,
        match_score=rec.match_score,
        status=status,
        detail=detail,
    )


async def _call(action, job_id: str):

    result = action(job_id)

    if isawaitable(result):
        return await result

    return result


async def apply_one_job(
    item: ApplicationQueueItem,
    apply,
    tailor=None,
    fallback=None,
) -> BulkApplyItem:

    rec = item.recommendation
    job = rec.job
    job_id = job.job_id

    try:
        if tailor is not None:
            await _call(tailor, job_id)
    except Exception as exc:
        return _item_from(
            item,
            "failed",
            f"tailor failed, moving on: {exc}",
        )

    try:
        await _call(apply, job_id)
        return _item_from(
            item,
            "applied",
            "Naukri Easy Apply",
        )
    except Exception as easy_exc:
        if fallback is None:
            return _item_from(
                item,
                "skipped",
                f"Easy Apply blocked, moving on: {easy_exc}",
            )

        try:
            detail = await _call(fallback, job_id)
            return _item_from(
                item,
                "applied",
                (
                    "Fallback after Easy Apply failed "
                    f"({easy_exc}): {detail}"
                ),
            )
        except Exception as fallback_exc:
            return _item_from(
                item,
                "skipped",
                (
                    f"Easy Apply: {easy_exc}. "
                    f"Fallback: {fallback_exc}. "
                    "Moved on to the next job."
                ),
            )


async def run_bulk_apply(
    items: list[ApplicationQueueItem],
    apply,
    tailor=None,
    fallback=None,
    min_match: float = MIN_MATCH_SCORE,
) -> BulkApplyReport:

    floor = max(70.0, min(float(min_match), 100.0))
    selected, skipped = select_bulk_targets(
        items,
        min_match=floor,
    )
    applied = []
    failed = []

    for item in selected:
        result = await apply_one_job(
            item,
            apply=apply,
            tailor=tailor,
            fallback=fallback,
        )

        if result.status == "applied":
            applied.append(result)
        elif result.status == "failed":
            failed.append(result)
        else:
            skipped.append(result)

    message = (
        f"Tried {len(selected)} qualified job(s) "
        f"(match ≥ {floor:.0f}%, APPLY). "
        f"Applied {len(applied)}, skipped {len(skipped)}, "
        f"failed {len(failed)}. "
        "One failure never stops the rest."
    )

    return BulkApplyReport(
        min_match=floor,
        applied=applied,
        skipped=skipped,
        failed=failed,
        message=message,
    )
