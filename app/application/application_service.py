from app.application.application_queue import (
    ApplicationQueue,
)
from app.application.application_workflow import (
    ApplicationWorkflow,
)
from app.models.application_queue_item import (
    ApplicationQueueItem,
)
from app.models.application_record import (
    ApplicationRecord,
)
from app.store.application_store import (
    ApplicationStore,
)


class ApplicationService:

    def __init__(
        self,
        queue: ApplicationQueue,
        store: ApplicationStore,
        workflow: ApplicationWorkflow | None = None,
    ):
        self.queue = queue
        self.store = store

        self.workflow = (
            workflow
            or ApplicationWorkflow(
                queue,
                store,
            )
        )

    def get_all(
        self,
    ) -> list[ApplicationRecord]:

        return self.store.load()

    def get(
        self,
        job_id: str,
    ) -> ApplicationRecord | None:

        return self.store.get(job_id)

    def get_pending(
        self,
    ) -> list[ApplicationQueueItem]:

        return self.queue.get_pending()

    def apply(
        self,
        job_id: str,
    ) -> ApplicationQueueItem | None:

        return self.workflow.apply(job_id)

    def move_to_interview(
        self,
        job_id: str,
    ) -> ApplicationQueueItem | None:

        return self.workflow.move_to_interview(
            job_id
        )

    def mark_offer(
        self,
        job_id: str,
    ) -> ApplicationQueueItem | None:

        return self.workflow.mark_offer(
            job_id
        )

    def reject(
        self,
        job_id: str,
    ) -> ApplicationQueueItem | None:

        return self.workflow.reject(job_id)

    def add_note(
        self,
        job_id: str,
        note: str,
    ) -> ApplicationQueueItem | None:

        return self.workflow.add_note(
            job_id,
            note,
        )