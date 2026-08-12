from typing import List

from pydantic import BaseModel


class MatchResult(BaseModel):
    job_id: str
    job_title: str

    overall_score: float

    skill_score: float
    experience_score: float
    domain_score: float
    role_score: float

    matched_skills: List[str]
    missing_required_skills: List[str]

    matched_domains: List[str]

    recommendation: str

    reasons: List[str]