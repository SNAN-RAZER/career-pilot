from pydantic import BaseModel, Field


class ResumeExperienceBlock(BaseModel):

    company: str
    role: str
    dates: str = ""
    tools: str = ""
    bullets: list[str] = Field(
        default_factory=list
    )


class TailoredResume(BaseModel):

    summary: str

    skills: list[str] = Field(
        default_factory=list
    )

    experiences: list[ResumeExperienceBlock] = Field(
        default_factory=list
    )

    experience_highlights: list[str] = Field(
        default_factory=list
    )

    project_highlights: list[str] = Field(
        default_factory=list
    )

    competencies: list[str] = Field(
        default_factory=list
    )

    grounded: bool = True

    warnings: list[str] = Field(
        default_factory=list
    )


class ATSResult(BaseModel):

    score: float

    matched_keywords: list[str] = Field(
        default_factory=list
    )

    missing_keywords: list[str] = Field(
        default_factory=list
    )

    passed: bool = False

    issues: list[str] = Field(
        default_factory=list
    )


class ResumePackage(BaseModel):

    resume: TailoredResume

    ats: ATSResult

    resume_path: str | None = None
