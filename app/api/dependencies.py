from app.application.application_dashboard import (
    ApplicationDashboard,
)
from app.application.application_queue import (
    ApplicationQueue,
)
from app.application.application_service import (
    ApplicationService,
)
from app.application.application_workflow import (
    ApplicationWorkflow,
)
from app.application.naukri_apply_agent import (
    NaukriApplyAgent,
)
from app.store.application_store import (
    ApplicationStore,
)


class ApplicationDependencies:

    def __init__(
        self,
        store_path: str = "data/applications.json",
        job_search_pipeline=None,
        resume_agent=None,
    ):
        self.queue = ApplicationQueue()

        self.store = ApplicationStore(
            store_path
        )

        for application in self.store.load():
            self.queue.load_application(
                application
            )

        self.workflow = ApplicationWorkflow(
            self.queue,
            self.store,
            apply_agent=NaukriApplyAgent(
                client_factory=(
                    self.get_naukri_client
                )
            ),
        )

        self.service = ApplicationService(
            queue=self.queue,
            store=self.store,
            workflow=self.workflow,
        )

        self.dashboard = ApplicationDashboard(
            self.service
        )

        self._job_search_pipeline = (
            job_search_pipeline
        )
        self._naukri_client = None

        from app.resume.resume_agent import (
            ResumeAgent,
        )

        self.resume_agent = (
            resume_agent or ResumeAgent()
        )

    def reset_naukri_client(self):

        self._naukri_client = None
        self._job_search_pipeline = None

    def get_naukri_client(self):

        if self._naukri_client is not None:
            return self._naukri_client

        from app.config.naukri import (
            NaukriSettings,
        )
        from app.naukri.client import (
            create_naukri_client,
        )

        settings = NaukriSettings()

        self._naukri_client = (
            create_naukri_client(
                username=settings.username,
                password=settings.password,
            )
        )

        return self._naukri_client

    def get_job_search_pipeline(self):

        if self._job_search_pipeline is not None:
            return self._job_search_pipeline

        from app.matching.decision_engine import (
            DecisionEngine,
        )
        from app.matching.job_evaluator import (
            JobEvaluator,
        )
        from app.matching.job_ranker import (
            JobRanker,
        )
        from app.matching.target_matcher import (
            TargetMatcher,
        )
        from app.pipeline.job_search_pipeline import (
            JobSearchPipeline,
        )
        from app.sources.job_collector import (
            JobCollector,
        )
        from app.sources.naukri_adapter import (
            NaukriAdapter,
        )

        naukri_client = self.get_naukri_client()

        adapter = NaukriAdapter(
            naukri_client
        )

        collector = JobCollector(
            adapter
        )

        self._job_search_pipeline = (
            JobSearchPipeline(
                collector=collector,
                evaluator=JobEvaluator(),
                target_matcher=TargetMatcher(),
                decision_engine=DecisionEngine(),
                ranker=JobRanker(),
                application_queue=self.queue,
                application_store=self.store,
                application_workflow=(
                    self.workflow
                ),
            )
        )

        return self._job_search_pipeline


application_dependencies = (
    ApplicationDependencies()
)
