from app.models.candidate import CandidateProfile
from app.resume.skill_match import skill_atoms


class AllowedFacts:

    def __init__(
        self,
        candidate: CandidateProfile,
    ):
        self.candidate = candidate

        skills = set()

        for skill in candidate.skills:
            skills.add(self.normalize(skill))
            skills.update(skill_atoms(skill))

        for experience in candidate.experiences:
            for item in experience.technologies:
                skills.add(self.normalize(item))
                skills.update(skill_atoms(item))

        for project in candidate.projects:
            for item in project.technologies:
                skills.add(self.normalize(item))
                skills.update(skill_atoms(item))

        self.skills = {item for item in skills if item}

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

        return normalized in self.skills
