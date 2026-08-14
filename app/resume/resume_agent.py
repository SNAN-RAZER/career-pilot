from app.models.candidate import CandidateProfile
from app.models.job import JobPosting
from app.models.tailored_resume import ResumePackage
from app.resume.allowed_facts import AllowedFacts
from app.resume.ats_pipeline import ATSResumePipeline
from app.resume.ats_validator import ATSValidator
from app.resume.docx_exporter import ResumeExporter
from app.resume.resume_tailor import ResumeTailor


class ResumeAgent:

    def __init__(
        self,
        tailor: ResumeTailor | None = None,
        validator: ATSValidator | None = None,
        exporter: ResumeExporter | None = None,
    ):
        self.tailor = tailor or ResumeTailor()
        self.validator = (
            validator or ATSValidator()
        )
        self.exporter = (
            exporter or ResumeExporter()
        )

        self.pipeline = ATSResumePipeline(
            tailor=self.tailor,
        )

    def run(
        self,
        candidate: CandidateProfile,
        job: JobPosting,
        export: bool = True,
    ) -> ResumePackage:

        resume = self.pipeline.generate(
            candidate,
            job,
        )

        ats = self.validator.score(
            resume,
            job,
            candidate,
        )

        if ats.missing_keywords:
            resume = (
                self.tailor._cover_claimable_keywords(
                    resume,
                    candidate,
                    job,
                    AllowedFacts(candidate),
                )
            )
            ats = self.validator.score(
                resume,
                job,
                candidate,
            )

        resume_path = None

        if export:
            resume_path = self.exporter.export(
                candidate,
                job,
                resume,
            )

        return ResumePackage(
            resume=resume,
            ats=ats,
            resume_path=resume_path,
        )
