from typing import List, Optional
from pydantic import BaseModel, Field


class Experience(BaseModel):
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    description: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str
    description: str
    technologies: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: str
    institution: str
    year: Optional[str] = None


class CandidateProfile(BaseModel):
    name: str

    target_roles: List[str] = Field(default_factory=list)

    total_experience_years: float = 0

    professional_summary: str = ""

    skills: List[str] = Field(default_factory=list)

    domains: List[str] = Field(default_factory=list)

    experiences: List[Experience] = Field(default_factory=list)

    projects: List[Project] = Field(default_factory=list)

    education: List[Education] = Field(default_factory=list)

    certifications: List[str] = Field(default_factory=list)

    preferred_locations: List[str] = Field(default_factory=list)

    remote_preference: Optional[str] = None