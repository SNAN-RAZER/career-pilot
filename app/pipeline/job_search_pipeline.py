from dataclasses import dataclass

from app.matching.candidate_fit_prefilter import CandidateFitPreFilter
from app.matching.decision_engine import DecisionEngine
from app.matching.job_evaluator import JobEvaluator
from app.matching.job_ranker import JobRanker
from app.matching.target_matcher import TargetMatcher

from app.models.candidate import CandidateProfile
from app.models.job import JobPosting
from app.models.job_ranking import JobRanking
from app.models.target_profile import TargetProfile
from app.models.job_match_result import JobMatchResult

from app.models.application_recommendation import (
    ApplicationRecommendation,
)
from app.models.application_queue_item import (
    ApplicationQueueItem,
)

from app.sources.job_collector import JobCollector

from app.application.application_queue import (
    ApplicationQueue,
)

from app.store.application_store import (
    ApplicationStore,
)

from app.application.application_workflow import (
    ApplicationWorkflow,
)

@dataclass
class PipelineResult:
    collected_jobs: int
    relevant_jobs: int
    rejected_by_target: int
    rejected_by_candidate_fit: int
    rankings: list[JobRanking]
    match_results: list[JobMatchResult]
    application_recommendations: list[ApplicationRecommendation]
    application_queue: list[ApplicationQueueItem]
    

class JobSearchPipeline:

    def __init__(
    self,
    collector: JobCollector,
    evaluator: JobEvaluator,
    target_matcher: TargetMatcher,
    decision_engine: DecisionEngine,
    ranker: JobRanker,
    candidate_fit_prefilter: CandidateFitPreFilter | None = None,
    application_queue: ApplicationQueue | None = None,
    application_store: ApplicationStore | None = None,
    application_workflow: ApplicationWorkflow | None = None,

    ):

        self.collector = collector

        self.evaluator = evaluator

        self.target_matcher = target_matcher

        self.decision_engine = decision_engine

        self.ranker = ranker

        self.candidate_fit_prefilter = (
            candidate_fit_prefilter
            or CandidateFitPreFilter()
        )

        self.application_queue = (
            application_queue
            or ApplicationQueue()
        )

        self.application_store = (
            application_store
            or ApplicationStore()
        )

        self.application_workflow = (
            application_workflow
            or ApplicationWorkflow(
                self.application_queue,
                self.application_store,
            )
        )

    def run(
        self,
        candidate: CandidateProfile,
        target_profile: TargetProfile,
        queries: list[str],
        location: str = "",
        pages: int = 1,
        experience: int = 2,
        job_age: int = 3,
    ) -> PipelineResult:

        # ---------------------------------------------
        # 1. Collect jobs
        # ---------------------------------------------

        print("\nCollecting jobs from Naukri...")

        jobs = self.collector.collect(
            queries=queries,
            location=location,
            pages=pages,
            experience=experience,
            job_age=job_age,
        )

        print(
            f"Collected {len(jobs)} unique jobs."
        )

        # ---------------------------------------------
        # 2. Target filtering
        # ---------------------------------------------

        target_jobs: list[JobPosting] = []

        rejected_by_target = 0

        for job in jobs:

            target_result = (
                self.target_matcher.match(
                    job,
                    target_profile,
                )
            )

            if not target_result.matched:

                rejected_by_target += 1

                continue

            target_jobs.append(job)

        print(
            "Target filtering complete: "
            f"{len(target_jobs)} relevant, "
            f"{rejected_by_target} rejected."
        )

        # ---------------------------------------------
        # 3. Candidate-fit prefilter
        #
        # Cheap deterministic/semantic check.
        # This happens BEFORE the expensive LLM
        # evaluation.
        # ---------------------------------------------

        relevant_jobs: list[JobPosting] = []

        rejected_by_candidate_fit = 0

        for job in target_jobs:

            fit_result = (
                self.candidate_fit_prefilter.match(
                    candidate,
                    job,
                )
            )

            if not fit_result.matched:

                rejected_by_candidate_fit += 1

                print(
                    f"Candidate-fit rejected: "
                    f"{job.title} - "
                    f"{fit_result.reason}"
                )

                continue

            relevant_jobs.append(job)

        print(
            "Candidate-fit filtering complete: "
            f"{len(relevant_jobs)} entering LLM evaluation, "
            f"{rejected_by_candidate_fit} rejected."
        )

        # ---------------------------------------------
        # 4. LLM evaluation
        # ---------------------------------------------
        match_results = []
        application_recommendations = []
        evaluations = []

        for index, job in enumerate(
            relevant_jobs,
            start=1,
        ):

            print(
                f"\nEvaluating "
                f"[{index}/{len(relevant_jobs)}] "
                f"{job.title} - {job.company}"
            )

            evaluation = self.evaluator.evaluate(
                candidate,
                job,
            )

            # -----------------------------------------
            # 5. Career decision
            # -----------------------------------------

            decision = self.decision_engine.decide(
                evaluation
            )
            recommendation = ApplicationRecommendation(
                job=job,
                match_score=decision.match_score,
                eligibility_score=decision.eligibility_score,
                recommendation=decision.decision.value,
                missing_requirements=[
                    blocker.requirement
                    for blocker in decision.blockers
                ],
                reasons=decision.reasons,
                next_action=(
                    "APPLY"
                    if decision.decision.value == "APPLY"
                    else "REVIEW"
                    if decision.decision.value == "REVIEW"
                    else "REJECT"
                ),
            )
            
            application_recommendations.append(
                    recommendation
                )
            if self.application_workflow:
                self.application_workflow.enqueue(
                    recommendation
                )
            evaluation.recommendation = (
                decision.decision.value
            )

            evaluation.reasons = (
                decision.reasons
            )
            match_results.append(
                JobMatchResult(
                    job=job,
                    score=round(
                        JobRanker._calculate_score(evaluation),
                        2,
                    ),
                    recommendation=decision.decision.value,
                    missing_requirements=(
                        evaluation.missing_required_skills
                    ),
                    reasons=decision.reasons,
                )
            )

            evaluations.append(
                (
                    job.title,
                    job.company,
                    evaluation,
                )
            )

        # ---------------------------------------------
        # 6. Rank
        # ---------------------------------------------

        rankings = self.ranker.rank(
            evaluations
        )

        application_queue = (
            self.application_queue.get_all()
        )

        return PipelineResult(
            collected_jobs=len(jobs),
            relevant_jobs=len(relevant_jobs),
            rejected_by_target=rejected_by_target,
            rejected_by_candidate_fit=(
                rejected_by_candidate_fit
            ),
            rankings=rankings,
            match_results=match_results,
            application_recommendations=(
                application_recommendations
            ),
            application_queue=application_queue,
        )