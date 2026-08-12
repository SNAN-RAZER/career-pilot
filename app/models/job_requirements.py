from typing import List, Optional

from pydantic import BaseModel, Field


class JobRequirement(BaseModel):
    requirement: str

    category: str

    mandatory: bool = True

    minimum_years: Optional[float] = None

    maximum_years: Optional[float] = None


class JobRequirements(BaseModel):
    required_skills: List[JobRequirement] = Field(
        default_factory=list
    )

    preferred_skills: List[JobRequirement] = Field(
        default_factory=list
    )

    domains: List[str] = Field(
        default_factory=list
    )

    required_experience_years: Optional[float] = None

    maximum_experience_years: Optional[float] = None

    education_requirements: List[str] = Field(
        default_factory=list
    )

    certifications: List[str] = Field(
        default_factory=list
    )

    hard_requirements: List[str] = Field(
        default_factory=list
    )

    role_type: Optional[str] = None