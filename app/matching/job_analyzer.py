import json

from app.llm.lmstudio_client import LMStudioClient
from app.models.job_requirements import (
    JobRequirement,
    JobRequirements,
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
                        f"{job_description}"
                    )
                }
            ],
            temperature=0.0,
            response_schema=self.RESPONSE_SCHEMA
        )

        data = json.loads(response)

        return self._build_requirements(data)

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
            for skill in data.get(
                "required_skills",
                []
            )
        ]

        preferred_skills = [
            JobRequirement(
                requirement=skill,
                category="technical_skill",
                mandatory=False,
            )
            for skill in data.get(
                "preferred_skills",
                []
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