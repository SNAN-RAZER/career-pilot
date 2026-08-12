from pydantic import BaseModel


class JobRanking(BaseModel):
    rank: int

    title: str

    company: str

    score: float

    recommendation: str

    missing_requirements: list[str]

    reasons: list[str]