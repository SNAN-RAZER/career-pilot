from typing import Literal

from pydantic import BaseModel, Field


class EvidenceJudgment(BaseModel):
    supported: bool

    confidence: float = Field(
        ge=0.0,
        le=1.0
    )

    evidence_strength: Literal[
        "strong",
        "moderate",
        "weak",
        "none"
    ]

    reason: str