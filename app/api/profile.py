import json
import tempfile
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

    from app.llm.lmstudio_client import LMStudioClient
    if not LMStudioClient().reachable():
        raise HTTPException(400, "Start your model server and test models in Agent settings before parsing a resume.")
    content = resume_file.file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Choose a resume smaller than 10 MB.")
    dest = PROFILE_DIR / f"{SOURCE_STEM}{suffix}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, dir=PROFILE_DIR) as staged:
        staged.write(content)
        staged_path = Path(staged.name)
    try:
        text = extract_resume_text(staged_path)
        if not text.strip():
            raise HTTPException(400, "Could not extract text from that file.")
        facts, meta = ResumeIngestor().parse_for_preview(text)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Resume parsing failed ({type(exc).__name__}). Check your model settings and try again. Your saved profile has been preserved.") from exc
    finally:
        staged_path.unlink(missing_ok=True)
    # Only replace the source after successful extraction and model parsing.
    for old in PROFILE_DIR.glob(f"{SOURCE_STEM}.*"):
        if old.suffix.lower() != ".json":
            old.unlink()
    dest.write_bytes(content)
    (PROFILE_DIR / f"{SOURCE_STEM}.txt").write_text(text, encoding="utf-8")

    PREVIEW_PATH.write_text(
        json.dumps(facts, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "status": "parsed",
        "stored": False,
        "filename": dest.name,
        "facts": facts,
        "source": meta["source"],
        "model": meta["model"],
        "kind": meta["kind"],
        "message": (
            f"Parsed with {meta['kind']} "
            f"({meta['model']}). Review the facts, "
            "then click Store in profile JSON."
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
        ingestor.tagger.enrich_profile(profile)
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
