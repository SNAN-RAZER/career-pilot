from typing import Set

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.match_result import MatchResult


class JobMatcher:

    APPLY_THRESHOLD = 80
    REVIEW_THRESHOLD = 60

    def match(
        self,
        candidate: CandidateProfile,
        job: Job
    ) -> MatchResult:

        candidate_skills = self._normalize(
            candidate.skills
        )

        required_skills = self._normalize(
            job.required_skills
        )

        preferred_skills = self._normalize(
            job.preferred_skills
        )

        candidate_domains = self._normalize(
            candidate.domains
        )

        job_domains = self._normalize(
            job.domains
        )

        matched_required = (
            candidate_skills & required_skills
        )

        matched_preferred = (
            candidate_skills & preferred_skills
        )

        missing_required = (
            required_skills - candidate_skills
        )

        matched_domains = (
            candidate_domains & job_domains
        )

        skill_score = self._calculate_skill_score(
            required_skills,
            matched_required,
            preferred_skills,
            matched_preferred
        )

        experience_score = self._calculate_experience_score(
            candidate.total_experience_years,
            job.required_experience_years
        )

        domain_score = self._calculate_domain_score(
            candidate_domains,
            job_domains
        )

        role_score = self._calculate_role_score(
            candidate.target_roles,
            job.title
        )

        overall_score = (
            skill_score * 0.45
            + experience_score * 0.20
            + domain_score * 0.20
            + role_score * 0.15
        )

        overall_score = round(
            min(overall_score, 100),
            2
        )

        recommendation = self._recommend(
            overall_score,
            missing_required
        )

        reasons = self._build_reasons(
            matched_required,
            matched_preferred,
            missing_required,
            matched_domains,
            candidate.total_experience_years,
            job.required_experience_years
        )

        return MatchResult(
            job_id=job.job_id,
            job_title=job.title,

            overall_score=overall_score,

            skill_score=round(skill_score, 2),
            experience_score=round(
                experience_score,
                2
            ),
            domain_score=round(
                domain_score,
                2
            ),
            role_score=round(
                role_score,
                2
            ),

            matched_skills=sorted(
                matched_required | matched_preferred
            ),

            missing_required_skills=sorted(
                missing_required
            ),

            matched_domains=sorted(
                matched_domains
            ),

            recommendation=recommendation,

            reasons=reasons
        )

    @staticmethod
    def _normalize(values) -> Set[str]:

        return {
            value.strip().lower()
            for value in values
            if value and value.strip()
        }

    @staticmethod
    def _calculate_skill_score(
        required_skills,
        matched_required,
        preferred_skills,
        matched_preferred
    ):

        required_score = 100

        if required_skills:
            required_score = (
                len(matched_required)
                / len(required_skills)
            ) * 100

        preferred_score = 0

        if preferred_skills:
            preferred_score = (
                len(matched_preferred)
                / len(preferred_skills)
            ) * 100

        if required_skills and preferred_skills:

            return (
                required_score * 0.75
                + preferred_score * 0.25
            )

        if required_skills:
            return required_score

        if preferred_skills:
            return preferred_score

        return 0

    @staticmethod
    def _calculate_experience_score(
        candidate_years,
        required_years
    ):

        if required_years is None:
            return 100

        if candidate_years >= required_years:
            return 100

        if required_years == 0:
            return 100

        ratio = (
            candidate_years
            / required_years
        )

        return min(
            ratio * 100,
            100
        )

    @staticmethod
    def _calculate_domain_score(
        candidate_domains,
        job_domains
    ):

        if not job_domains:
            return 50

        matched = (
            candidate_domains & job_domains
        )

        return (
            len(matched)
            / len(job_domains)
        ) * 100

    @staticmethod
    def _calculate_role_score(
        target_roles,
        job_title
    ):

        title = job_title.lower()

        for role in target_roles:

            role_words = (
                role.lower()
                .split()
            )

            if all(
                word in title
                for word in role_words
            ):
                return 100

        # Partial role matching
        role_words = set()

        for role in target_roles:
            role_words.update(
                role.lower().split()
            )

        matched_words = [
            word
            for word in role_words
            if word in title
        ]

        if matched_words:
            return 60

        return 20

    def _recommend(
        self,
        score,
        missing_required
    ):

        if missing_required:
            if score >= self.APPLY_THRESHOLD:
                return "REVIEW"

            return "REJECT"

        if score >= self.APPLY_THRESHOLD:
            return "APPLY"

        if score >= self.REVIEW_THRESHOLD:
            return "REVIEW"

        return "REJECT"

    @staticmethod
    def _build_reasons(
        matched_required,
        matched_preferred,
        missing_required,
        matched_domains,
        candidate_years,
        required_years
    ):

        reasons = []

        if matched_required:
            reasons.append(
                "Matches required skills: "
                + ", ".join(
                    sorted(matched_required)
                )
            )

        if matched_preferred:
            reasons.append(
                "Matches preferred skills: "
                + ", ".join(
                    sorted(matched_preferred)
                )
            )

        if matched_domains:
            reasons.append(
                "Matches domains: "
                + ", ".join(
                    sorted(matched_domains)
                )
            )

        if missing_required:
            reasons.append(
                "Missing required skills: "
                + ", ".join(
                    sorted(missing_required)
                )
            )

        if required_years is not None:

            if candidate_years >= required_years:
                reasons.append(
                    "Experience requirement satisfied."
                )
            else:
                reasons.append(
                    f"Candidate has approximately "
                    f"{candidate_years} years, "
                    f"while the job requires "
                    f"{required_years} years."
                )

        return reasons