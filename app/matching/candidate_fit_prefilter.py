import json
import re
from dataclasses import dataclass

from app.llm.lmstudio_client import LMStudioClient
from app.models.candidate import CandidateProfile
from app.models.job import JobPosting
from app.models.target_profile import TargetProfile


@dataclass
class CandidateFitResult:
    matched: bool
    score: float
    matched_skills: list[str]
    reason: str


SCREEN_SCHEMA = {
    "name": "job_fit_screen",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "jobs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "job_id": {"type": "string"},
                        "keep": {"type": "boolean"},
                        "score": {"type": "number"},
                        "overlapping_skills": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "reason": {"type": "string"},
                    },
                    "required": [
                        "job_id",
                        "keep",
                        "score",
                        "overlapping_skills",
                        "reason",
                    ],
                },
            }
        },
        "required": ["jobs"],
    },
}


class CandidateFitPreFilter:

    BATCH_SIZE = 8

    def __init__(
        self,
        llm: LMStudioClient | None = None,
        screen=None,
    ):
        self.llm = llm or LMStudioClient()
        self._screen = screen

    def match(
        self,
        candidate: CandidateProfile,
        job: JobPosting,
        queries: list[str] | None = None,
        target_profile: TargetProfile | None = None,
    ) -> CandidateFitResult:

        results = self.screen(
            candidate,
            [job],
            queries=queries,
            target_profile=target_profile,
        )

        return results.get(
            job.job_id,
            CandidateFitResult(
                matched=True,
                score=50.0,
                matched_skills=[],
                reason="Screen did not return this job.",
            ),
        )

    def screen(
        self,
        candidate: CandidateProfile,
        jobs: list[JobPosting],
        queries: list[str] | None = None,
        target_profile: TargetProfile | None = None,
    ) -> dict[str, CandidateFitResult]:

        if self._screen is not None:
            return self._screen(
                candidate,
                jobs,
                queries=queries,
                target_profile=target_profile,
            )

        if not jobs:
            return {}

        if not str(self.llm.llm_model or "").strip():
            return self._query_title_fallback(
                jobs,
                queries or [],
                "No chat model selected; keeping query-title matches only.",
            )

        if not self.llm.reachable():
            return self._query_title_fallback(
                jobs,
                queries or [],
                "LLM host unreachable; keeping query-title matches only.",
            )

        profile_text = self._profile_text(
            candidate,
            target_profile,
        )
        merged: dict[str, CandidateFitResult] = {}

        for start in range(0, len(jobs), self.BATCH_SIZE):
            batch = jobs[start:start + self.BATCH_SIZE]
            merged.update(
                self._ask_batch(
                    profile_text,
                    queries or [],
                    batch,
                )
            )

        for job in jobs:
            if job.job_id not in merged:
                merged[job.job_id] = CandidateFitResult(
                    matched=False,
                    score=0.0,
                    matched_skills=[],
                    reason=(
                        "Model omitted this job; "
                        "not keeping it."
                    ),
                )

        return merged

    def _ask_batch(
        self,
        profile_text: str,
        queries: list[str],
        jobs: list[JobPosting],
    ) -> dict[str, CandidateFitResult]:

        payload = []

        for job in jobs:
            payload.append(
                {
                    "job_id": job.job_id,
                    "title": job.title,
                    "company": job.company,
                    "description": (job.description or "")[:2500],
                }
            )

        try:
            raw = self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": self._prompt(),
                    },
                    {
                        "role": "user",
                        "content": (
                            "CANDIDATE PROFILE:\n"
                            f"{profile_text}\n\n"
                            "SEARCH QUERIES:\n"
                            + (
                                "\n".join(queries)
                                if queries
                                else "(none)"
                            )
                            + "\n\nJOBS:\n"
                            + json.dumps(
                                payload,
                                ensure_ascii=False,
                            )
                            + "\n\nReturn JSON only."
                        ),
                    },
                ],
                temperature=0,
                max_tokens=4000,
                response_schema=SCREEN_SCHEMA,
            )
        except Exception as exc:
            return self._query_title_fallback(
                jobs,
                queries,
                f"Fit screen failed ({exc}); "
                "keeping query-title matches only.",
            )

        parsed = self._parse_json(raw)
        rows = []

        if isinstance(parsed, dict):
            rows = parsed.get("jobs") or []
        elif isinstance(parsed, list):
            rows = parsed

        by_id = {
            str(row.get("job_id")): row
            for row in rows
            if isinstance(row, dict) and row.get("job_id")
        }

        results = {}

        for job in jobs:
            row = by_id.get(job.job_id)

            if not row:
                results[job.job_id] = CandidateFitResult(
                    matched=False,
                    score=0.0,
                    matched_skills=[],
                    reason=(
                        "Model omitted this job; "
                        "not keeping it."
                    ),
                )
                continue

            skills = self._ground_skills(
                row.get("overlapping_skills") or [],
                profile_text,
            )

            results[job.job_id] = CandidateFitResult(
                matched=bool(row.get("keep")) and bool(skills),
                score=float(row.get("score") or 0),
                matched_skills=skills,
                reason=str(
                    row.get("reason")
                    or "Model screened this job."
                ),
            )

        return results

    @staticmethod
    def _prompt() -> str:

        return """
You screen jobs for one candidate before a deeper review.

Read the candidate profile as written. Skill lines may be
grouped (for example "Programming: Python, C"). Treat
tools and languages named inside those lines as listed
skills. Do not invent skills, jobs, or employers.

Keep a job only when:
- the search queries, if any, describe the job's
  actual work (in the title or as a primary skill),
  not a passing mention among many unrelated
  technologies
- it is not an excluded role
- there is real overlap with the candidate's listed
  skills, paid work, or projects

Reject laundry-list full-stack roles that only
mention the query once. Related-sounding titles
are not enough.

overlapping_skills must be copied from the candidate
profile text. Return JSON only.
""".strip()

    @staticmethod
    def _profile_text(
        candidate: CandidateProfile,
        target_profile: TargetProfile | None,
    ) -> str:

        roles = candidate.target_roles
        excluded = candidate.excluded_roles
        domains = candidate.domains

        if target_profile is not None:
            roles = target_profile.target_roles or roles
            excluded = (
                target_profile.excluded_roles or excluded
            )
            domains = target_profile.target_domains or domains

        jobs = []

        for item in candidate.experiences:
            jobs.append(
                {
                    "company": item.company,
                    "role": item.role,
                    "bullets": item.description[:8],
                }
            )

        projects = []

        for item in candidate.projects:
            projects.append(
                {
                    "name": item.name,
                    "description": (item.description or "")[:1200],
                }
            )

        return json.dumps(
            {
                "name": candidate.name,
                "headline": candidate.headline,
                "summary": candidate.professional_summary,
                "target_roles": roles,
                "excluded_roles": excluded,
                "domains": domains,
                "skills_as_written": candidate.skills,
                "experience": jobs,
                "projects": projects,
            },
            ensure_ascii=False,
            indent=2,
        )

    @staticmethod
    def _ground_skills(
        skills: list,
        profile_text: str,
    ) -> list[str]:

        haystack = profile_text.lower()
        grounded = []

        for item in skills:
            skill = str(item or "").strip()

            if skill and skill.lower() in haystack:
                grounded.append(skill)

        return grounded

    @staticmethod
    def _query_title_fallback(
        jobs: list[JobPosting],
        queries: list[str],
        reason: str,
    ) -> dict[str, CandidateFitResult]:

        results = {}

        for job in jobs:
            title = (job.title or "").lower()
            keep = False

            for query in queries:
                token = query.lower().strip()

                if token and token in title:
                    keep = True
                    break

            results[job.job_id] = CandidateFitResult(
                matched=keep,
                score=60.0 if keep else 0.0,
                matched_skills=[],
                reason=reason,
            )

        return results

    @staticmethod
    def _pass_through(
        jobs: list[JobPosting],
        reason: str,
    ) -> dict[str, CandidateFitResult]:

        return {
            job.job_id: CandidateFitResult(
                matched=True,
                score=50.0,
                matched_skills=[],
                reason=reason,
            )
            for job in jobs
        }

    @staticmethod
    def _parse_json(raw: str) -> dict | list | None:

        text = (raw or "").strip()

        if not text:
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(
            r"\{.*\}|\[.*\]",
            text,
            re.S,
        )

        if not match:
            return None

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
