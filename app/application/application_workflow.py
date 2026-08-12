from app.application.application_queue import ApplicationQueue
from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.store.application_store import ApplicationStore


class ApplicationWorkflow:

    def __init__(
        self,
        queue: ApplicationQueue,
        store: ApplicationStore | None = None,
    ):
        self.queue = queue
        self.store = store

    def _persist(
        self,
        item,
    ):
        if self.store is not None and item is not None:
            self.store.save(
                item.to_application_record()
            )

        return item

    def enqueue(
        self,
        recommendation: ApplicationRecommendation,
    ):

        if recommendation.next_action != "APPLY":
            return None

        item = self.queue.add(
            recommendation
        )

        return self._persist(item)

    def apply(
        self,
        job_id: str,
    ):

        item = self.queue.update_status(
            job_id,
            "APPLIED",
        )

        return self._persist(item)

    def move_to_interview(
        self,
        job_id: str,
    ):

        item = self.queue.update_status(
            job_id,
            "INTERVIEW",
        )

        return self._persist(item)

    def mark_offer(
        self,
        job_id: str,
    ):

        item = self.queue.update_status(
            job_id,
            "OFFER",
        )

        return self._persist(item)

    def reject(
        self,
        job_id: str,
    ):

        item = self.queue.update_status(
            job_id,
            "REJECTED",
        )

        return self._persist(item)

    def add_note(
        self,
        job_id: str,
        note: str,
    ):

        item = self.queue.add_note(
            job_id,
            note,
        )

        return self._persist(item)