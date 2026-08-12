from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    PROFESSIONAL = "professional"
    PROJECT = "project"
    EDUCATION = "education"
    CERTIFICATION = "certification"


class SkillEvidence(BaseModel):
    skill: str

    evidence_type: EvidenceType

    source: str

    description: str

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0
    )

    technologies: List[str] = Field(
        default_factory=list
    )

    domains: List[str] = Field(
        default_factory=list
    )

    years: Optional[float] = None