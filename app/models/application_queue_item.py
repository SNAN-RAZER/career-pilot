from pydantic import BaseModel, Field

from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.models.application_record import (
    ApplicationRecord,
)
from app.models.tailored_resume import (
    ATSResult,
    TailoredResume,
)


class ApplicationQueueItem(BaseModel):

    recommendation: ApplicationRecommendation

    status: str = "PENDING"

    priority: str = "NORMAL"

    notes: list[str] = Field(
        default_factory=list
    )

    tailored_resume: TailoredResume | None = None

    ats: ATSResult | None = None

    resume_path: str | None = None

    applied_via: str | None = None

    apply_message: str | None = None

    def to_application_record(
        self,
    ) -> ApplicationRecord:

        return ApplicationRecord(
            job=self.recommendation.job,
            status=self.status,
            match_score=(
                self.recommendation.match_score
            ),
            eligibility_score=(
                self.recommendation.eligibility_score
            ),
            recommendation=(
                self.recommendation.recommendation
            ),
            missing_requirements=(
                self.recommendation.missing_requirements
            ),
            reasons=(
                self.recommendation.reasons
            ),
            notes=list(self.notes),
            tailored_resume=self.tailored_resume,
            ats=self.ats,
            resume_path=self.resume_path,
            applied_via=self.applied_via,
            apply_message=self.apply_message,
        )