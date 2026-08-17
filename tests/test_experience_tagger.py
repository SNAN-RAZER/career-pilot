import json

from app.models.candidate import CandidateProfile, Experience, Project
from app.profile.experience_tagger import (
    ExperienceTagger,
    ground_domains,
    ground_technologies,
)


CYIENT_BULLETS = [
    "Built a Python-based LDRA regression automation tool.",
    "Systematized DOORS verification and baseline comparison.",
    "Executed Embedded C integration testing using Eclipse RT.",
    "Applied an engineering RAG and agentic AI workflow.",
]


def test_grounding_keeps_named_tools_and_drops_invented():

    text = "\n".join(CYIENT_BULLETS)

    assert ground_technologies(
        ["Python", "LDRA", "DOORS", "TensorFlow"],
        text,
    ) == ["Python", "LDRA", "DOORS"]

    assert "TensorFlow" not in ground_technologies(
        ["TensorFlow"],
        text,
    )


def test_grounding_keeps_domains_named_in_description():

    text = "\n".join(CYIENT_BULLETS)

    assert "RAG" in ground_domains(["RAG", "FinTech"], text)
    assert "FinTech" not in ground_domains(
        ["RAG", "FinTech"],
        text,
    )


def test_tagger_reads_description_via_llm():

    tagger = ExperienceTagger()
    tagger.llm.llm_model = "test-model"
    tagger.llm.chat = lambda *args, **kwargs: json.dumps(
        {
            "items": [
                {
                    "id": "job-0",
                    "technologies": [
                        "Python",
                        "LDRA",
                        "DOORS",
                        "Embedded C",
                        "Eclipse RT",
                        "TensorFlow",
                    ],
                    "domains": [
                        "Software Testing",
                        "RAG",
                        "Agentic AI",
                    ],
                }
            ]
        }
    )

    facts = tagger.enrich_facts(
        {
            "experience": [
                {
                    "company": "Cyient",
                    "title": "Python Automation Engineer",
                    "bullets": CYIENT_BULLETS,
                    "technologies": [],
                    "domains": [],
                }
            ],
            "projects": [],
        }
    )
    job = facts["experience"][0]

    assert "Python" in job["technologies"]
    assert "LDRA" in job["technologies"]
    assert "DOORS" in job["technologies"]
    assert "Embedded C" in job["technologies"]
    assert "Eclipse RT" in job["technologies"]
    assert "TensorFlow" not in job["technologies"]
    assert "RAG" in job["domains"]
    assert "Agentic AI" in job["domains"]


def test_tagger_reads_project_description_via_llm():

    project_text = (
        "Developed an agentic AI RAG system using Python, "
        "LangChain, LangGraph, Ollama, Qdrant, and Docker."
    )
    tagger = ExperienceTagger()
    tagger.llm.llm_model = "test-model"
    tagger.llm.chat = lambda *args, **kwargs: json.dumps(
        {
            "items": [
                {
                    "id": "project-0",
                    "technologies": [
                        "Python",
                        "LangChain",
                        "LangGraph",
                        "Ollama",
                        "Qdrant",
                        "Docker",
                        "TensorFlow",
                    ],
                    "domains": [
                        "RAG",
                        "Agentic AI",
                        "FinTech",
                    ],
                }
            ]
        }
    )

    facts = tagger.enrich_facts(
        {
            "experience": [],
            "projects": [
                {
                    "name": "AI / RAG / KNOWLEDGE GRAPH PROJECT",
                    "description": project_text,
                    "technologies": [],
                    "domains": [],
                }
            ],
        }
    )
    project = facts["projects"][0]

    assert "Python" in project["technologies"]
    assert "LangChain" in project["technologies"]
    assert "Qdrant" in project["technologies"]
    assert "Docker" in project["technologies"]
    assert "TensorFlow" not in project["technologies"]
    assert "RAG" in project["domains"]
    assert "FinTech" not in project["domains"]


def test_enrich_profile_fills_empty_project_tags():

    tagger = ExperienceTagger()
    tagger.llm.llm_model = "test-model"
    tagger.llm.chat = lambda *args, **kwargs: json.dumps(
        {
            "items": [
                {
                    "id": "project-0",
                    "technologies": ["Qdrant", "Ollama"],
                    "domains": ["RAG"],
                }
            ]
        }
    )
    profile = CandidateProfile(
        name="Nayaab Ahmed N",
        projects=[
            Project(
                name="AI RAG project",
                description=(
                    "Vector indexing with Qdrant and local "
                    "inference through Ollama for a RAG system."
                ),
            )
        ],
    )

    tagger.enrich_profile(profile)

    assert profile.projects[0].technologies == [
        "Qdrant",
        "Ollama",
    ]
    assert profile.projects[0].domains == ["RAG"]


def test_enrich_profile_fills_empty_experience_tags():

    tagger = ExperienceTagger()
    tagger.llm.llm_model = "test-model"
    tagger.llm.chat = lambda *args, **kwargs: json.dumps(
        {
            "items": [
                {
                    "id": "job-0",
                    "technologies": ["Matplotlib"],
                    "domains": [],
                }
            ]
        }
    )
    profile = CandidateProfile(
        name="Nayaab Ahmed N",
        experiences=[
            Experience(
                company="Amazon Development Center",
                role="Process Associate",
                description=[
                    "Built automated analytics dashboards using Matplotlib."
                ],
            )
        ],
    )

    tagger.enrich_profile(profile)

    assert profile.experiences[0].technologies == [
        "Matplotlib"
    ]
