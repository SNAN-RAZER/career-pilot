from app.matching.job_ranker import JobRanker
from app.models.job_evaluation import (
    JobEvaluation,
    SkillEvaluation,
)


def make_evaluation(
    overall_score,
    required_matches,
    required_total,
    professional_score,
    project_score,
    domain_score,
    experience_score,
    preferred_matches,
    preferred_total,
):

    required = [
        SkillEvaluation(
            requirement=f"Skill {i}",
            required=True,
            supported=i < required_matches,
        )
        for i in range(
            required_total
        )
    ]

    preferred = [
        SkillEvaluation(
            requirement=f"Preferred {i}",
            required=False,
            supported=i < preferred_matches,
        )
        for i in range(
            preferred_total
        )
    ]

    return JobEvaluation(
        overall_score=overall_score,

        professional_score=professional_score,

        project_score=project_score,

        domain_score=domain_score,

        experience_score=experience_score,

        required_skills=required,

        preferred_skills=preferred,

        missing_required_skills=[
            item.requirement
            for item in required
            if not item.supported
        ],

        matched_required_skills=[
            item.requirement
            for item in required
            if item.supported
        ],

        career_transition_score=project_score,

        recommendation=(
            "APPLY"
            if required_matches == required_total
            else "REVIEW"
        ),

        reasons=[],
    )


def test_job_ranker():

    strong_job = make_evaluation(
        overall_score=90,
        required_matches=5,
        required_total=5,
        professional_score=90,
        project_score=90,
        domain_score=100,
        experience_score=100,
        preferred_matches=2,
        preferred_total=2,
    )

    weaker_job = make_evaluation(
        overall_score=60,
        required_matches=3,
        required_total=5,
        professional_score=40,
        project_score=70,
        domain_score=80,
        experience_score=100,
        preferred_matches=1,
        preferred_total=2,
    )

    ranker = JobRanker()

    results = ranker.rank(
        [
            (
                "ML Engineer",
                "Company B",
                weaker_job,
            ),
            (
                "AI Engineer",
                "Company A",
                strong_job,
            ),
        ]
    )

    assert len(results) == 2

    assert results[0].title == (
        "AI Engineer"
    )

    assert results[0].rank == 1

    assert results[1].rank == 2

    assert (
        results[0].score
        > results[1].score
    )