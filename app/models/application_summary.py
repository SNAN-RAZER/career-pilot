from pydantic import BaseModel


class ApplicationSummary(BaseModel):

    job_id: str
    title: str
    company: str
    location: str

    status: str

    match_score: float
    eligibility_score: float

    recommendation: str

    missing_requirements: list[str]
    reasons: list[str]

    notes_count: int

    next_action: str