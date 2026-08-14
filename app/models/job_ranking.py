from pydantic import BaseModel, Field


class JobRanking(BaseModel):
    rank: int

    job_id: str = ""

    title: str

    company: str

    location: str | None = None

    score: float

    recommendation: str

    missing_requirements: list[str] = Field(
        default_factory=list
    )

    reasons: list[str] = Field(
        default_factory=list
    )