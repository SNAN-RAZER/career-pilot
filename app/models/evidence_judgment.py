from typing import Literal

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("confidence", mode="before")
    @classmethod
    def scale_percent_confidence(cls, value):

        if value is None or value == "":
            return 0.0

        number = float(value)

        if number > 1.0:
            number = number / 100.0

        return max(0.0, min(1.0, number))
