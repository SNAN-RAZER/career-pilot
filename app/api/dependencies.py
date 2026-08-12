from app.application.application_dashboard import (
    ApplicationDashboard,
)
from app.application.application_queue import (
    ApplicationQueue,
)
from app.application.application_service import (
    ApplicationService,
)
from app.application.application_workflow import (
    ApplicationWorkflow,
)
from app.store.application_store import (
    ApplicationStore,
)


class ApplicationDependencies:

    def __init__(
        self,
        store_path: str = "data/applications.json",
    ):
        self.queue = ApplicationQueue()

        self.store = ApplicationStore(
            store_path
        )

        for application in self.store.load():
            self.queue.load_application(
                application
            )

        self.workflow = ApplicationWorkflow(
            self.queue,
            self.store,
        )

        self.service = ApplicationService(
            queue=self.queue,
            store=self.store,
            workflow=self.workflow,
        )

        self.dashboard = ApplicationDashboard(
            self.service
        )
application_dependencies = (
    ApplicationDependencies()
)