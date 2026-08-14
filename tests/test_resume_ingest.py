from pathlib import Path

from app.models.candidate import CandidateProfile
from app.profile.resume_ingest import (
    ResumeIngestor,
    profile_gaps,
)


SAMPLE = """
Nayaab Ahmed N
nayaabahmedn@gmail.com
8197718054

Skills
Python, VxWorks, RTOS, C

Experience
Aeronautical Development Agency
Embedded Software Engineer
- Developed mission software using VxWorks and Python.

Education
Bachelor of Engineering, Sai Vidya Institute of Technology
"""


def test_parse_rejects_function_call_json():

    parsed = ResumeIngestor._normalize_llm_output(
        {
            "name": "extract_resume_facts",
            "parameters": {
                "resume_text": "Nayaab Ahmed N",
            },
        }
    )

    assert parsed is None


def test_parse_real_resume_extracts_jobs_and_skills():

    text = Path(
        "data/profile/source_resume.txt"
    ).read_text(encoding="utf-8")

    ingestor = ResumeIngestor()
    ingestor._llm_extract = lambda text: None
    facts = ingestor.parse_text(text)

    assert facts["name"] == "Nayaab Ahmed N"
    assert facts["email"] == "nayaabahmedn@gmail.com"
    companies = [
        job["company"] for job in facts["experience"]
    ]
    assert "Cyient Limited" in companies
    assert "Aeronautical Development Agency" in companies
    assert len(facts["experience"]) >= 4
    assert "Python" in facts["skills"]
    assert "LDRA" in facts["skills"]
    assert facts["experience"][0]["bullets"]


def test_parse_text_extracts_contact_and_skills():

    ingestor = ResumeIngestor()
    ingestor._llm_extract = lambda text: None
    facts = ingestor.parse_text(SAMPLE)

    assert facts["email"] == (
        "nayaabahmedn@gmail.com"
    )
    assert "8197718054" in facts["phone"]
    assert "Python" in facts["skills"]
    assert facts["name"]


def test_store_maps_facts_into_candidate_json():

    facts = {
        "name": "Nayaab Ahmed N",
        "email": "nayaabahmedn@gmail.com",
        "skills": ["Python", "VxWorks"],
        "experience": [
            {
                "company": "Cyient Limited",
                "title": "Software Developer",
                "start_date": "2024-05",
                "end_date": "Present",
                "bullets": [
                    "Conducted integration testing using LDRA."
                ],
            }
        ],
        "education": [
            {
                "degree": "B.E.",
                "institution": "SVIT",
            }
        ],
        "location": "Bangalore",
    }

    existing = CandidateProfile(
        name="Old Name",
        target_roles=["AI Engineer"],
        skills=["C"],
    )

    profile = ResumeIngestor().to_profile(
        facts,
        existing,
    )

    assert profile.name == "Nayaab Ahmed N"
    assert profile.email == "nayaabahmedn@gmail.com"
    assert profile.skills == ["Python", "VxWorks"]
    assert profile.experiences[0].company == (
        "Cyient Limited"
    )
    assert profile.experiences[0].role == (
        "Software Developer"
    )
    assert profile.target_roles == ["AI Engineer"]
    assert profile.preferred_locations == [
        "Bangalore"
    ]
    assert profile_gaps(profile) == []


def test_profile_gaps_for_empty_profile():

    assert "name" in profile_gaps(None)
    assert profile_gaps(
        CandidateProfile(
            name="Nayaab",
            skills=["Python"],
            experiences=[],
        )
    ) == ["experiences"]
