from typing import List, Optional

from pydantic import BaseModel, Field


class Job(BaseModel):
    job_id: str

    title: str
    company: Optional[str] = None
    location: Optional[str] = None

    description: str = ""

    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)

    required_experience_years: Optional[float] = None

    domains: List[str] = Field(default_factory=list)

    employment_type: Optional[str] = None

    url: Optional[str] = None


class JobPosting(BaseModel):
    job_id: str

    title: str

    company: str

    location: str | None = None

    url: str | None = None

    description: str

    source: str

    posted_date: str | None = None

    salary: str | None = None

    employment_type: str | None = None

    raw_data: dict = Field(
        default_factory=dict
    )



class JobPosting(BaseModel):
    job_id: str

    title: str

    company: str

    location: str | None = None

    url: str | None = None

    description: str

    source: str

    posted_date: str | None = None

    salary: str | None = None

    employment_type: str | None = None

    raw_data: dict = Field(
        default_factory=dict
    )