import json
from pathlib import Path

from app.models.candidate import CandidateProfile


class ProfileManager:

    def __init__(self, profile_path: str):
        self.profile_path = Path(profile_path)

    def load(self) -> CandidateProfile:
        if not self.profile_path.exists():
            raise FileNotFoundError(
                f"Candidate profile not found: {self.profile_path}"
            )

        with open(self.profile_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return CandidateProfile.model_validate(data)

    def save(self, profile: CandidateProfile) -> None:
        self.profile_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            self.profile_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                profile.model_dump(),
                file,
                indent=2,
                ensure_ascii=False
            )