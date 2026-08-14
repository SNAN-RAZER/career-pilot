from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.services.application_state_machine import (
    InvalidApplicationTransition,
)
from app.application.exceptions import (
    ApplyBlocked,
)
from app.api.dependencies import (
    application_dependencies,
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

    from app.profile.profile_manager import (
        ProfileManager,
    )

    candidate = ProfileManager(
        "data/profile/candidate.json"
    ).load()

    package = (
        application_dependencies
        .resume_agent
        .run(
            candidate,
            application.job,
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

    if application is None or not application.resume_path:

        raise HTTPException(
            status_code=404,
            detail="Resume not found. Tailor it first.",
        )

    path = Path(application.resume_path)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Resume file is missing.",
        )

    return FileResponse(
        path,
        filename=path.name,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
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