from app.matching.candidate_fit_prefilter import CandidateFitPreFilter
from app.matching.decision_engine import DecisionEngine
from app.matching.job_evaluator import JobEvaluator
from app.matching.job_ranker import JobRanker
from app.matching.target_matcher import TargetMatcher
from app.models.candidate import (
    CandidateProfile,
    Experience,
    Project,
)
from app.models.job import JobPosting
from app.models.target_profile import TargetProfile
from app.pipeline.job_search_pipeline import JobSearchPipeline
from app.sources.job_collector import JobCollector


class FakeSource:

    def search(
        self,
        keyword,
        location="",
        page=1,
        experience=2,
        job_age=3,
        results_per_page=20,
    ):

        return [
            JobPosting(
                job_id="1",
                title="AI Engineer",
                company="AI Company",
                location="Bangalore",
                description="""
                Build LLM applications using Python,
                RAG, LangChain and Qdrant.
                """,
                source="test",
            ),
            JobPosting(
                job_id="2",
                title="Java Developer",
                company="Java Company",
                location="Bangalore",
                description="""
                Build enterprise Java applications
                using Spring Boot and Hibernate.
                """,
                source="test",
            ),
        ]


def make_candidate():

    return CandidateProfile(
        name="Test Candidate",

        total_experience_years=3,

        skills=[
            "Python",
            "LLM",
            "RAG",
            "LangChain",
            "Qdrant",
        ],

        domains=[
            "AI",
            "Generative AI",
        ],

        experiences=[
            Experience(
                company="AI Company",
                role="AI Engineer",
                description=[
                    "Developed AI applications."
                ],
                technologies=[
                    "Python",
                    "LLM",
                ],
                domains=[
                    "AI",
                ],
            )
        ],

        projects=[
            Project(
                name="RAG Project",
                description=(
                    "Built a local RAG application."
                ),
                technologies=[
                    "Python",
                    "RAG",
                    "LangChain",
                    "Qdrant",
                ],
                domains=[
                    "Generative AI",
                    "RAG",
                ],
            )
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
            "RAG",
            "Generative AI",
        ],
    )


class CountingEvaluator:

    def __init__(self):

        self.calls = []

    def evaluate(
        self,
        candidate,
        job_description,
    ):

        self.calls.append(
            job_description
        )

        return JobEvaluator().evaluate(
            candidate,
            job_description,
        )


def test_candidate_fit_prefilter_runs_before_evaluator():

    source = FakeSource()

    collector = JobCollector(
        source
    )

    evaluator = CountingEvaluator()

    pipeline = JobSearchPipeline(
        collector=collector,
        evaluator=evaluator,
        target_matcher=TargetMatcher(),
        decision_engine=DecisionEngine(),
        ranker=JobRanker(),
        candidate_fit_prefilter=CandidateFitPreFilter(),
    )

    result = pipeline.run(
        candidate=make_candidate(),
        target_profile=make_target_profile(),
        queries=[
            "AI Engineer",
        ],
        location="Bangalore",
    )

    assert result.collected_jobs == 2

    assert result.relevant_jobs == 1

    assert result.rejected_by_candidate_fit == 0

    assert len(evaluator.calls) == 1


def test_candidate_fit_rejects_unrelated_job():

    class BroadTargetMatcher:

        def match(
            self,
            job,
            profile,
        ):

            return type(
                "TargetResult",
                (),
                {
                    "matched": True,
                    "score": 100,
                    "reason": "test",
                },
            )()

    source = FakeSource()

    collector = JobCollector(
        source
    )

    evaluator = CountingEvaluator()

    pipeline = JobSearchPipeline(
        collector=collector,
        evaluator=evaluator,
        target_matcher=BroadTargetMatcher(),
        decision_engine=DecisionEngine(),
        ranker=JobRanker(),
        candidate_fit_prefilter=CandidateFitPreFilter(),
    )

    result = pipeline.run(
        candidate=make_candidate(),
        target_profile=make_target_profile(),
        queries=[
            "AI Engineer",
        ],
        location="Bangalore",
    )

    assert result.collected_jobs == 2

    assert result.rejected_by_candidate_fit == 1

    assert result.relevant_jobs == 1

    assert len(evaluator.calls) == 1