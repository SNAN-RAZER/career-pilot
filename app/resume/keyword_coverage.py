import re

from app.models.candidate import CandidateProfile
from app.resume.allowed_facts import AllowedFacts
from app.resume.keyword_extractor import extract_keywords


def contains_keyword(text: str, keyword: str) -> bool:

    if not text or not keyword:
        return False

    pattern = (
        r"(?<![A-Za-z0-9+#])"
        + re.escape(keyword.lower())
        + r"(?![A-Za-z0-9+#])"
    )

    return re.search(pattern, text.lower()) is not None


def candidate_corpus(
    candidate: CandidateProfile,
) -> str:

    parts = [
        candidate.professional_summary,
        *candidate.skills,
        *candidate.domains,
        *candidate.certifications,
        *candidate.target_roles,
    ]

    for experience in candidate.experiences:
        parts.extend(
            [
                experience.company,
                experience.role,
                *experience.description,
                *experience.technologies,
                *experience.domains,
            ]
        )

    for project in candidate.projects:
        parts.extend(
            [
                project.name,
                project.description,
                *project.technologies,
                *project.domains,
            ]
        )

    for item in candidate.education:
        parts.extend(
            [
                item.degree,
                item.institution,
            ]
        )

    return " ".join(
        part
        for part in parts
        if part
    )


def claimable_keywords(
    candidate: CandidateProfile,
    job_title: str,
    job_description: str,
) -> list[str]:

    corpus = candidate_corpus(candidate)
    facts = AllowedFacts(candidate)
    keywords = extract_keywords(
        f"{job_title} {job_description}"
    )[:40]

    claimable = []

    for keyword in keywords:
        if facts.allows_skill(keyword) or contains_keyword(
            corpus,
            keyword,
        ):
            claimable.append(keyword)

    return claimable


def resume_text(resume) -> str:

    experience_bits = list(
        resume.experience_highlights
    )

    for block in getattr(resume, "experiences", []) or []:
        experience_bits.extend(
            [
                block.company,
                block.role,
                *block.bullets,
            ]
        )

    return " ".join(
        [
            resume.summary,
            *resume.skills,
            *experience_bits,
            *resume.project_highlights,
        ]
    )
