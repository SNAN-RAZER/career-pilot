from app.application.application_service import (
    ApplicationService,
)
from app.application.company_apply import (
    naukri_listing_url,
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

        if application.status == "PENDING":
            if application.tailored_resume is None:
                next_action = "TAILOR"
            else:
                next_action = "APPLY"
        elif application.status == "APPLIED":
            next_action = "WAIT"
        elif application.status == "INTERVIEW":
            next_action = "FOLLOW_UP"
        elif application.status == "OFFER":
            next_action = "NEGOTIATE"
        else:
            next_action = "CLOSED"

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
            ats_score=(
                application.ats.score
                if application.ats
                else None
            ),
            ats_passed=(
                application.ats.passed
                if application.ats
                else None
            ),
            resume_path=application.resume_path,
            tailored_summary=(
                application.tailored_resume.summary
                if application.tailored_resume
                else None
            ),
            tailored_skills=(
                application.tailored_resume.skills
                if application.tailored_resume
                else []
            ),
            source=job.source,
            url=naukri_listing_url(job),
            applied_via=application.applied_via,
            apply_message=(
                application.apply_message
            ),
        )