import json
import re

from app.llm.lmstudio_client import LMStudioClient
from app.matching.job_text import strip_job_html
from app.models.job_requirements import (
    JobRequirement,
    JobRequirements,
)


FAKE_SKILL_RE = re.compile(
    r"^(extract_|parse_|get_|format_|job_description$"
    r"|parameters$|resume_text$)",
    re.I,
)


class JobAnalyzer:

    SYSTEM_PROMPT = """
You extract job requirements from job descriptions.

Be factual and conservative.

Extract:

1. Required technical skills.
2. Preferred technical skills.
3. Domains.
4. Minimum experience years.
5. Maximum experience years.
6. Education requirements.
7. Certifications.
8. Hard requirements.
9. Role type.

Rules:

- Only extract information explicitly present.
- Do not invent technologies.
- A technology listed under Required is required.
- A technology listed under Preferred, Nice to Have,
  Advantage, or Bonus is preferred.
- Keep skill names short and standardized.
- Examples:
  "Strong Python programming experience" -> "Python"
  "Experience with Large Language Models" -> "LLM"
  "experience building RAG applications" -> "RAG"
  "vector databases" -> "Vector Databases"
- Do not put explanations inside skill names.
- Do not return HTML, tool names, or field names
  such as extract_requirements or job_description.
- Return only JSON.
"""

    RESPONSE_SCHEMA = {
        "name": "job_requirements",
        "schema": {
            "type": "object",
            "properties": {
                "required_skills": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "preferred_skills": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "domains": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "required_experience_years": {
                    "type": [
                        "number",
                        "null"
                    ]
                },
                "maximum_experience_years": {
                    "type": [
                        "number",
                        "null"
                    ]
                },
                "education_requirements": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "certifications": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "hard_requirements": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "role_type": {
                    "type": [
                        "string",
                        "null"
                    ]
                }
            },
            "required": [
                "required_skills",
                "preferred_skills",
                "domains",
                "required_experience_years",
                "maximum_experience_years",
                "education_requirements",
                "certifications",
                "hard_requirements",
                "role_type"
            ],
            "additionalProperties": False
        }
    }

    def __init__(
        self,
        client: LMStudioClient | None = None
    ):
        self.client = client or LMStudioClient()

    def analyze(
        self,
        job_description: str
    ) -> JobRequirements:

        if not job_description.strip():
            raise ValueError(
                "Job description cannot be empty."
            )

        cleaned = strip_job_html(job_description)[:8000]
        last = None

        for attempt in (1, 2):
            extra = ""

            if attempt == 2:
                extra = (
                    "\nReturn skill names only "
                    "(Python, .NET, React). "
                    "Never return HTML or tool names.\n"
                )

            response = self.client.chat(
                messages=[
                    {
                        "role": "system",
                        "content": self.SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": (
                            "Extract the requirements from "
                            "the following job description.\n\n"
                            f"{cleaned}"
                            f"{extra}"
                        )
                    }
                ],
                temperature=0.0,
                response_schema=self.RESPONSE_SCHEMA
            )

            data = self._parse_json(response)

            if data is None:
                continue

            last = self._build_requirements(data)

            if last.required_skills:
                return last

        if last is not None:
            return last

        raise ValueError(
            "Could not extract job requirements."
        )

    @staticmethod
    def _build_requirements(
        data: dict
    ) -> JobRequirements:

        required_skills = [
            JobRequirement(
                requirement=skill,
                category="technical_skill",
                mandatory=True,
            )
            for skill in JobAnalyzer._clean_skills(
                data.get("required_skills", [])
            )
        ]

        preferred_skills = [
            JobRequirement(
                requirement=skill,
                category="technical_skill",
                mandatory=False,
            )
            for skill in JobAnalyzer._clean_skills(
                data.get("preferred_skills", [])
            )
        ]

        return JobRequirements(
            required_skills=required_skills,
            preferred_skills=preferred_skills,

            domains=data.get(
                "domains",
                []
            ),

            required_experience_years=data.get(
                "required_experience_years"
            ),

            maximum_experience_years=data.get(
                "maximum_experience_years"
            ),

            education_requirements=data.get(
                "education_requirements",
                []
            ),

            certifications=data.get(
                "certifications",
                []
            ),

            hard_requirements=data.get(
                "hard_requirements",
                []
            ),

            role_type=data.get(
                "role_type"
            )
        )

    @staticmethod
    def _clean_skills(raw) -> list[str]:

        if isinstance(raw, str):
            raw = [raw]

        if isinstance(raw, dict):
            raw = list(raw.keys())

        skills = []

        for item in raw or []:
            if isinstance(item, dict):
                item = (
                    item.get("name")
                    or item.get("skill")
                    or ""
                )

            if not isinstance(item, str):
                continue

            skill = re.sub(
                r"\s+",
                " ",
                item,
            ).strip()
            skill = skill.strip(" ;,")

            if JobAnalyzer._is_bad_skill(skill):
                continue

            skills.append(skill)

        return list(dict.fromkeys(skills))

    @staticmethod
    def _is_bad_skill(skill: str) -> bool:

        text = (skill or "").strip()

        if not text or len(text) > 48:
            return True

        if "<" in text or ">" in text:
            return True

        if FAKE_SKILL_RE.match(text):
            return True

        lowered = text.lower()

        return lowered in {
            "na",
            "n/a",
            "none",
            "job_description",
            "job description",
        }

    @staticmethod
    def _parse_json(raw: str) -> dict | None:

        if not raw or not raw.strip():
            return None

        text = re.sub(
            r"^\s*```(?:json)?\s*",
            "",
            raw.strip(),
            flags=re.I,
        )
        text = re.sub(r"\s*```\s*$", "", text).strip()

        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            loaded = None

            for match in re.finditer(r"\{", text):
                try:
                    loaded, _ = decoder.raw_decode(
                        text[match.start():]
                    )
                    break
                except json.JSONDecodeError:
                    continue

        if not isinstance(loaded, dict):
            return None

        name = str(loaded.get("name") or "")

        if (
            "parameters" in loaded
            or "job_description" in loaded
            or name.startswith("extract_")
        ):
            return None

        return loaded

