import re

from app.models.job import JobPosting
from app.models.target_profile import TargetProfile


GENERIC_QUERY_WORDS = {
    "the",
    "a",
    "an",
    "job",
    "role",
    "sr",
    "senior",
}

NON_SOFTWARE_TITLE_TERMS = [
    "technician",
    "electrician",
    "mechanic",
    "operator",
    "sales",
    "recruiter",
    "intern",
    "trainee",
    "fresher",
    "customer care",
    "customer support",
    "support executive",
    "care executive",
    "call center",
    "call centre",
    "bpo",
    "voice process",
]

ENGINEERING_TITLE_TERMS = {
    "engineer",
    "developer",
    "firmware",
    "software",
    "programmer",
    "embedded",
    "rtos",
    "avionics",
    "sde",
}


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
        queries: list[str] | None = None,
    ) -> TargetMatchResult:

        title = job.title.lower()

        for term in NON_SOFTWARE_TITLE_TERMS:
            if term in title:
                return TargetMatchResult(
                    matched=False,
                    score=0.0,
                    reason=(
                        f"Title is not a software "
                        f"role: {term}"
                    ),
                )

        for excluded in profile.excluded_roles:
            if self._contains_role(
                title,
                excluded,
            ):
                return TargetMatchResult(
                    matched=False,
                    score=0.0,
                    reason=(
                        f"Role matches excluded "
                        f"title: {excluded}"
                    ),
                )

        if queries:
            if self.matches_queries(job, queries):
                return TargetMatchResult(
                    matched=True,
                    score=90.0,
                    reason=(
                        "Job matches the search query."
                    ),
                )

            return TargetMatchResult(
                matched=False,
                score=0.0,
                reason=(
                    "Job is unrelated to the "
                    "search query."
                ),
            )

        role_matches = [
            role
            for role in profile.target_roles
            if self._contains_role(title, role)
        ]

        if role_matches:
            return TargetMatchResult(
                matched=True,
                score=100.0,
                reason=(
                    "Job title matches target role: "
                    + ", ".join(role_matches)
                ),
            )

        description = job.description.lower()
        role_tokens = {
            token
            for role in profile.target_roles
            for token in re.findall(
                r"[a-z0-9]+",
                role.lower(),
            )
            if token not in GENERIC_QUERY_WORDS
        }
        title_matches_role_token = any(
            self._contains_token(title, token)
            for token in role_tokens
        )

        if title_matches_role_token:
            domain_matches = [
                domain
                for domain in profile.target_domains
                if domain.lower() in description
            ]

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

    @classmethod
    def matches_queries(
        cls,
        job: JobPosting,
        queries: list[str],
    ) -> bool:

        title = job.title.lower()
        text = (
            f"{job.title} {job.description}"
        ).lower()

        for query in queries:
            query = query.lower().strip()

            if not query:
                continue

            if query in title:
                return True

            tokens = [
                token
                for token in re.findall(
                    r"[a-z0-9]+",
                    query,
                )
                if token not in GENERIC_QUERY_WORDS
            ]

            if not tokens:
                continue

            if len(tokens) == 1:
                token = tokens[0]

                if cls._contains_token(title, token):
                    return True

                if len(token) <= 3 and not cls._engineering_title(
                    title
                ):
                    continue

                if cls._contains_token(text, token):
                    return True
                continue

            phrase = r"\b" + r"\s+".join(
                re.escape(token)
                for token in tokens
            ) + r"\b"

            if re.search(phrase, title):
                return True

        return False

    @staticmethod
    def _contains_token(
        text: str,
        token: str,
    ) -> bool:

        pattern = (
            r"\b"
            + re.escape(token)
            + r"(?:\d+)?\b"
        )

        return re.search(pattern, text) is not None

    @staticmethod
    def _engineering_title(title: str) -> bool:

        return any(
            TargetMatcher._contains_token(
                title,
                term,
            )
            for term in ENGINEERING_TITLE_TERMS
        )

    @staticmethod
    def _contains_role(
        title: str,
        role: str,
    ) -> bool:

        pattern = (
            r"\b"
            + re.escape(role.lower())
            + r"\b"
        )

        return re.search(pattern, title) is not None
