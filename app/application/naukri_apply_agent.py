from app.application.apply_gate import (
    require_ready_to_apply,
)
from app.application.apply_result import ApplyResult
from app.application.exceptions import ApplyBlocked
from app.models.application_queue_item import (
    ApplicationQueueItem,
)
from app.sources.naukri_adapter import NaukriAdapter


class NaukriApplyAgent:

    def __init__(
        self,
        client=None,
        client_factory=None,
    ):
        self._client = client
        self._client_factory = client_factory

    @property
    def client(self):

        if self._client is not None:
            return self._client

        if self._client_factory is None:
            raise ApplyBlocked(
                "Naukri client is not configured."
            )

        self._client = self._client_factory()

        return self._client

    def submit(
        self,
        item: ApplicationQueueItem,
    ) -> ApplyResult:

        require_ready_to_apply(item)

        job = item.recommendation.job

        if job.source != "naukri":
            return ApplyResult(
                submitted=True,
                mode="TRACKED",
                message=(
                    "Marked as applied in Career-Pilot."
                ),
            )

        if self.client.is_external_apply(
            job.job_id
        ):
            raise ApplyBlocked(
                "This job uses an external company "
                "apply page. Open the company site "
                "to apply."
            )

        naukri_job = NaukriAdapter.to_naukri_job(
            job
        )

        tags = (
            job.raw_data.get("tags")
            or item.tailored_resume.skills
        )

        result = self.client.apply_job(
            naukri_job,
            mandatory_skills=tags[:2],
            optional_skills=tags[2:],
            source="search",
        )

        job_result = (
            result.get("jobs") or [{}]
        )[0]

        if job_result.get("questionnaire") or result.get(
            "questionnaire"
        ):
            listing = ""
            from app.application.company_apply import (
                naukri_listing_url,
            )

            url = naukri_listing_url(job)

            if url:
                listing = f" Open {url}"

            raise ApplyBlocked(
                "Naukri asked a screening "
                "questionnaire. Career-Pilot cannot "
                "answer employer questions. Apply "
                "manually on Naukri."
                + listing
            )

        if not self._is_confirmed(result, job_result):
            raise ApplyBlocked(
                "Naukri did not confirm the "
                "application. Open the job on "
                "naukri.com and click Apply there."
            )

        return ApplyResult(
            submitted=True,
            mode="NAUKRI_EASY_APPLY",
            message=(
                "Submitted via Naukri Easy Apply."
            ),
        )

    @staticmethod
    def _is_confirmed(
        result: dict,
        job_result: dict,
    ) -> bool:

        flags = [
            result.get("applied"),
            result.get("alreadyApplied"),
            result.get("applySuccess"),
            result.get("success"),
            job_result.get("applied"),
            job_result.get("alreadyApplied"),
            job_result.get("applySuccess"),
            job_result.get("success"),
        ]

        if any(flag is True for flag in flags):
            return True

        status = str(
            job_result.get("applyStatus")
            or job_result.get("status")
            or result.get("status")
            or result.get("applyStatus")
            or ""
        ).lower()

        return status in {
            "applied",
            "already applied",
            "success",
            "successful",
        }
