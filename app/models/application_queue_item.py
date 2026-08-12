from pydantic import BaseModel, Field

from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.models.application_record import (
    ApplicationRecord,
)


class ApplicationQueueItem(BaseModel):

    recommendation: ApplicationRecommendation

    status: str = "PENDING"

    priority: str = "NORMAL"

    notes: list[str] = Field(
        default_factory=list
    )

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
        )