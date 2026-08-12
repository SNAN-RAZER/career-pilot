from app.models.application_status import (
    ApplicationStatus,
)


class InvalidApplicationTransition(
    ValueError
):
    pass


class ApplicationStateMachine:

    ALLOWED_TRANSITIONS = {

        ApplicationStatus.PENDING: {
            ApplicationStatus.APPLIED,
            ApplicationStatus.REJECTED,
        },

        ApplicationStatus.APPLIED: {
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.REJECTED,
        },

        ApplicationStatus.INTERVIEW: {
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
        },

        ApplicationStatus.OFFER: set(),

        ApplicationStatus.REJECTED: set(),
    }

    @classmethod
    def can_transition(
        cls,
        current: ApplicationStatus,
        target: ApplicationStatus,
    ) -> bool:

        return target in cls.ALLOWED_TRANSITIONS.get(
            current,
            set(),
        )

    @classmethod
    def transition(
        cls,
        current: ApplicationStatus,
        target: ApplicationStatus,
    ) -> ApplicationStatus:

        if not cls.can_transition(
            current,
            target,
        ):

            raise InvalidApplicationTransition(
                f"Invalid application status "
                f"transition: "
                f"{current.value} -> "
                f"{target.value}"
            )

        return target