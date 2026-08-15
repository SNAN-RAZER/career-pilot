import re

from app.models.skill import (
    SkillMapping,
    SkillRelation,
)


class SkillOntology:

    # Candidate technology → broader concepts
    #
    # These relationships are intentionally one-way.
    SPECIALIZATIONS = {

        "qdrant": [
            "vector database",
            "vector databases",
        ],

        "chroma": [
            "vector database",
            "vector databases",
        ],

        "pinecone": [
            "vector database",
            "vector databases",
        ],

        "weaviate": [
            "vector database",
            "vector databases",
        ],

        "faiss": [
            "vector database",
            "vector databases",
            "vector search",
        ],

        "fastapi": [
            "rest api",
            "rest apis",
            "api development",
        ],

        "flask": [
            "rest api",
            "rest apis",
            "api development",
        ],

        "django rest framework": [
            "rest api",
            "rest apis",
            "api development",
        ],

        "express": [
            "rest api",
            "rest apis",
            "api development",
        ],

        "express.js": [
            "rest api",
            "rest apis",
            "api development",
        ],

        "vxworks": [
            "rtos",
            "real time operating system",
            "real-time operating system",
        ],

        "freertos": [
            "rtos",
            "real time operating system",
            "real-time operating system",
        ],

        "rtx": [
            "rtos",
            "real time operating system",
        ],

        "llm applications": [
            "llm",
        ],

        "retrieval augmented generation": [
            "rag",
        ],

        "python automation": [
            "python",
        ],
    }

    @classmethod
    def normalize(
        cls,
        skill: str,
    ) -> str:

        text = (
            skill
            .strip()
            .lower()
            .replace("-", " ")
        )
        return re.sub(
            r"\s+\d+(?:\.\d+)*$",
            "",
            text,
        ).strip()

    @classmethod
    def match(
        cls,
        candidate_skill: str,
        job_requirement: str,
    ) -> SkillMapping | None:

        candidate = cls.normalize(
            candidate_skill
        )

        requirement = cls.normalize(
            job_requirement
        )

        # Exact
        if candidate == requirement:

            return SkillMapping(
                candidate_skill=candidate_skill,
                job_requirement=job_requirement,
                relation=SkillRelation.EXACT,
                confidence=1.0,
                explanation=(
                    "Candidate skill exactly matches "
                    "the job requirement."
                ),
            )

        # Candidate specialization → broader job category
        specializations = cls.SPECIALIZATIONS.get(
            candidate,
            []
        )

        if requirement in specializations:

            return SkillMapping(
                candidate_skill=candidate_skill,
                job_requirement=job_requirement,
                relation=SkillRelation.SPECIALIZATION,
                confidence=0.95,
                explanation=(
                    f"{candidate_skill} is a specific "
                    f"technology belonging to "
                    f"{job_requirement}."
                ),
            )

        return None