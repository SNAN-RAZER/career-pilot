from enum import Enum

from pydantic import BaseModel, Field


class Decision(str, Enum):
    APPLY = "APPLY"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class BlockerType(str, Enum):
    MISSING_REQUIRED_SKILL = "missing_required_skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    DOMAIN = "domain"
    OTHER = "other"


class DecisionBlocker(BaseModel):
    blocker_type: BlockerType

    requirement: str

    severity: str

    explanation: str


class CareerDecision(BaseModel):
    decision: Decision

    match_score: float = Field(
        ge=0,
        le=100,
    )

    eligibility_score: float = Field(
        ge=0,
        le=100,
    )

    career_transition_score: float = Field(
        ge=0,
        le=100,
    )

    blockers: list[DecisionBlocker] = Field(
        default_factory=list
    )

    reasons: list[str] = Field(
        default_factory=list
    )