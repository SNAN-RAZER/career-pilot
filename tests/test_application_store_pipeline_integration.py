from app.matching.candidate_fit_prefilter import (
    CandidateFitPreFilter,
)
from app.matching.decision_engine import DecisionEngine
from app.matching.job_ranker import JobRanker
from app.matching.target_matcher import TargetMatcher
from app.pipeline.application_queue import ApplicationQueue
from app.pipeline.job_search_pipeline import JobSearchPipeline
from app.sources.job_collector import JobCollector
from app.store.application_store import ApplicationStore

from tests.test_job_search_pipeline import (
    FakeSource,
    FakeEvaluator,
    make_candidate,
    make_target_profile,
)
from app.application.application_workflow import (
    ApplicationWorkflow,
)

import pytest
def test_pipeline_persists_application(
    tmp_path,
):

    store = ApplicationStore(
        str(tmp_path / "applications.json")
    )

    pipeline = JobSearchPipeline(
        collector=JobCollector(
            FakeSource()
        ),
        evaluator=FakeEvaluator(),
        target_matcher=TargetMatcher(),
        decision_engine=DecisionEngine(),
        ranker=JobRanker(),
        candidate_fit_prefilter=(
            CandidateFitPreFilter()
        ),
        application_queue=ApplicationQueue(),
        application_store=store,
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

    stored = store.load()

    assert len(stored) == 1

    application = stored[0]

    assert (
        application.job.title
        == "AI Engineer"
    )

    assert (
        application.status
        == "PENDING"
    )

    assert (
        application.recommendation
        == "APPLY"
    )

def make_pipeline(queue):

    workflow = ApplicationWorkflow(
        queue
    )

    collector = JobCollector(
        FakeSource()
    )

    return JobSearchPipeline(
        collector=collector,
        evaluator=FakeEvaluator(),
        target_matcher=TargetMatcher(),
        decision_engine=DecisionEngine(),
        ranker=JobRanker(),
        application_workflow=workflow,
    )


def test_apply_recommendation_enters_application_queue():

    queue = ApplicationQueue()

    pipeline = make_pipeline(queue)

    result = pipeline.run(
        candidate=make_candidate(),
        target_profile=make_target_profile(),
        queries=["AI Engineer"],
        location="Bangalore",
    )

    assert result.relevant_jobs == 1

    pending = queue.get_pending()

    assert len(pending) == 1

    item = pending[0]

    assert item.status == "PENDING"

    assert (
        item.recommendation.job.title
        == "AI Engineer"
    )


def test_queued_application_preserves_original_job():

    queue = ApplicationQueue()

    pipeline = make_pipeline(queue)

    pipeline.run(
        candidate=make_candidate(),
        target_profile=make_target_profile(),
        queries=["AI Engineer"],
        location="Bangalore",
    )

    item = queue.get_by_job_id("1")

    assert item is not None

    job = item.recommendation.job

    assert job.job_id == "1"
    assert job.title == "AI Engineer"
    assert job.company == "AI Company"
    assert job.location == "Bangalore"


def test_pipeline_without_workflow_still_works():

    collector = JobCollector(
        FakeSource()
    )

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

    assert result.relevant_jobs == 1
    assert len(result.application_recommendations) == 1