from app.models.candidate import CandidateProfile
from app.resume.skill_match import skill_matches_keyword


class AllowedFacts:

    def __init__(
        self,
        candidate: CandidateProfile,
    ):
        self.candidate = candidate

        skills = {
            self.normalize(skill)
            for skill in candidate.skills
        }

        for experience in candidate.experiences:
            skills.update(
                self.normalize(item)
                for item in experience.technologies
            )

        for project in candidate.projects:
            skills.update(
                self.normalize(item)
                for item in project.technologies
            )

        self.skills = skills

        self.companies = {
            self.normalize(item.company)
            for item in candidate.experiences
        }

        self.roles = {
            self.normalize(item.role)
            for item in candidate.experiences
        }

        self.projects = {
            self.normalize(item.name)
            for item in candidate.projects
        }

        self.institutions = {
            self.normalize(item.institution)
            for item in candidate.education
        }

        self.certifications = {
            self.normalize(item)
            for item in candidate.certifications
        }

    @staticmethod
    def normalize(value: str) -> str:
        return " ".join(value.lower().split())

    def allows_skill(self, skill: str) -> bool:
        normalized = self.normalize(skill)

        if not normalized:
            return False

        if normalized in self.skills:
            return True

        if len(normalized) <= 2:
            return False

        return any(
            skill_matches_keyword(normalized, allowed)
            for allowed in self.skills
            if allowed and len(allowed) > 2
        )
