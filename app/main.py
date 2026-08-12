from fastapi import FastAPI

from app.api.applications import (
    router as application_router,
)
from app.profile.profile_manager import (
    ProfileManager,
)


from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.services.application_state_machine import (
    InvalidApplicationTransition,
)

app = FastAPI()


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


PROFILE_PATH = (
    "data/profile/candidate.json"
)


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

    @app.get("/health")
    def health():

        return {
            "status": "ok",
            "service": "career-pilot",
        }
if __name__ == "__main__":
    main()