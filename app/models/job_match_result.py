from pydantic import BaseModel, Field

from app.models.job import JobPosting


class JobMatchResult(BaseModel):

    job: JobPosting

    score: float

    recommendation: str

    missing_requirements: list[str] = Field(
        default_factory=list
    )

    reasons: list[str] = Field(
        default_factory=list
    )