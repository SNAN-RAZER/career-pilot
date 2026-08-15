from pathlib import Path
import webbrowser

from app.application.company_apply import (
    CompanyApplyPackage,
    extract_company_apply_url,
    naukri_listing_url,
)
from app.application.exceptions import ApplyBlocked
from app.models.application_record import (
    ApplicationRecord,
)
from app.models.candidate import CandidateProfile
from app.resume.resume_agent import ResumeAgent


class CompanyApplyAgent:

    def __init__(
        self,
        resume_agent: ResumeAgent | None = None,
        naukri_client=None,
        client_factory=None,
    ):
        self.resume_agent = (
            resume_agent or ResumeAgent()
        )
        self._client = naukri_client
        self._client_factory = client_factory

    @property
    def client(self):

        if self._client is not None:
            return self._client

        if self._client_factory is None:
            return None

        self._client = self._client_factory()

        return self._client

    def prepare(
        self,
        application: ApplicationRecord,
        candidate: CandidateProfile,
        launch: bool = False,
        write_resume: bool = True,
    ) -> CompanyApplyPackage:

        resume_path = application.resume_path or ""

        if write_resume and (
            not resume_path
            or not Path(resume_path).exists()
        ):
            package = self.resume_agent.run(
                candidate,
                application.job,
            )
            resume_path = package.resume_path or ""

        details = {}
        client = self.client

        if client is not None:
            details = client.get_job_details(
                application.job.job_id
            )

        apply_url = extract_company_apply_url(
            details,
            application.job,
        )

        if not apply_url:
            raise ApplyBlocked(
                "No company apply URL was found. "
                "Open the job on Naukri and use "
                "Apply on company website."
            )

        result = CompanyApplyPackage(
            job_id=application.job.job_id,
            title=application.job.title,
            company=application.job.company,
            apply_url=apply_url,
            naukri_url=naukri_listing_url(
                application.job
            ),
            resume_path=resume_path,
            candidate_name=candidate.name,
            candidate_email=candidate.email,
            candidate_phone=candidate.phone,
            message=(
                "Tailored resume is ready. Open the "
                "company apply page, sign in if asked, "
                "and upload the generated DOCX."
            ),
        )

        if launch and resume_path:
            self.launch(result)

        return result

    @staticmethod
    def launch(package: CompanyApplyPackage) -> None:

        webbrowser.open(package.apply_url)

        resume = Path(package.resume_path)

        if resume.exists():
            webbrowser.open(resume.resolve().as_uri())
