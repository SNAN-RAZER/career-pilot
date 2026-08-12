from enum import Enum

from pydantic import BaseModel

from app.llm.lmstudio_client import LMStudioClient
from app.models.evidence import (
    EvidenceType,
    SkillEvidence,
)
from app.matching.semantic_matcher import (
    SemanticMatcher,
)


class RequirementMatchType(str, Enum):
    EXACT = "exact"
    SEMANTIC = "semantic"
    PARTIAL = "partial"
    MISSING = "missing"


class RequirementMatch(BaseModel):
    requirement: str

    match_type: RequirementMatchType

    similarity_score: float

    evidence_type: str | None = None

    evidence_source: str | None = None

    evidence: str | None = None


class RequirementMatcher:

    def __init__(
        self,
        semantic_matcher: SemanticMatcher | None = None,
    ):

        self.semantic_matcher = (
            semantic_matcher
            or SemanticMatcher()
        )

    def match(
        self,
        requirement: str,
        evidence: list[SkillEvidence],
    ) -> RequirementMatch:

        requirement_normalized = (
            requirement.strip().lower()
        )

        # First: exact matching
        for item in evidence:

            skill_normalized = (
                item.skill.strip().lower()
            )

            if (
                requirement_normalized
                == skill_normalized
            ):

                return RequirementMatch(
                    requirement=requirement,
                    match_type=RequirementMatchType.EXACT,
                    similarity_score=100.0,
                    evidence_type=(
                        item.evidence_type.value
                    ),
                    evidence_source=item.source,
                    evidence=item.description,
                )

        # Second: semantic matching
        best_match = None
        best_score = 0.0

        for item in evidence:

            score = (
                self.semantic_matcher.similarity(
                    requirement,
                    item.skill,
                )
            )

            if score > best_score:

                best_score = score
                best_match = item

        # Conservative threshold.
        #
        # We deliberately don't use 70 because
        # our earlier test showed unrelated concepts
        # can score around 68.

        if best_match and best_score >= 82:

            return RequirementMatch(
                requirement=requirement,
                match_type=RequirementMatchType.SEMANTIC,
                similarity_score=best_score,
                evidence_type=(
                    best_match.evidence_type.value
                ),
                evidence_source=best_match.source,
                evidence=best_match.description,
            )

        return RequirementMatch(
            requirement=requirement,
            match_type=RequirementMatchType.MISSING,
            similarity_score=best_score,
        )