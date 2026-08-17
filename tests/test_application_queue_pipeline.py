from app.matching.candidate_fit_prefilter import (
    CandidateFitPreFilter,
)
from tests.job_fit_stubs import keep_non_java_jobs
from app.matching.decision_engine import DecisionEngine
from app.matching.job_ranker import JobRanker
from app.matching.target_matcher import TargetMatcher
from app.pipeline.application_queue import ApplicationQueue
from app.pipeline.job_search_pipeline import JobSearchPipeline
from app.sources.job_collector import JobCollector

from tests.test_job_search_pipeline import (
    FakeSource,
    FakeEvaluator,
    make_candidate,
    make_target_profile,
)


def test_pipeline_builds_application_queue():

    pipeline = JobSearchPipeline(
        collector=JobCollector(
            FakeSource()
        ),
        evaluator=FakeEvaluator(),
        target_matcher=TargetMatcher(),
        decision_engine=DecisionEngine(),
        ranker=JobRanker(),
        candidate_fit_prefilter=(
            CandidateFitPreFilter(
                screen=keep_non_java_jobs,
            )
        ),
        application_queue=ApplicationQueue(),
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

    assert len(
        result.application_queue
    ) == 1

    queue_item = result.application_queue[0]

    assert (
        queue_item.recommendation.job.title
        == "AI Engineer"
    )

    assert (
        queue_item.status
        == "PENDING"
    )

    assert queue_item.priority in {
        "HIGH",
        "NORMAL",
        "LOW",
    }