from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.services.application_state_machine import (
    InvalidApplicationTransition,
)
from app.application.exceptions import (
    ApplyBlocked,
)
from app.api.dependencies import (
    application_dependencies,
)
from app.resume.docx_exporter import ResumeExporter
from app.resume.temp_resume import (
    delete_temp_resume,
    write_temp_resume,
)


router = APIRouter(
    prefix="/applications",
    tags=["applications"],
)


@router.get("")
def get_applications():

    return (
        application_dependencies
        .dashboard
        .get_applications()
    )


@router.get("/pending")
def get_pending_applications():

    return (
        application_dependencies
        .service
        .get_pending()
    )


@router.post("/bulk-apply")
async def bulk_apply(min_match: float = 80):

    from app.application.bulk_apply import (
        run_bulk_apply,
    )

    try:
        _load_candidate()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    def tailor(job_id: str):
        application = (
            application_dependencies
            .service
            .get(job_id)
        )

        if application is None:
            return

        _ensure_tailored(job_id, application)

    def apply(job_id: str):
        result = (
            application_dependencies
            .service
            .apply(job_id)
        )

        if result is None:
            raise ApplyBlocked(
                "Application not found"
            )

    async def fallback(job_id: str):
        report = await _web_apply_once(job_id)

        if report.status == "submitted":
            return "Web agent submitted"

        if report.status == "filled":
            return (
                "Web agent filled the form; "
                "submit in Chrome if needed"
            )

        raise ApplyBlocked(
            report.message or report.status
        )

    return await run_bulk_apply(
        application_dependencies.service.get_pending(),
        apply=apply,
        tailor=tailor,
        fallback=fallback,
        min_match=min_match,
    )


@router.get("/{job_id}")
def get_application(
    job_id: str,
):

    application = (
        application_dependencies
        .dashboard
        .get_application(job_id)
    )

    if application is None:

        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return application


def _load_candidate():

    from app.profile.profile_manager import (
        ProfileManager,
    )

    return ProfileManager(
        "data/profile/candidate.json"
    ).load()


def _ensure_tailored(job_id: str, application):

    if application.tailored_resume is not None:
        return application

    candidate = _load_candidate()
    package = (
        application_dependencies
        .resume_agent
        .run(
            candidate,
            application.job,
            export=False,
        )
    )
    application_dependencies.service.tailor(
        job_id,
        package,
    )
    return application_dependencies.service.get(job_id)


async def _web_apply_once(job_id: str, submit: bool = False):

    from app.application.company_apply_agent import (
        CompanyApplyAgent,
    )
    from app.application.web_apply_agent import (
        WebApplyAgent,
    )

    application = (
        application_dependencies
        .service
        .get(job_id)
    )

    if application is None:
        raise ApplyBlocked("Application not found")

    candidate = _load_candidate()
    application = _ensure_tailored(job_id, application)
    temp_path = None

    try:
        prepared = CompanyApplyAgent(
            resume_agent=(
                application_dependencies
                .resume_agent
            ),
            client_factory=(
                application_dependencies
                .get_naukri_client
            ),
        ).prepare(
            application,
            candidate,
            launch=False,
            write_resume=False,
        )
        temp_path = write_temp_resume(
            candidate,
            application.job,
            application.tailored_resume,
        )
        return await WebApplyAgent().run(
            prepared.apply_url,
            candidate,
            resume_path=temp_path,
            allow_submit=submit,
            job_title=application.job.title,
            company=application.job.company,
            tailored=application.tailored_resume,
        )
    finally:
        delete_temp_resume(temp_path)


@router.post("/{job_id}/tailor")
def tailor_application(
    job_id: str,
):

    application = (
        application_dependencies
        .service
        .get(job_id)
    )

    if application is None:

        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    candidate = _load_candidate()

    package = (
        application_dependencies
        .resume_agent
        .run(
            candidate,
            application.job,
            export=False,
        )
    )

    result = (
        application_dependencies
        .service
        .tailor(job_id, package)
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return (
        application_dependencies
        .dashboard
        .get_application(job_id)
    )


@router.get("/{job_id}/resume-file")
def download_resume(job_id: str):

    application = (
        application_dependencies
        .service
        .get(job_id)
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    application = _ensure_tailored(job_id, application)
    candidate = _load_candidate()
    temp_path = write_temp_resume(
        candidate,
        application.job,
        application.tailored_resume,
    )
    filename = ResumeExporter.filename(application.job)

    return FileResponse(
        temp_path,
        filename=filename,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
        ),
        background=BackgroundTask(
            delete_temp_resume,
            temp_path,
        ),
    )


@router.post("/{job_id}/company-apply")
def company_apply(job_id: str):

    application = (
        application_dependencies
        .service
        .get(job_id)
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    from app.profile.profile_manager import (
        ProfileManager,
    )
    from app.application.company_apply_agent import (
        CompanyApplyAgent,
    )

    candidate = ProfileManager(
        "data/profile/candidate.json"
    ).load()

    if application.tailored_resume is None:
        package = (
            application_dependencies
            .resume_agent
            .run(
                candidate,
                application.job,
            )
        )
        application_dependencies.service.tailor(
            job_id,
            package,
        )
        application = (
            application_dependencies
            .service
            .get(job_id)
        )

    try:
        result = CompanyApplyAgent(
            resume_agent=(
                application_dependencies
                .resume_agent
            ),
            client_factory=(
                application_dependencies
                .get_naukri_client
            ),
        ).prepare(
            application,
            candidate,
            launch=False,
        )
    except ApplyBlocked as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return result


@router.post("/{job_id}/web-apply")
async def web_apply(
    job_id: str,
    submit: bool = False,
):

    application = (
        application_dependencies
        .service
        .get(job_id)
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    try:
        return await _web_apply_once(job_id, submit)
    except ApplyBlocked as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.post("/{job_id}/auto-apply")
async def auto_apply(job_id: str):

    from app.application.bulk_apply import (
        apply_one_job,
    )

    item = (
        application_dependencies
        .service
        .queue
        .get_by_job_id(job_id)
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    def tailor(target_id: str):
        application = (
            application_dependencies
            .service
            .get(target_id)
        )

        if application is None:
            return

        _ensure_tailored(target_id, application)

    def apply(target_id: str):
        result = (
            application_dependencies
            .service
            .apply(target_id)
        )

        if result is None:
            raise ApplyBlocked("Application not found")

    async def fallback(target_id: str):
        report = await _web_apply_once(target_id)

        if report.status in {"submitted", "filled"}:
            return f"Web agent ({report.status})"

        raise ApplyBlocked(
            report.message or report.status
        )

    return await apply_one_job(
        item,
        apply=apply,
        tailor=tailor,
        fallback=fallback,
    )


@router.post("/{job_id}/apply")
def apply_application(
    job_id: str,
):

    try:
        result = (
            application_dependencies
            .service
            .apply(job_id)
        )

    except ApplyBlocked as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return (
        application_dependencies
        .dashboard
        .get_application(job_id)
    )


@router.post("/{job_id}/interview")
def move_to_interview(
    job_id: str,
):

    result = (
        application_dependencies
        .service
        .move_to_interview(job_id)
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return (
        application_dependencies
        .dashboard
        .get_application(job_id)
    )


@router.post("/{job_id}/offer")
def mark_offer(
    job_id: str,
):
    try:
        result = (
            application_dependencies
            .service
            .mark_offer(job_id)
        )

    except InvalidApplicationTransition as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return (
        application_dependencies
        .dashboard
        .get_application(job_id)
    )

@router.post("/{job_id}/reject")
def reject_application(
    job_id: str,
):

    result = (
        application_dependencies
        .service
        .reject(job_id)
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return (
        application_dependencies
        .dashboard
        .get_application(job_id)
    )