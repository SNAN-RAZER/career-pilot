from app.application.application_queue import ApplicationQueue
from app.application.exceptions import ApplyBlocked
from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.store.application_store import ApplicationStore


class ApplicationWorkflow:

    def __init__(
        self,
        queue: ApplicationQueue,
        store: ApplicationStore | None = None,
        apply_agent=None,
    ):
        self.queue = queue
        self.store = store
        self.apply_agent = apply_agent

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

        item = self.queue.add(
            recommendation
        )

        return self._persist(item)

    def apply(
        self,
        job_id: str,
    ):

        item = self.queue.get_by_job_id(job_id)

        if item is None:
            return None

        if self.apply_agent is not None:
            result = self.apply_agent.submit(
                item
            )

            if not result.submitted:
                raise ApplyBlocked(
                    result.message
                )

            item.applied_via = result.mode
            item.apply_message = result.message
            item.notes.append(result.message)

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

    def tailor(
        self,
        job_id: str,
        package,
    ):

        item = self.queue.get_by_job_id(job_id)

        if item is None:
            return None

        item.tailored_resume = package.resume
        item.ats = package.ats
        item.resume_path = package.resume_path

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