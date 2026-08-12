from typing import List

from pydantic import BaseModel, Field


class SkillEvaluation(BaseModel):
    requirement: str

    required: bool

    supported: bool

    evidence_type: str | None = None

    evidence_source: str | None = None

    similarity_score: float = 0.0

    confidence: float = 0.0

    reason: str = ""


class JobEvaluation(BaseModel):
    overall_score: float

    professional_score: float

    project_score: float

    domain_score: float

    experience_score: float

    required_skills: List[SkillEvaluation] = Field(
        default_factory=list
    )

    preferred_skills: List[SkillEvaluation] = Field(
        default_factory=list
    )

    missing_required_skills: List[str] = Field(
        default_factory=list
    )

    matched_required_skills: List[str] = Field(
        default_factory=list
    )

    career_transition_score: float

    recommendation: str

    reasons: List[str] = Field(
        default_factory=list
    )