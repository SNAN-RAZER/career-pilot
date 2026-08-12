from app.application.application_service import (
    ApplicationService,
)
from app.models.application_summary import (
    ApplicationSummary,
)


class ApplicationDashboard:

    def __init__(
        self,
        service: ApplicationService,
    ):
        self.service = service

    def get_applications(
        self,
    ) -> list[ApplicationSummary]:

        applications = (
            self.service.get_all()
        )

        return [
            self._to_summary(application)
            for application in applications
        ]

    def get_application(
        self,
        job_id: str,
    ) -> ApplicationSummary | None:

        application = self.service.get(
            job_id
        )

        if application is None:
            return None

        return self._to_summary(
            application
        )

    @staticmethod
    def _to_summary(
        application,
    ) -> ApplicationSummary:

        job = application.job

        next_action = (
            "APPLY"
            if application.status == "PENDING"
            and application.recommendation == "APPLY"
            else "WAIT"
            if application.status == "APPLIED"
            else "FOLLOW_UP"
            if application.status == "INTERVIEW"
            else "NEGOTIATE"
            if application.status == "OFFER"
            else "CLOSED"
        )

        return ApplicationSummary(
            job_id=job.job_id,
            title=job.title,
            company=job.company,
            location=job.location,
            status=application.status,
            match_score=application.match_score,
            eligibility_score=(
                application.eligibility_score
            ),
            recommendation=(
                application.recommendation
            ),
            missing_requirements=(
                application.missing_requirements
            ),
            reasons=application.reasons,
            notes_count=len(application.notes),
            next_action=next_action,
        )