from app.matching.decision_engine import DecisionEngine
from app.matching.job_ranker import JobRanker
from app.matching.target_matcher import TargetMatcher
from app.matching.candidate_fit_prefilter import CandidateFitPreFilter
from tests.job_fit_stubs import keep_non_java_jobs
from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.pipeline.job_search_pipeline import JobSearchPipeline
from app.sources.job_collector import JobCollector

from tests.test_job_search_pipeline import (
    FakeSource,
    FakeEvaluator,
    make_candidate,
    make_target_profile,
)


def test_pipeline_creates_application_recommendation():

    pipeline = JobSearchPipeline(
        collector=JobCollector(FakeSource()),
        evaluator=FakeEvaluator(),
        target_matcher=TargetMatcher(),
        decision_engine=DecisionEngine(),
        ranker=JobRanker(),
        candidate_fit_prefilter=CandidateFitPreFilter(
            screen=keep_non_java_jobs,
        ),
    )

    result = pipeline.run(
        candidate=make_candidate(),
        target_profile=make_target_profile(),
        queries=["AI Engineer"],
        location="Bangalore",
    )

    assert len(
        result.application_recommendations
    ) == 1

    recommendation = (
        result.application_recommendations[0]
    )

    assert isinstance(
        recommendation,
        ApplicationRecommendation,
    )

    assert recommendation.job.title == "AI Engineer"

    assert recommendation.job.company == "AI Company"

    assert recommendation.match_score == 90.0

    assert recommendation.eligibility_score == 90.0

    assert recommendation.recommendation == "APPLY"

    assert recommendation.missing_requirements == []

    assert recommendation.next_action == "APPLY"


def test_pipeline_recommendation_preserves_job_url():

    pipeline = JobSearchPipeline(
        collector=JobCollector(FakeSource()),
        evaluator=FakeEvaluator(),
        target_matcher=TargetMatcher(),
        decision_engine=DecisionEngine(),
        ranker=JobRanker(),
        candidate_fit_prefilter=CandidateFitPreFilter(
            screen=keep_non_java_jobs,
        ),
    )

    result = pipeline.run(
        candidate=make_candidate(),
        target_profile=make_target_profile(),
        queries=["AI Engineer"],
        location="Bangalore",
    )

    recommendation = (
        result.application_recommendations[0]
    )

    assert (
        recommendation.job.job_id
        == "1"
    )