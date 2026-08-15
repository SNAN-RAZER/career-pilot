from app.models.candidate import CandidateProfile
from app.models.evidence import (
    EvidenceType,
    SkillEvidence,
)
from app.resume.skill_match import skill_matches_keyword


class EvidenceBuilder:

    def build(
        self,
        candidate: CandidateProfile
    ) -> list[SkillEvidence]:

        evidence = []
        seen: set[tuple[str, str, str]] = set()

        for experience in candidate.experiences:
            blob = " ".join(
                [
                    experience.role or "",
                    *experience.description,
                ]
            )
            technologies = list(
                experience.technologies or []
            )

            for skill in candidate.skills:
                if skill_matches_keyword(skill, blob):
                    technologies.append(skill)

            for technology in dict.fromkeys(technologies):
                self._add(
                    evidence,
                    seen,
                    SkillEvidence(
                        skill=technology,
                        evidence_type=EvidenceType.PROFESSIONAL,
                        source=experience.company,
                        description=(
                            "Professional experience as "
                            f"{experience.role}. "
                            + " ".join(
                                experience.description
                            )
                        ),
                        confidence=1.0,
                        technologies=list(
                            dict.fromkeys(technologies)
                        ),
                        domains=experience.domains,
                    ),
                )

        for project in candidate.projects:
            blob = " ".join(
                [
                    project.name or "",
                    project.description or "",
                ]
            )
            technologies = list(
                project.technologies or []
            )

            for skill in candidate.skills:
                if skill_matches_keyword(skill, blob):
                    technologies.append(skill)

            for technology in dict.fromkeys(technologies):
                self._add(
                    evidence,
                    seen,
                    SkillEvidence(
                        skill=technology,
                        evidence_type=EvidenceType.PROJECT,
                        source=project.name,
                        description=project.description,
                        confidence=0.8,
                        technologies=list(
                            dict.fromkeys(technologies)
                        ),
                        domains=project.domains,
                    ),
                )

        for skill in candidate.skills:
            self._add(
                evidence,
                seen,
                SkillEvidence(
                    skill=skill,
                    evidence_type=EvidenceType.DECLARED,
                    source="candidate.skills",
                    description=(
                        "Listed on the candidate profile: "
                        f"{skill}."
                    ),
                    confidence=0.9,
                    technologies=[skill],
                    domains=candidate.domains,
                ),
            )

        return evidence

    @staticmethod
    def _add(
        evidence: list[SkillEvidence],
        seen: set[tuple[str, str, str]],
        item: SkillEvidence,
    ) -> None:

        key = (
            item.skill.lower(),
            item.evidence_type.value,
            item.source.lower(),
        )

        if key in seen:
            return

        seen.add(key)
        evidence.append(item)
