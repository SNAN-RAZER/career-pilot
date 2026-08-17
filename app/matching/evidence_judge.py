import json

from app.llm.lmstudio_client import LMStudioClient
from app.models.evidence import SkillEvidence
from app.models.evidence_judgment import EvidenceJudgment


class EvidenceJudge:

    SYSTEM_PROMPT = """
You are a strict career evidence verification system.

Your job is to determine whether the candidate evidence
actually supports the job requirement.

Rules:

1. Never assume a skill from a related skill.
2. Never invent experience.
3. Never upgrade project experience into professional experience.
4. Never treat semantic similarity as proof.
5. If the evidence does not explicitly or strongly support
   the requirement, return supported=false.
6. Related technologies are not automatically equivalent.
7. Python experience does not prove TensorFlow, PyTorch,
   Django, FastAPI, or another Python technology.
8. RAG experience does not automatically prove machine
   learning research experience.
9. Professional experience is stronger evidence than
   project experience.
10. Use ONLY the evidence supplied by the application.
11. confidence is a fraction from 0.0 to 1.0.
    Never use a percentage such as 95.
""".strip()

    RESPONSE_SCHEMA = {
        "name": "evidence_judgment",
        "schema": {
            "type": "object",
            "properties": {
                "supported": {
                    "type": "boolean"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "evidence_strength": {
                    "type": "string",
                    "enum": [
                        "strong",
                        "moderate",
                        "weak",
                        "none"
                    ]
                },
                "reason": {
                    "type": "string"
                }
            },
            "required": [
                "supported",
                "confidence",
                "evidence_strength",
                "reason"
            ],
            "additionalProperties": False
        }
    }

    def __init__(
        self,
        client: LMStudioClient | None = None
    ):
        self.client = client or LMStudioClient()

    def judge(
        self,
        requirement: str,
        evidence: SkillEvidence
    ) -> EvidenceJudgment:

        user_prompt = f"""
JOB REQUIREMENT:
{requirement}

CANDIDATE EVIDENCE TYPE:
{evidence.evidence_type.value}

CANDIDATE SKILL:
{evidence.skill}

EVIDENCE TYPE:
{evidence.evidence_type.value}

EVIDENCE SOURCE:
{evidence.source}

EVIDENCE:
{evidence.description}

TECHNOLOGIES:
{", ".join(evidence.technologies)}

DOMAINS:
{", ".join(evidence.domains)}

YEARS:
{
    evidence.years
    if evidence.years is not None
    else "Not specified"
}

Determine whether this evidence genuinely supports
the job requirement.

confidence must be between 0.0 and 1.0, not 0-100.
"""

        response = self.client.chat(
            messages=[
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.0,
            response_schema=self.RESPONSE_SCHEMA,
        )

        return EvidenceJudgment.model_validate(
            EvidenceJudge._parse_json(response)
        )

    @staticmethod
    def _parse_json(raw: str) -> dict:

        text = (raw or "").strip()

        if not text:
            raise ValueError("Empty evidence judgment.")

        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")

            if start < 0 or end <= start:
                raise

            loaded = json.loads(text[start:end + 1])

        if not isinstance(loaded, dict):
            raise ValueError("Evidence judgment was not an object.")

        return loaded