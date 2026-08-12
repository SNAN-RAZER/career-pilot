from app.profile.profile_manager import ProfileManager


PROFILE_PATH = "data/profile/candidate.json"


def main():
    manager = ProfileManager(PROFILE_PATH)

    profile = manager.load()

    print("\nCandidate Profile")
    print("=================")

    print(f"Name: {profile.name}")
    print(f"Experience: {profile.total_experience_years} years")

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
        print(f"  - {project.name}")


if __name__ == "__main__":
    main()