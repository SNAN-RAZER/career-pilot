from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from fastapi.responses import JSONResponse

from app.api.applications import (
    router as application_router,
)
from app.api.jobs import (
    router as jobs_router,
)
from app.api.profile import (
    router as profile_router,
)
from app.profile.profile_manager import (
    ProfileManager,
)
from app.application.exceptions import (
    ApplyBlocked,
)
from app.services.application_state_machine import (
    InvalidApplicationTransition,
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(
    ApplyBlocked
)
async def apply_blocked_handler(
    request,
    exc: ApplyBlocked,
):
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
        },
    )


@app.exception_handler(
    InvalidApplicationTransition
)
async def invalid_application_transition_handler(
    request,
    exc: InvalidApplicationTransition,
):
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
        },
    )


app.include_router(
    application_router
)
app.include_router(
    jobs_router
)
app.include_router(
    profile_router
)


PROFILE_PATH = (
    "data/profile/candidate.json"
)


@app.get("/")
def root():

    return {
        "status": "ok",
        "service": "career-pilot",
        "dashboard": "http://localhost:5173",
        "docs": "/docs",
        "health": "/health",
        "applications": "/applications",
    }


@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "career-pilot",
    }


def main():

    manager = ProfileManager(
        PROFILE_PATH
    )

    profile = manager.load()

    print("\nCandidate Profile")
    print("=================")

    print(
        f"Name: {profile.name}"
    )

    print(
        "Experience: "
        f"{profile.total_experience_years} years"
    )

    print("\nTarget Roles:")

    for role in profile.target_roles:
        print(f"  - {role}")

    print("\nSkills:")

    for skill in profile.skills:
        print(f"  - {skill}")

    print("\nExperience:")

    for experience in profile.experiences:

        print(
            f"  - {experience.company} | "
            f"{experience.role}"
        )

    print("\nProjects:")

    for project in profile.projects:
        print(
            f"  - {project.name}"
        )


if __name__ == "__main__":
    main()
