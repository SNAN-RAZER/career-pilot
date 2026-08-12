from app.models.application_queue_item import ApplicationQueueItem
from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.models.application_status import ApplicationStatus
from app.services.application_state_machine import (
    ApplicationStateMachine,
)
from app.models.application_record import (
    ApplicationRecord,
)
class ApplicationQueue:

    def __init__(self):
        self._items: list[ApplicationQueueItem] = []

    def add(
        self,
        recommendation: ApplicationRecommendation,
        priority: str = "NORMAL",
    ) -> ApplicationQueueItem:

        # Prevent the same job from entering
        # the queue more than once.
        for item in self._items:

            if (
                item.recommendation.job.job_id
                == recommendation.job.job_id
            ):

                return item

        item = ApplicationQueueItem(
            recommendation=recommendation,
            priority=priority,
        )

        self._items.append(item)

        return item

    def get_all(
        self,
    ) -> list[ApplicationQueueItem]:

        return list(self._items)

    def get_pending(
    self,
) -> list[ApplicationQueueItem]:

        pending = [
            item
            for item in self._items
            if item.status == "PENDING"
        ]

        return sorted(
            pending,
            key=self._sort_key,
        )

    def get_by_job_id(
        self,
        job_id: str,
    ) -> ApplicationQueueItem | None:

        for item in self._items:

            if (
                item.recommendation.job.job_id
                == job_id
            ):

                return item

        return None

    def remove(
        self,
        job_id: str,
    ) -> bool:

        item = self.get_by_job_id(job_id)

        if item is None:
            return False

        self._items.remove(item)

        return True


    def update_status(
    self,
    job_id: str,
    status: str,
) -> ApplicationQueueItem | None:

        item = self.get_by_job_id(job_id)

        if item is None:
            return None

        current_status = ApplicationStatus(
            item.status
        )

        target_status = ApplicationStatus(
            status
        )

        new_status = ApplicationStateMachine.transition(
            current_status,
            target_status,
        )

        item.status = new_status.value

        return item

    def add_note(
    self,
    job_id: str,
    note: str,
) -> ApplicationQueueItem | None:

        item = self.get_by_job_id(job_id)

        if item is None:
            return None

        note = note.strip()

        if not note:
            raise ValueError(
                "Note cannot be empty."
            )

        item.notes.append(note)

        return item
    def build(
    self,
    recommendations: list[ApplicationRecommendation],
) -> list[ApplicationQueueItem]:

        for recommendation in recommendations:

            if recommendation.recommendation == "REJECT":
                continue

            priority = self._priority(
                recommendation
            )

            self.add(
                recommendation,
                priority=priority,
            )

        return self.get_pending()


    @staticmethod
    def _priority(
        recommendation: ApplicationRecommendation,
    ) -> str:

        if (
            recommendation.recommendation == "APPLY"
            and recommendation.match_score >= 90
        ):
            return "HIGH"

        if (
            recommendation.recommendation == "APPLY"
        ):
            return "NORMAL"

        return "LOW"


    @staticmethod
    def _sort_key(
        item: ApplicationQueueItem,
    ):
        priority_order = {
            "HIGH": 0,
            "NORMAL": 1,
            "LOW": 2,
        }

        return (
            priority_order.get(
                item.priority,
                99,
            ),
            -item.recommendation.match_score,
        )

    def load_application(
    self,
    application: ApplicationRecord,
) -> ApplicationQueueItem:

        existing = self.get_by_job_id(
            application.job.job_id
        )

        if existing is not None:
            existing.status = application.status
            existing.notes = list(
                application.notes
            )

            return existing

        recommendation = ApplicationRecommendation(
            job=application.job,
            match_score=application.match_score,
            eligibility_score=(
                application.eligibility_score
            ),
            recommendation=(
                application.recommendation
            ),
            missing_requirements=list(
                application.missing_requirements
            ),
            reasons=list(
                application.reasons
            ),
            next_action=(
                "APPLY"
                if application.recommendation
                == "APPLY"
                else "REVIEW"
                if application.recommendation
                == "REVIEW"
                else "REJECT"
            ),
        )

        item = ApplicationQueueItem(
            recommendation=recommendation,
            status=application.status,
            notes=list(application.notes),
        )

        self._items.append(item)

        return item