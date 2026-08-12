from app.models.job import JobPosting
from app.models.target_profile import TargetProfile


class TargetMatchResult:
    def __init__(
        self,
        matched: bool,
        score: float,
        reason: str,
    ):
        self.matched = matched
        self.score = score
        self.reason = reason


class TargetMatcher:

    def match(
        self,
        job: JobPosting,
        profile: TargetProfile,
    ) -> TargetMatchResult:

        title = job.title.lower()

        # -----------------------------------------
        # Excluded roles
        # -----------------------------------------

        for excluded in profile.excluded_roles:

            if excluded.lower() in title:

                return TargetMatchResult(
                    matched=False,
                    score=0.0,
                    reason=(
                        f"Role matches excluded "
                        f"title: {excluded}"
                    ),
                )

        # -----------------------------------------
        # Target roles
        # -----------------------------------------

        role_matches = []

        for role in profile.target_roles:

            if role.lower() in title:
                role_matches.append(role)

        if role_matches:

            return TargetMatchResult(
                matched=True,
                score=100.0,
                reason=(
                    "Job title matches target role: "
                    + ", ".join(role_matches)
                ),
            )

        # -----------------------------------------
        # Domain fallback
        # -----------------------------------------

        description = (
            job.description.lower()
        )

        domain_matches = []

        for domain in profile.target_domains:

            if domain.lower() in description:

                domain_matches.append(domain)

        if domain_matches:

            return TargetMatchResult(
                matched=True,
                score=70.0,
                reason=(
                    "Job description matches "
                    "target domain: "
                    + ", ".join(domain_matches)
                ),
            )

        return TargetMatchResult(
            matched=False,
            score=0.0,
            reason=(
                "Job does not match the configured "
                "target roles or domains."
            ),
        )