from enum import Enum

from pydantic import BaseModel


class SkillRelation(str, Enum):
    EXACT = "exact"
    CATEGORY = "category"
    SPECIALIZATION = "specialization"
    RELATED = "related"


class SkillMapping(BaseModel):
    candidate_skill: str
    job_requirement: str

    relation: SkillRelation

    confidence: float

    explanation: str