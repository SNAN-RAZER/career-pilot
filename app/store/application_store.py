import json
from pathlib import Path

from app.models.application_record import (
    ApplicationRecord,
)

from app.models.application_status import (
    ApplicationStatus,
)

from app.services.application_state_machine import (
    ApplicationStateMachine,
)
class ApplicationStore:

    def __init__(
        self,
        path: str = "data/applications.json",
    ):
        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        application: ApplicationRecord,
    ) -> ApplicationRecord:

        applications = self.load()

        existing_index = next(
            (
                index
                for index, item in enumerate(
                    applications
                )
                if item.job.job_id
                == application.job.job_id
            ),
            None,
        )

        if existing_index is None:

            applications.append(
                application
            )

        else:

            applications[
                existing_index
            ] = application

        self._write(applications)

        return application

    def get(
        self,
        job_id: str,
    ) -> ApplicationRecord | None:

        applications = self.load()

        for application in applications:

            if application.job.job_id == job_id:
                return application

        return None

    def load(self) -> list[ApplicationRecord]:

        if not self.path.exists():
            return []

        data = json.loads(
            self.path.read_text(
                encoding="utf-8"
            )
        )

        return [
            ApplicationRecord.model_validate(item)
            for item in data
        ]

    def update_status(
    self,
    job_id: str,
    status: str,
) -> ApplicationRecord | None:

        application = self.get(job_id)

        if application is None:
            return None

        current_status = ApplicationStatus(
            application.status
        )

        target_status = ApplicationStatus(
            status
        )

        new_status = (
            ApplicationStateMachine.transition(
                current_status,
                target_status,
            )
        )

        application.status = new_status.value

        self.save(application)

        return application
    def _write(
        self,
        applications: list[ApplicationRecord],
    ):

        self.path.write_text(
            json.dumps(
                [
                    item.model_dump(
                        mode="json"
                    )
                    for item in applications
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

    def add_note(
        self,
        job_id: str,
        note: str,
    ) -> ApplicationRecord | None:

        application = self.get(job_id)

        if application is None:
            return None

        note = note.strip()

        if not note:
            raise ValueError(
                "Note cannot be empty."
            )

        application.notes.append(note)

        self.save(application)

        return application