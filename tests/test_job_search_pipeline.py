from app.matching.decision_engine import DecisionEngine
from app.matching.job_ranker import JobRanker
from app.matching.target_matcher import TargetMatcher
from app.models.candidate import CandidateProfile
from app.models.job import JobPosting
from app.models.job_evaluation import (
    JobEvaluation,
    SkillEvaluation,
)
from app.models.target_profile import TargetProfile
from app.pipeline.job_search_pipeline import (
    JobSearchPipeline,
)
from app.sources.job_collector import JobCollector


class FakeSource:

    def search(
        self,
        keyword,
        location,
        page,
        experience,
        job_age,
    ):

        return [
            JobPosting(
                job_id="1",
                title="AI Engineer",
                company="AI Company",
                location="Bangalore",
                description=(
                    "Python, RAG and LLM"
                ),
                source="test",
            ),
            JobPosting(
                job_id="2",
                title="Java Developer",
                company="Java Company",
                location="Bangalore",
                description=(
                    "Java and Spring Boot"
                ),
                source="test",
            ),
        ]


class FakeEvaluator:

    def __init__(self):
        self.calls = []

    def evaluate(
            self,
            candidate,
            job,
        ):

        self.calls.append(
            job.description
            if hasattr(job, "description")
            else job
        )

        return JobEvaluation(
            overall_score=90.0,
            professional_score=80.0,
            project_score=90.0,
            domain_score=100.0,
            experience_score=100.0,

            required_skills=[
                SkillEvaluation(
                    requirement="Python",
                    required=True,
                    supported=True,
                ),
                SkillEvaluation(
                    requirement="RAG",
                    required=True,
                    supported=True,
                ),
            ],

            preferred_skills=[
                SkillEvaluation(
                    requirement="Docker",
                    required=False,
                    supported=True,
                ),
            ],

            missing_required_skills=[],

            matched_required_skills=[
                "Python",
                "RAG",
            ],

            career_transition_score=90.0,

            recommendation="APPLY",

            reasons=[
                "Strong candidate alignment."
            ],
        )


def make_candidate():

    return CandidateProfile(
        name="Test Candidate",
        target_roles=[
            "AI Engineer",
        ],
        total_experience_years=4,
        skills=[
            "Python",
            "RAG",
            "LLM",
        ],
        domains=[
            "AI",
            "Generative AI",
        ],
    )


def make_target_profile():

    return TargetProfile(
        target_roles=[
            "AI Engineer",
        ],
        excluded_roles=[
            "Java Developer",
        ],
        target_domains=[
            "AI",
            "Generative AI",
            "RAG",
        ],
    )


def test_job_search_pipeline():

    source = FakeSource()

    collector = JobCollector(
        source
    )

    evaluator = FakeEvaluator()

    pipeline = JobSearchPipeline(
        collector=collector,
        evaluator=evaluator,
        target_matcher=TargetMatcher(),
        decision_engine=DecisionEngine(),
        ranker=JobRanker(),
    )

    result = pipeline.run(
        candidate=make_candidate(),
        target_profile=make_target_profile(),
        queries=[
            "AI Engineer",
        ],
        location="Bangalore",
    )

    print("\n")
    print("=" * 60)
    print("JOB SEARCH PIPELINE")
    print("=" * 60)

    print(
        "\nCollected:",
        result.collected_jobs,
    )

    print(
        "Relevant:",
        result.relevant_jobs,
    )

    print(
        "Rejected by target:",
        result.rejected_by_target,
    )

    print("\nRankings:")

    for ranking in result.rankings:

        print(
            f"\n#{ranking.rank} "
            f"{ranking.title}"
        )

        print(
            f"Company: "
            f"{ranking.company}"
        )

        print(
            f"Score: "
            f"{ranking.score}"
        )

        print(
            f"Decision: "
            f"{ranking.recommendation}"
        )

    # -----------------------------------------
    # Assertions
    # -----------------------------------------

    assert result.collected_jobs == 2

    assert result.relevant_jobs == 1

    assert result.rejected_by_target == 1

    assert len(result.rankings) == 1

    assert (
        result.rankings[0].title
        == "AI Engineer"
    )

    assert (
        result.rankings[0].company
        == "AI Company"
    )

    assert (
        result.rankings[0].recommendation
        == "APPLY"
    )

    # Evaluator must only be called for
    # target-relevant jobs.
    assert len(evaluator.calls) == 1

    assert (
        "Python"
        in evaluator.calls[0]
    )