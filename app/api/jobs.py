from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

from app.api.dependencies import (
    application_dependencies,
)
from app.profile.profile_manager import (
    ProfileManager,
)
from app.profile.target_profile_builder import (
    build_target_profile,
)


router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
)

PROFILE_PATH = "data/profile/candidate.json"


class JobSearchRequest(BaseModel):

    queries: list[str] = Field(
        min_length=1,
    )
    location: str = ""
    pages: int = Field(default=1, ge=1)
    experience: int = Field(default=2, ge=0)
    job_age: int = Field(default=3, ge=1)


class JobRankingResponse(BaseModel):

    rank: int
    job_id: str = ""
    title: str
    company: str
    location: str | None = None
    score: float
    recommendation: str
    missing_requirements: list[str]
    reasons: list[str]


class JobSearchResponse(BaseModel):

    collected_jobs: int
    relevant_jobs: int
    rejected_by_target: int
    rejected_by_candidate_fit: int
    rankings: list[JobRankingResponse]
    applications_queued: int


@router.post(
    "/search",
    response_model=JobSearchResponse,
)
def search_jobs(
    request: JobSearchRequest,
):

    manager = ProfileManager(PROFILE_PATH)

    try:
        candidate = manager.load()

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    target_profile = build_target_profile(
        candidate
    )

    pipeline = (
        application_dependencies
        .get_job_search_pipeline()
    )

    result = pipeline.run(
        candidate=candidate,
        target_profile=target_profile,
        queries=request.queries,
        location=request.location,
        pages=request.pages,
        experience=request.experience,
        job_age=request.job_age,
    )

    return JobSearchResponse(
        collected_jobs=result.collected_jobs,
        relevant_jobs=result.relevant_jobs,
        rejected_by_target=(
            result.rejected_by_target
        ),
        rejected_by_candidate_fit=(
            result.rejected_by_candidate_fit
        ),
        rankings=[
            JobRankingResponse(
                rank=ranking.rank,
                job_id=ranking.job_id,
                title=ranking.title,
                company=ranking.company,
                location=ranking.location,
                score=ranking.score,
                recommendation=(
                    ranking.recommendation
                ),
                missing_requirements=(
                    ranking.missing_requirements
                ),
                reasons=ranking.reasons,
            )
            for ranking in result.rankings
        ],
        applications_queued=len(
            result.application_recommendations
        ),
    )
