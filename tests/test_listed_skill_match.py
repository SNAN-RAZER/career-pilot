from app.models.candidate import CandidateProfile
from app.matching.job_evaluator import JobEvaluator
from app.matching.job_analyzer import JobAnalyzer
from app.models.job_requirements import (
    JobRequirement,
    JobRequirements,
)


def test_listed_profile_skill_is_not_missing():

    candidate = CandidateProfile(
        name="Nayaab Ahmed N",
        skills=["Python", "RAG", "Docker"],
        experiences=[
            {
                "company": "Cyient",
                "role": "Python Automation Engineer",
                "description": [
                    "Built a Python-based LDRA regression tool."
                ],
                "technologies": [],
            }
        ],
    )

    class StubAnalyzer(JobAnalyzer):
        def analyze(self, job_description: str):
            return JobRequirements(
                required_skills=[
                    JobRequirement(
                        requirement="Python",
                        category="technical_skill",
                        mandatory=True,
                    )
                ]
            )

    result = JobEvaluator(
        analyzer=StubAnalyzer(),
    ).evaluate(
        candidate,
        "Required: Python",
    )

    assert "Python" in result.matched_required_skills
    assert "Python" not in result.missing_required_skills
    assert result.required_skills[0].supported is True
