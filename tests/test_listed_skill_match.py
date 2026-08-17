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


def test_grouped_skill_line_covers_c():

    from app.resume.skill_match import skill_matches_keyword

    listed = (
        "Programming: Python, Embedded C, C, Ada 95"
    )

    assert skill_matches_keyword("C", listed)
    assert skill_matches_keyword("Python", listed)
    assert not skill_matches_keyword("Java", listed)


def test_jd_filler_words_are_not_claimable_from_category_lines():

    from app.resume.allowed_facts import AllowedFacts
    from app.resume.keyword_coverage import claimable_keywords

    candidate = CandidateProfile(
        name="Nayaab",
        skills=[
            "Programming: Python, Embedded C, C",
            "Professional Strengths: High-Quality Delivery",
        ],
    )
    facts = AllowedFacts(candidate)

    assert facts.allows_skill("Python") is True
    assert facts.allows_skill("closely") is False
    assert facts.allows_skill("high") is False
    assert facts.allows_skill("delivery") is False

    claimable = claimable_keywords(
        candidate,
        "Diagnostics Software Engineer",
        "Work closely with successful manufacturing centers.",
    )
    lowered = [item.lower() for item in claimable]
    assert "closely" not in lowered
    assert "successful" not in lowered


def test_semantic_matcher_falls_back_without_embeddings():

    from app.matching.semantic_matcher import SemanticMatcher

    class Boom:
        def embed(self, text):
            raise RuntimeError("no embed")

    matcher = SemanticMatcher(client=Boom())

    assert matcher.similarity("Python", "Python") == 100.0
    assert matcher.similarity("Python", "Java") == 0.0
