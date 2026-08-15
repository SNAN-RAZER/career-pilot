import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.candidate import CandidateProfile
from app.profile.profile_manager import ProfileManager
from app.profile.resume_ingest import (
    ResumeIngestor,
    profile_gaps,
)
from app.resume.source_document import (
    SOURCE_STEM,
    extract_resume_text,
    find_source_resume,
)


router = APIRouter(
    prefix="/profile",
    tags=["profile"],
)

PROFILE_DIR = Path("data/profile")
PROFILE_PATH = PROFILE_DIR / "candidate.json"
PREVIEW_PATH = PROFILE_DIR / "parsed_preview.json"
ALLOWED = {".pdf", ".docx", ".doc", ".txt"}


def _load_profile() -> CandidateProfile | None:

    if not PROFILE_PATH.exists():
        return None

    try:
        return ProfileManager(
            str(PROFILE_PATH)
        ).load()
    except Exception:
        return None


@router.get("")
def get_profile_status():

    profile = _load_profile()
    missing = profile_gaps(profile)
    source = find_source_resume(PROFILE_DIR)
    preview = None

    if PREVIEW_PATH.exists():
        preview = json.loads(
            PREVIEW_PATH.read_text(encoding="utf-8")
        )

    return {
        "json_exists": profile is not None,
        "complete": len(missing) == 0,
        "missing": missing,
        "name": profile.name if profile else None,
        "skills_count": (
            len(profile.skills) if profile else 0
        ),
        "jobs_count": (
            len(profile.experiences) if profile else 0
        ),
        "source_resume": (
            source.name if source else None
        ),
        "parsed_preview": preview is not None,
        "preview_name": (
            preview.get("name") if preview else None
        ),
        "preview": preview,
    }


@router.get("/source-resume")
def get_source_resume():

    path = find_source_resume(PROFILE_DIR)

    if path is None:
        return {
            "uploaded": False,
            "filename": None,
        }

    return {
        "uploaded": True,
        "filename": path.name,
    }


@router.post("/parse")
def parse_resume(
    resume_file: UploadFile = File(...),
):

    filename = resume_file.filename or "resume.pdf"
    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED:
        raise HTTPException(
            status_code=400,
            detail="Upload a PDF, DOC, DOCX, or TXT resume.",
        )

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    for old in PROFILE_DIR.glob(f"{SOURCE_STEM}.*"):
        if old.suffix.lower() != ".json":
            old.unlink()

    dest = PROFILE_DIR / f"{SOURCE_STEM}{suffix}"
    dest.write_bytes(resume_file.file.read())
    text = extract_resume_text(dest)

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from that file.",
        )

    (
        PROFILE_DIR / f"{SOURCE_STEM}.txt"
    ).write_text(text, encoding="utf-8")

    facts = ResumeIngestor().parse_text(text)
    PREVIEW_PATH.write_text(
        json.dumps(facts, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "status": "parsed",
        "stored": False,
        "filename": dest.name,
        "facts": facts,
        "message": (
            "Parsed. Review the facts, then click "
            "Store in profile JSON to update candidate.json."
        ),
    }


@router.post("/store")
def store_parsed_profile():

    if not PREVIEW_PATH.exists():
        raise HTTPException(
            status_code=400,
            detail=(
                "No parsed resume to store. "
                "Use Parse resume first."
            ),
        )

    facts = json.loads(
        PREVIEW_PATH.read_text(encoding="utf-8")
    )
    source = PROFILE_DIR / f"{SOURCE_STEM}.txt"
    ingestor = ResumeIngestor()

    if source.exists():
        facts = ingestor._fill_contact(
            facts,
            source.read_text(encoding="utf-8"),
        )

    existing = _load_profile()

    try:
        profile = ingestor.to_profile(
            facts,
            existing,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    ProfileManager(str(PROFILE_PATH)).save(profile)
    PREVIEW_PATH.unlink(missing_ok=True)

    return {
        "status": "stored",
        "name": profile.name,
        "skills_count": len(profile.skills),
        "jobs_count": len(profile.experiences),
        "missing": profile_gaps(profile),
        "complete": not profile_gaps(profile),
    }
