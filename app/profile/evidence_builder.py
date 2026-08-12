from app.models.candidate import CandidateProfile
from app.models.evidence import (
    EvidenceType,
    SkillEvidence,
)


class EvidenceBuilder:

    def build(
        self,
        candidate: CandidateProfile
    ) -> list[SkillEvidence]:

        evidence = []

        # Professional experience
        for experience in candidate.experiences:

            for technology in experience.technologies:

                evidence.append(
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
                        technologies=experience.technologies,
                        domains=experience.domains,
                    )
                )

        # Project experience
        for project in candidate.projects:

            for technology in project.technologies:

                evidence.append(
                    SkillEvidence(
                        skill=technology,
                        evidence_type=EvidenceType.PROJECT,
                        source=project.name,
                        description=project.description,
                        confidence=0.8,
                        technologies=project.technologies,
                        domains=project.domains,
                    )
                )

        return evidence