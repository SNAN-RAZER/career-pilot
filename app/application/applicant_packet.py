from app.models.candidate import CandidateProfile
from app.models.tailored_resume import TailoredResume


def build_applicant_packet(
    candidate: CandidateProfile,
    tailored: TailoredResume | None = None,
) -> dict[str, str]:

    parts = [
        part
        for part in candidate.name.split()
        if part
    ]
    first = parts[0] if parts else ""
    last = " ".join(parts[1:]) if len(parts) > 1 else ""
    current = (
        candidate.experiences[0]
        if candidate.experiences
        else None
    )
    school = (
        candidate.education[0]
        if candidate.education
        else None
    )
    location = (
        candidate.preferred_locations[0]
        if candidate.preferred_locations
        else ""
    )
    summary = candidate.professional_summary or ""
    skills = list(candidate.skills[:20])
    experience_bits = []

    for item in candidate.experiences[:3]:
        experience_bits.append(
            f"{item.role} at {item.company}"
        )
        experience_bits.extend(item.description[:2])

    if tailored is not None:
        if tailored.summary:
            summary = tailored.summary

        if tailored.skills:
            skills = list(tailored.skills[:25])

        tailored_bits = []

        for block in tailored.experiences[:3]:
            tailored_bits.append(
                f"{block.role} at {block.company}"
            )
            tailored_bits.extend(block.bullets[:2])

        if tailored_bits:
            experience_bits = tailored_bits

        experience_bits.extend(
            tailored.experience_highlights[:4]
        )

    packet = {
        "full_name": candidate.name,
        "first_name": first,
        "last_name": last,
        "email": candidate.email or "",
        "phone": candidate.phone or "",
        "linkedin": candidate.linkedin or "",
        "github": candidate.github or "",
        "location": location,
        "city": location,
        "years_experience": (
            str(int(candidate.total_experience_years))
            if candidate.total_experience_years
            else ""
        ),
        "current_company": (
            current.company if current else ""
        ),
        "current_title": current.role if current else "",
        "skills": ", ".join(skills),
        "summary": summary,
        "cover_letter": summary,
        "experience": " ".join(experience_bits)[:1500],
        "degree": school.degree if school else "",
        "institution": (
            school.institution if school else ""
        ),
        "education_year": (
            school.year if school else ""
        ) or "",
    }

    return {
        key: value.strip()
        for key, value in packet.items()
        if value and str(value).strip()
    }
