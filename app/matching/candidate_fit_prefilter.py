from dataclasses import dataclass

from app.models.candidate import CandidateProfile
from app.models.job import JobPosting


@dataclass
class CandidateFitResult:
    matched: bool
    score: float
    matched_skills: list[str]
    reason: str


class CandidateFitPreFilter:

    SKILL_ALIASES = {
        "Python": {
            "python",
        },
        "LLM": {
            "llm",
            "large language model",
            "large language models",
        },
        "RAG": {
            "rag",
            "retrieval augmented generation",
            "retrieval-augmented generation",
        },
        "LangChain": {
            "langchain",
        },
        "Qdrant": {
            "qdrant",
        },
        "Vector Databases": {
            "vector database",
            "vector databases",
            "vector db",
            "vector dbs",
        },
        "Embedded C": {
            "embedded c",
        },
        "C": {
            "c programming",
        },
        "VxWorks": {
            "vxworks",
        },
        "RTOS": {
            "rtos",
            "real time operating system",
            "real-time operating system",
        },
        "Ollama": {
            "ollama",
        },
    }

    AI_SKILLS = {
        "Python",
        "LLM",
        "RAG",
        "LangChain",
        "Qdrant",
        "Vector Databases",
        "Ollama",
    }

    PROFESSIONAL_SKILLS = {
        "Embedded C",
        "C",
        "VxWorks",
        "RTOS",
    }

    def match(
        self,
        candidate: CandidateProfile,
        job: JobPosting,
    ) -> CandidateFitResult:

        candidate_skills = (
            self._candidate_skills(candidate)
        )

        job_text = (
            f"{job.title} "
            f"{job.description}"
        ).lower()

        matched_skills = []

        for skill, aliases in self.SKILL_ALIASES.items():

            if skill.lower() not in candidate_skills:
                continue

            if any(
                alias in job_text
                for alias in aliases
            ):
                matched_skills.append(skill)

        if not matched_skills:

            return CandidateFitResult(
                matched=False,
                score=0.0,
                matched_skills=[],
                reason=(
                    "No meaningful overlap was found "
                    "between the candidate's skills and "
                    "the job."
                ),
            )

        score = self._calculate_score(
            matched_skills
        )

        return CandidateFitResult(
            matched=score >= 50.0,
            score=round(score, 2),
            matched_skills=matched_skills,
            reason=self._build_reason(
                matched_skills,
                score,
            ),
        )

    @staticmethod
    def _candidate_skills(
        candidate: CandidateProfile,
    ) -> set[str]:

        skills = set()

        for skill in candidate.skills:

            skills.add(
                skill.lower().strip()
            )

        for experience in candidate.experiences:

            for technology in (
                experience.technologies
            ):
                skills.add(
                    technology.lower().strip()
                )

        for project in candidate.projects:

            for technology in (
                project.technologies
            ):
                skills.add(
                    technology.lower().strip()
                )

        return skills

    @classmethod
    def _calculate_score(
        cls,
        matched_skills: list[str],
    ) -> float:

        ai_matches = sum(
            1
            for skill in matched_skills
            if skill in cls.AI_SKILLS
        )

        professional_matches = sum(
            1
            for skill in matched_skills
            if skill in cls.PROFESSIONAL_SKILLS
        )

        # -----------------------------------------
        # AI / transition evidence
        # -----------------------------------------

        ai_score = min(
            ai_matches * 25,
            75,
        )

        # -----------------------------------------
        # Direct professional engineering evidence
        # -----------------------------------------

        professional_score = min(
            professional_matches * 20,
            60,
        )

        score = max(
            ai_score,
            professional_score,
        )

        # Strong mixed profile:
        #
        # Example:
        # Python + RAG + VxWorks
        #
        # This is especially valuable for the
        # candidate's transition into AI engineering.
        if (
            ai_matches >= 2
            and professional_matches >= 1
        ):
            score = max(
                score,
                80,
            )

        # Strong direct overlap.
        if ai_matches >= 3:
            score = max(
                score,
                75,
            )

        if professional_matches >= 3:
            score = max(
                score,
                80,
            )

        return min(
            score,
            100,
        )

    @staticmethod
    def _build_reason(
        matched_skills: list[str],
        score: float,
    ) -> str:

        skills = ", ".join(
            matched_skills
        )

        if score >= 70:

            return (
                "Strong candidate/job skill overlap: "
                f"{skills}."
            )

        if score >= 50:

            return (
                "Moderate candidate/job skill overlap: "
                f"{skills}."
            )

        return (
            "Limited candidate/job skill overlap: "
            f"{skills}."
        )