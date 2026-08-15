import json
import re
import sys
from pathlib import Path

from app.llm.lmstudio_client import LMStudioClient
from app.models.candidate import CandidateProfile
from app.models.job import JobPosting
from app.models.tailored_resume import TailoredResume
from app.resume.allowed_facts import AllowedFacts
from app.resume.resume_tailor import ResumeTailor
from app.resume.source_document import (
    extract_contact,
    extract_resume_text,
    find_source_resume,
)


def _load_ats_scorer():

    root = (
        Path(__file__).resolve().parents[3]
        / "resume_builder"
    )

    if not root.exists():
        return None

    path = str(root)

    if path not in sys.path:
        sys.path.insert(0, path)

    from validator import ATSScorer

    return ATSScorer()


class ATSResumePipeline:

    def __init__(
        self,
        llm: LMStudioClient | None = None,
        tailor: ResumeTailor | None = None,
    ):
        self.llm = llm or LMStudioClient()
        self.tailor = tailor or ResumeTailor()
        self.scorer = _load_ats_scorer()

    def generate(
        self,
        candidate: CandidateProfile,
        job: JobPosting,
    ) -> TailoredResume:

        resume = self.tailor.tailor(candidate, job)

        if self.scorer is not None:
            scores = self.scorer.validate(
                self._plain_text(candidate, resume),
                self._jd_keywords(job),
            )
            resume.warnings.append(
                "ATS builder score: "
                f"{scores.get('overall_ats_score', 0)}"
            )

        return resume

    def _llm_reachable(self) -> bool:

        try:
            import requests

            response = requests.get(
                f"{self.llm.base_url}/models",
                timeout=0.4,
            )
            return response.ok
        except Exception:
            return False

    @staticmethod
    def _source_text() -> str:

        path = find_source_resume()

        if path is None:
            return ""

        return extract_resume_text(path)

    @staticmethod
    def _facts(
        candidate: CandidateProfile,
        contact: dict[str, str],
    ) -> dict:

        return {
            "name": candidate.name,
            "email": candidate.email or contact.get("email"),
            "phone": candidate.phone or contact.get("phone"),
            "linkedin": contact.get("linkedin", ""),
            "github": contact.get("github", ""),
            "location": (
                candidate.preferred_locations[0]
                if candidate.preferred_locations
                else ""
            ),
            "skills": list(candidate.skills),
            "experience": [
                {
                    "company": item.company,
                    "title": item.role,
                    "start_date": item.start_date,
                    "end_date": item.end_date,
                    "bullets": list(item.description),
                    "technologies": list(
                        item.technologies
                    ),
                }
                for item in candidate.experiences
            ],
            "education": [
                {
                    "degree": item.degree,
                    "institution": item.institution,
                    "year": item.year,
                }
                for item in candidate.education
            ],
        }

    def _llm_summary(
        self,
        facts: dict,
        job: JobPosting,
    ) -> str:

        system = (
            "You are writing a professional resume "
            "summary for a real candidate. Return ONLY "
            "2 or 3 plain sentences. Do not invent skills, "
            "companies, metrics, or experience. Use only "
            "the supplied facts. Tailor toward the job. "
            "Do not return JSON, function calls, "
            "tool names, or a parameters object."
        )
        user = (
            f"Name: {facts.get('name')}\n"
            f"Skills: {', '.join(facts.get('skills') or [])}\n"
            f"Experience: {facts.get('experience')}\n"
            f"Target job title: {job.title}\n"
            f"Job description:\n{job.description}\n"
        )

        raw = self.llm.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        ).strip()

        return self._plain_summary(raw) or ""

    @staticmethod
    def _is_tool_call(text: str) -> bool:

        if not text:
            return False

        stripped = text.strip()

        if re.search(
            r'"name"\s*:\s*"(format_|extract_|parse_|get_)',
            stripped,
        ):
            return True

        if "parameters" not in stripped:
            return False

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", stripped, re.S)

            if not match:
                return "format_resume" in stripped

            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return "format_resume" in stripped

        return (
            isinstance(parsed, dict)
            and "parameters" in parsed
        )

    @classmethod
    def _plain_summary(cls, text: str) -> str | None:

        if not text or cls._is_tool_call(text):
            return None

        cleaned = re.sub(r"\s+", " ", text).strip()

        if cleaned.startswith("{") or cleaned.startswith("["):
            return None

        return cleaned

    def _apply_llm_bullets(
        self,
        resume: TailoredResume,
        facts: dict,
        job: JobPosting,
        candidate: CandidateProfile,
    ) -> None:

        originals = {
            item["company"]: item["bullets"]
            for item in facts.get("experience", [])
        }

        system = (
            "Rewrite the supplied experience bullets "
            "for ATS clarity. Use ONLY the supplied "
            "experience. Never invent technologies, "
            "metrics, or achievements. Return bullet "
            "lines starting with '- '."
        )

        for block in resume.experiences:
            source = originals.get(block.company, [])

            if not source:
                continue

            user = (
                f"Company: {block.company}\n"
                f"Title: {block.role}\n"
                f"Bullets:\n"
                + "\n".join(
                    f"- {bullet}"
                    for bullet in source
                )
                + f"\nTarget job: {job.title}\n"
                f"{job.description}\n"
            )

            raw = self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": system,
                    },
                    {
                        "role": "user",
                        "content": user,
                    },
                ]
            )

            if self._is_tool_call(raw):
                continue

            rewritten = [
                line.lstrip("- ").strip()
                for line in raw.splitlines()
                if line.strip().startswith("-")
            ]

            grounded = [
                line
                for line in rewritten
                if self._bullet_grounded(
                    line,
                    source,
                    candidate,
                )
            ]

            if grounded:
                block.bullets = grounded

    @staticmethod
    def _bullet_grounded(
        line: str,
        originals: list[str],
        candidate: CandidateProfile,
    ) -> bool:

        facts = AllowedFacts(candidate)
        lowered = line.lower()

        for original in originals:
            words = [
                word
                for word in original.lower().split()
                if len(word) > 4
            ]
            overlap = sum(
                1
                for word in words
                if word in lowered
            )

            if words and overlap / len(words) >= 0.35:
                return True

        invented = [
            token
            for token in line.replace(",", " ").split()
            if token[0:1].isupper()
            and len(token) > 2
            and not facts.allows_skill(token)
            and token.lower()
            not in {
                "performed",
                "conducted",
                "developed",
                "authored",
                "collaborated",
                "built",
                "created",
                "analyzed",
            }
        ]

        return not invented

    @staticmethod
    def _grounded(
        text: str,
        candidate: CandidateProfile,
    ) -> bool:

        if ATSResumePipeline._is_tool_call(text):
            return False

        facts = AllowedFacts(candidate)
        corpus = " ".join(
            [
                candidate.professional_summary,
                *candidate.skills,
                *[
                    bullet
                    for item in candidate.experiences
                    for bullet in item.description
                ],
            ]
        ).lower()

        if not corpus:
            return False

        words = [
            word
            for word in text.lower().split()
            if len(word) > 5
        ]

        if not words:
            return False

        hit = sum(1 for word in words if word in corpus)

        return hit / len(words) >= 0.3

    @staticmethod
    def _jd_keywords(job: JobPosting) -> list[str]:

        from app.resume.keyword_extractor import (
            extract_keywords,
        )

        return extract_keywords(
            f"{job.title} {job.description}"
        )[:40]

    @staticmethod
    def _plain_text(
        candidate: CandidateProfile,
        resume: TailoredResume,
    ) -> str:

        parts = [
            candidate.name,
            "SUMMARY",
            resume.summary,
            "TECHNICAL SKILLS",
            ", ".join(resume.skills),
            "WORK EXPERIENCE",
        ]

        for block in resume.experiences:
            parts.append(block.company)
            parts.append(block.role)
            parts.extend(block.bullets)

        if resume.project_highlights:
            parts.append("PROJECTS")
            parts.extend(resume.project_highlights)

        if candidate.education:
            parts.append("EDUCATION")
            for item in candidate.education:
                parts.append(
                    f"{item.degree}, {item.institution}"
                )

        return "\n".join(parts)
