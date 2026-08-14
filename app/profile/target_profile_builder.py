from app.models.candidate import CandidateProfile
from app.models.target_profile import TargetProfile


DEFAULT_EXCLUDED_ROLES = [
    "AI Research Scientist",
    "Research Scientist",
    "Machine Learning Researcher",
]


def build_target_profile(
    candidate: CandidateProfile,
) -> TargetProfile:

    excluded_roles = (
        candidate.excluded_roles
        or DEFAULT_EXCLUDED_ROLES
    )

    return TargetProfile(
        target_roles=candidate.target_roles,
        target_domains=candidate.domains,
        preferred_locations=(
            candidate.preferred_locations
        ),
        excluded_roles=excluded_roles,
        minimum_match_score=70.0,
        auto_apply_score=85.0,
        allow_project_based_transition=True,
        require_professional_experience=False,
        max_experience_years=5.0,
    )
