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
        return _extract_pdf(path)

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
    location = ""
    city = re.search(
        r"\b(Bangalore|Bengaluru)(?:,\s*India)?\b",
        text,
        re.I,
    )

    if city:
        location = city.group(0)

    if not linkedin:
        slug = re.search(
            r"LinkedIn:\s*([\w\-]+)",
            text,
            re.I,
        )

        if slug:
            linkedin_url = (
                "https://www.linkedin.com/in/"
                f"{slug.group(1)}"
            )
        else:
            linkedin_url = ""
    else:
        linkedin_url = linkedin.group(0)

    if not github:
        handle = re.search(
            r"GitHub:\s*([\w\-]+)",
            text,
            re.I,
        )

        if handle:
            github_url = (
                f"https://github.com/{handle.group(1)}"
            )
        else:
            github_url = ""
    else:
        github_url = github.group(0)

    return {
        "email": email.group(0) if email else "",
        "phone": re.sub(r"\s+", "", phone.group(0))
        if phone
        else "",
        "linkedin": linkedin_url,
        "github": github_url,
        "location": location,
    }


def _extract_pdf(path: Path) -> str:

    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []

    for page in reader.pages:
        text = ""

        try:
            text = page.extract_text(
                extraction_mode="layout"
            ) or ""
        except TypeError:
            text = ""

        if not text.strip():
            text = page.extract_text() or ""

        pages.append(text)

    return _repair_pdf_lines("\n".join(pages))


def _repair_pdf_lines(text: str) -> str:

    lines = [line.rstrip() for line in text.splitlines()]
    joined: list[str] = []

    for line in lines:
        stripped = line.strip()

        if (
            joined
            and stripped
            and not re.match(r"^[•●▪◦\-–—*]", stripped)
            and not stripped.isupper()
            and joined[-1]
            and not re.search(r"[.!?]$", joined[-1].rstrip())
            and (
                stripped[:1].islower()
                or re.match(
                    r"^(present|current|\d+%)",
                    stripped,
                    re.I,
                )
            )
        ):
            joined[-1] = f"{joined[-1]} {stripped}".strip()
            continue

        joined.append(stripped)

    return "\n".join(joined)
