from pydantic import BaseModel, Field


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

    ats_score: float | None = None

    ats_passed: bool | None = None

    resume_path: str | None = None

    tailored_summary: str | None = None

    tailored_skills: list[str] = Field(
        default_factory=list
    )

    source: str | None = None

    url: str | None = None

    applied_via: str | None = None

    apply_message: str | None = None