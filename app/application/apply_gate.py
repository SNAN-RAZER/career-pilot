from app.application.exceptions import ApplyBlocked
from app.models.application_queue_item import (
    ApplicationQueueItem,
)


def require_ready_to_apply(
    item: ApplicationQueueItem,
) -> None:

    job = item.recommendation.job

    if job.source != "naukri":
        return

    if item.tailored_resume is None:
        raise ApplyBlocked(
            "Tailor a resume before applying "
            "on Naukri."
        )
