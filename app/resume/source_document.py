import re
from pathlib import Path

PROFILE_DIR = Path("data/profile")
SOURCE_STEM = "source_resume"


def find_source_resume(
    profile_dir: Path = PROFILE_DIR,
) -> Path | None:

    for suffix in (".pdf", ".docx", ".doc", ".txt"):
        path = profile_dir / f"{SOURCE_STEM}{suffix}"

        if path.exists():
            return path

    matches = []

    for suffix in (".pdf", ".docx", ".doc", ".txt"):
        matches.extend(profile_dir.glob(f"*{suffix}"))

    real = [
        path
        for path in matches
        if path.name != "candidate.json"
    ]

    return real[0] if real else None


def extract_resume_text(path: Path) -> str:

    suffix = path.suffix.lower()

    if suffix == ".txt":
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = [
            page.extract_text() or ""
            for page in reader.pages
        ]
        return "\n".join(pages)

    if suffix in {".docx", ".doc"}:
        import docx2txt

        return docx2txt.process(str(path)) or ""

    return ""


def extract_contact(text: str) -> dict[str, str]:

    email = re.search(
        r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
        text,
        re.I,
    )
    phone = re.search(
        r"\+?\d[\d\s\-()]{8,}\d",
        text,
    )
    linkedin = re.search(
        r"https?://(?:www\.)?linkedin\.com/[^\s]+",
        text,
        re.I,
    )
    github = re.search(
        r"https?://(?:www\.)?github\.com/[^\s]+",
        text,
        re.I,
    )

    return {
        "email": email.group(0) if email else "",
        "phone": re.sub(r"\s+", "", phone.group(0))
        if phone
        else "",
        "linkedin": linkedin.group(0) if linkedin else "",
        "github": github.group(0) if github else "",
    }
