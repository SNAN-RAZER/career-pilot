from app.matching.decision_engine import DecisionEngine
from app.matching.job_ranker import JobRanker
from app.matching.target_matcher import TargetMatcher
from app.pipeline.job_search_pipeline import JobSearchPipeline
from app.sources.job_collector import JobCollector
from app.models.job_match_result import JobMatchResult

from tests.test_job_search_pipeline import (
    FakeSource,
    FakeEvaluator,
    make_candidate,
    make_target_profile,
)


def test_pipeline_creates_job_match_result():

    source = FakeSource()

    collector = JobCollector(source)

    pipeline = JobSearchPipeline(
        collector=collector,
        evaluator=FakeEvaluator(),
        target_matcher=TargetMatcher(),
        decision_engine=DecisionEngine(),
        ranker=JobRanker(),
    )

    result = pipeline.run(
        candidate=make_candidate(),
        target_profile=make_target_profile(),
        queries=["AI Engineer"],
        location="Bangalore",
    )

    assert result.collected_jobs == 2
    assert result.relevant_jobs == 1

    assert len(result.match_results) == 1

    match = result.match_results[0]

    assert isinstance(
        match,
        JobMatchResult,
    )

    assert match.job.title == "AI Engineer"
    assert match.job.company == "AI Company"

    assert match.score == 94.5
    assert match.recommendation == "APPLY"