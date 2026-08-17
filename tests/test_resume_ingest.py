from pathlib import Path

from app.models.candidate import CandidateProfile
from app.profile.resume_ingest import (
    ResumeIngestor,
    profile_gaps,
)
from app.profile.resume_parse_agent import ResumeParseAgent


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
    assert any("Cyient" in company for company in companies)
    assert "Aeronautical Development Agency" in companies
    assert len(facts["experience"]) >= 4
    assert facts["headline"].upper().startswith("PYTHON")
    assert facts.get("projects")
    assert "linkedin.com" in (facts.get("linkedin") or "")
    assert "github.com" in (facts.get("github") or "")
    assert "Python" in facts["skills"]
    assert "LDRA" in facts["skills"]
    assert "Kannada" in facts["languages"]
    assert len(facts["education"]) == 2
    assert any(
        "PCMB" in (row.get("degree") or "")
        for row in facts["education"]
    )
    amazon = [
        job
        for job in facts["experience"]
        if "amazon" in job["company"].lower()
    ]
    assert len(amazon) == 2
    assert all(job["company"] for job in amazon)
    assert facts["experience"][0]["bullets"]
    cyient = next(
        job
        for job in facts["experience"]
        if "Cyient" in job["company"]
    )
    ada = next(
        job
        for job in facts["experience"]
        if "Aeronautical" in job["company"]
    )
    assert any("75%" in bullet for bullet in cyient["bullets"])
    assert any("HUD" in bullet for bullet in ada["bullets"])
    assert any("200%" in bullet for bullet in ada["bullets"])


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
                "technologies": ["LDRA", "TensorFlow"],
                "domains": ["Software Testing"],
            }
        ],
        "education": [
            {
                "degree": "B.E.",
                "institution": "SVIT",
            }
        ],
        "location": "Bangalore",
        "summary": "Python Automation Engineer.",
        "projects": [
            {
                "name": "AI / RAG / KNOWLEDGE GRAPH PROJECT",
                "bullets": [
                    "Built a RAG system with Python, LangChain, Qdrant, and Docker."
                ],
                "technologies": ["Python", "LangChain", "Qdrant", "Docker", "TensorFlow"],
                "domains": ["RAG", "FinTech"],
            }
        ],
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
    assert profile.experiences[0].technologies == ["LDRA"]
    assert profile.experiences[0].domains == [
        "Software Testing"
    ]
    assert "TensorFlow" not in (
        profile.experiences[0].technologies
    )
    assert profile.target_roles == ["AI Engineer"]
    assert profile.preferred_locations == [
        "Bangalore"
    ]
    assert profile.professional_summary == (
        "Python Automation Engineer."
    )
    assert profile.projects[0].name.startswith("AI")
    assert profile.projects[0].technologies == [
        "Python",
        "LangChain",
        "Qdrant",
        "Docker",
    ]
    assert profile.projects[0].domains == ["RAG"]
    assert "TensorFlow" not in profile.projects[0].technologies
    assert profile_gaps(profile) == []


def test_store_maps_project_description_string_tags():

    facts = {
        "name": "Nayaab Ahmed N",
        "email": "nayaabahmedn@gmail.com",
        "skills": ["Python"],
        "experience": [
            {
                "company": "Cyient",
                "title": "Engineer",
                "bullets": ["Used Python."],
            }
        ],
        "projects": [
            {
                "name": "AI RAG project",
                "description": (
                    "Built semantic retrieval with Qdrant "
                    "and LangChain for RAG."
                ),
                "technologies": [
                    "Qdrant",
                    "LangChain",
                    "TensorFlow",
                ],
                "domains": ["RAG"],
            }
        ],
        "education": [
            {
                "degree": "B.E.",
                "institution": "SVIT",
            }
        ],
    }

    profile = ResumeIngestor().to_profile(facts)

    assert profile.projects[0].description.startswith(
        "Built semantic retrieval"
    )
    assert profile.projects[0].technologies == [
        "Qdrant",
        "LangChain",
    ]
    assert profile.projects[0].domains == ["RAG"]


def test_parse_uses_agent_json_not_heuristic_merge():

    payload = {
        "name": "Nayaab Ahmed N",
        "email": "nayaabahmedn@gmail.com",
        "phone": "8197718054",
        "skills": ["Python", "LDRA", "VxWorks"],
        "experience": [
            {
                "company": "Cyient",
                "title": "Python Automation Engineer",
                "start_date": "2024-05",
                "end_date": "Present",
                "bullets": [
                    "Engineered Python-based LDRA regression tool, reducing review time by 75%."
                ],
            }
        ],
        "education": [],
        "summary": "Python Automation Engineer with DO-178B experience.",
    }

    ingestor = ResumeIngestor()
    ingestor._llm_extract = lambda text: payload
    facts = ingestor.parse_text(SAMPLE)

    assert facts["experience"][0]["bullets"][0].startswith(
        "Engineered Python-based LDRA"
    )
    assert facts["summary"].startswith("Python Automation")
    assert "Aeronautical" not in str(facts["experience"])


def test_usable_agent_json_is_not_rewritten_by_heuristic():

    payload = {
        "name": "Nayaab Ahmed N",
        "email": "nayaabahmedn@gmail.com",
        "phone": "8197718054",
        "skills": [
            "Python",
            "LDRA",
            "VxWorks",
            "C",
        ],
        "experience": [
            {
                "company": "Cyient",
                "title": "Python Automation Engineer",
                "start_date": "2024-05",
                "end_date": "Present",
                "bullets": [
                    "Engineered Python-based LDRA regression tool, reducing review time by 75%."
                ],
            },
            {
                "company": "Amazon Development Center",
                "title": "Process Associate",
                "start_date": "2018-12",
                "end_date": "2019-05",
                "bullets": [
                    "Designed SCADA layouts using Movicon."
                ],
            },
        ],
        "education": [
            {
                "degree": "B.E Electrical & Electronics Engineering (CGPA: 6.67)",
                "institution": "Sai Vidya Institute of Technology",
                "year": "2018",
            }
        ],
        "summary": "Python Automation Engineer with DO-178B experience.",
    }

    text = Path(
        "data/profile/source_resume.txt"
    ).read_text(encoding="utf-8")
    ingestor = ResumeIngestor()
    ingestor._llm_extract = lambda _: payload
    facts = ingestor.parse_text(text)

    assert len(facts["experience"]) == 2
    assert facts["experience"][0]["company"] == "Cyient"
    assert facts["summary"].startswith("Python Automation")
    assert len(facts["education"]) == 1


def test_normalize_keeps_grounded_job_technologies():

    facts = ResumeParseAgent._normalize(
        {
            "name": "Nayaab Ahmed N",
            "experience": [
                {
                    "company": "Cyient",
                    "title": "Engineer",
                    "start_date": "2024-05",
                    "end_date": "Present",
                    "bullets": [
                        "Built a Python-based LDRA tool."
                    ],
                    "technologies": ["Python", "LDRA"],
                    "domains": ["Software Testing"],
                }
            ],
            "projects": [
                {
                    "name": "RAG project",
                    "bullets": [
                        "Used Python and Qdrant for RAG."
                    ],
                    "technologies": ["Python", "Qdrant"],
                    "domains": ["RAG"],
                }
            ],
        }
    )

    assert facts["experience"][0]["technologies"] == [
        "Python",
        "LDRA",
    ]
    assert facts["projects"][0]["technologies"] == [
        "Python",
        "Qdrant",
    ]


def test_agent_rejects_tool_call_name():

    assert ResumeParseAgent._is_fake_name(
        "extract_candidate_profile"
    )
    assert not ResumeParseAgent._is_fake_name(
        "Nayaab Ahmed N"
    )
    assert ResumeParseAgent._is_school_entry(
        {
            "company": "Sai Vidya Institute of Technology",
            "title": "B.E Electrical & Electronics Engineering",
        }
    )
    issues = ResumeParseAgent._quality_issues(
        {
            "name": "Nayaab Ahmed N",
            "skills": ["Python", "C", "LDRA"],
            "experience": [
                {
                    "company": (
                        "Built a Python-based LDRA regression "
                        "automation tool, reducing review time "
                        "by 75% and improving efficiency."
                    ),
                    "title": "Engineer",
                    "bullets": [],
                }
            ],
        }
    )
    assert issues
    assert ResumeParseAgent._strip_city(
        "Cyient, Bangalore"
    ) == "Cyient"


def test_profile_gaps_for_empty_profile():

    assert "name" in profile_gaps(None)
    assert profile_gaps(
        CandidateProfile(
            name="Nayaab",
            skills=["Python"],
            experiences=[],
        )
    ) == ["experiences"]


def test_parse_for_preview_requires_chat_model(monkeypatch):

    ingestor = ResumeIngestor()
    ingestor.llm.llm_model = ""

    try:
        ingestor.parse_for_preview(SAMPLE)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "chat model" in str(exc).lower()


def test_parse_for_preview_uses_agent_not_heuristic():

    payload = {
        "name": "Nayaab Ahmed N",
        "email": "nayaabahmedn@gmail.com",
        "skills": ["Python"],
        "experience": [
            {
                "company": "Cyient",
                "title": "Engineer",
                "start_date": "2024-01",
                "end_date": "Present",
                "bullets": ["Built tools."],
            }
        ],
    }
    ingestor = ResumeIngestor()
    ingestor.llm.llm_model = "hermes3:latest"
    ingestor.agent.reachable = lambda: True
    ingestor._llm_extract = lambda _: payload
    ingestor.tagger.enrich_facts = lambda facts: facts
    facts, meta = ingestor.parse_for_preview(SAMPLE)

    assert facts["experience"][0]["company"] == "Cyient"
    assert meta["source"] == "agent"
    assert meta["model"] == "hermes3:latest"
