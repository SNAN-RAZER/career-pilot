from fastapi import APIRouter, HTTPException

from app.services.application_state_machine import (
    InvalidApplicationTransition,
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
@router.post("/{job_id}/apply")
def apply_application(
    job_id: str,
):

    result = (
        application_dependencies
        .service
        .apply(job_id)
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