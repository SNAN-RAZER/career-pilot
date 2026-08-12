from pydantic import BaseModel, Field

from app.models.job import JobPosting


class ApplicationRecommendation(BaseModel):
    job: JobPosting

    match_score: float

    eligibility_score: float

    recommendation: str

    missing_requirements: list[str] = Field(
        default_factory=list
    )

    reasons: list[str] = Field(
        default_factory=list
    )

    next_action: str