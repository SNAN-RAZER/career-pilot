from pydantic import BaseModel, Field


class TargetProfile(BaseModel):
    target_roles: list[str] = Field(
        default_factory=list
    )

    excluded_roles: list[str] = Field(
        default_factory=list
    )

    target_domains: list[str] = Field(
        default_factory=list
    )

    preferred_locations: list[str] = Field(
        default_factory=list
    )

    minimum_match_score: float = 70.0

    auto_apply_score: float = 85.0

    allow_project_based_transition: bool = True

    require_professional_experience: bool = False

    max_experience_years: float | None = None