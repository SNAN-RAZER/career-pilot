from app.models.application_record import (
    ApplicationRecord,
)


class ApplicationNotes:

    @staticmethod
    def add(
        application: ApplicationRecord,
        note: str,
    ) -> ApplicationRecord:

        note = note.strip()

        if not note:
            raise ValueError(
                "Note cannot be empty."
            )

        application.notes.append(note)

        return application