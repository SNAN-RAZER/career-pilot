from datetime import datetime, UTC
from pydantic import BaseModel, Field

from app.models.job import JobPosting


class ApplicationRecord(BaseModel):

    job: JobPosting

    status: str = "PENDING"

    match_score: float

    eligibility_score: float

    recommendation: str

    missing_requirements: list[str] = Field(
        default_factory=list
    )

    reasons: list[str] = Field(
        default_factory=list
    )

    notes: list[str] = Field(
        default_factory=list
    )

    created_at: datetime = Field(
    default_factory=lambda: datetime.now(UTC)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )