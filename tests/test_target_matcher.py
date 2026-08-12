from app.matching.target_matcher import (
    TargetMatcher,
)
from app.models.job import JobPosting
from app.models.target_profile import (
    TargetProfile,
)


def make_job(title, description=""):

    return JobPosting(
        job_id="1",
        title=title,
        company="Test Company",
        description=description,
        source="test",
    )


def make_profile():

    return TargetProfile(
        target_roles=[
            "AI Engineer",
            "Generative AI Engineer",
            "RAG Engineer",
        ],

        excluded_roles=[
            "ML Research Scientist",
        ],

        target_domains=[
            "AI",
            "Generative AI",
            "RAG",
        ],
    )


def test_target_ai_engineer():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job("AI Engineer"),
        make_profile(),
    )

    assert result.matched is True
    assert result.score == 100.0


def test_target_rag_engineer():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job("RAG Engineer"),
        make_profile(),
    )

    assert result.matched is True


def test_excluded_research_role():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job(
            "ML Research Scientist"
        ),
        make_profile(),
    )

    assert result.matched is False
    assert result.score == 0.0


def test_ai_domain_fallback():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job(
            "Software Engineer",
            "Build AI and RAG applications."
        ),
        make_profile(),
    )

    assert result.matched is True
    assert result.score == 70.0