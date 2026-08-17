import json

from app.matching.candidate_fit_prefilter import CandidateFitPreFilter
from app.models.candidate import CandidateProfile, Experience, Project
from app.models.job import JobPosting


def make_candidate() -> CandidateProfile:
    return CandidateProfile(
        name="Test Candidate",
        skills=[
            "Programming: Python, Embedded C, C",
            "AI / RAG: LangChain, Qdrant, RAG, LLM",
        ],
        domains=[
            "Embedded Systems",
            "Aerospace",
            "Generative AI",
            "RAG",
        ],
        experiences=[
            Experience(
                company="Aeronautical Development Agency",
                role="Embedded Software Engineer",
                description=[
                    "Developed embedded software and RTOS drivers.",
                ],
                technologies=[],
                domains=[
                    "Aerospace",
                    "Embedded Systems",
                ],
            )
        ],
        projects=[
            Project(
                name="CareerPilot AI",
                description=(
                    "Built a local RAG application using "
                    "Python, LangChain, Qdrant and Ollama."
                ),
                technologies=[],
                domains=[
                    "Generative AI",
                    "RAG",
                ],
            )
        ],
    )


def make_job(
    title: str,
    description: str,
    job_id: str = "1",
) -> JobPosting:

    return JobPosting(
        job_id=job_id,
        title=title,
        company="Test Company",
        description=description,
        source="test",
    )


class FakeLLM:

    def __init__(self, payload):
        self.payload = payload
        self.prompts = []
        self.llm_model = "test-model"

    def reachable(self) -> bool:
        return True

    def chat(self, messages, **kwargs):
        self.prompts.append(messages[-1]["content"])
        return json.dumps(self.payload)


def test_agent_keeps_python_job_from_grouped_skill_line():

    llm = FakeLLM(
        {
            "jobs": [
                {
                    "job_id": "1",
                    "keep": True,
                    "score": 72,
                    "overlapping_skills": ["Python"],
                    "reason": "Python is listed on the profile.",
                }
            ]
        }
    )
    result = CandidateFitPreFilter(llm=llm).match(
        make_candidate(),
        make_job(
            "Python Developer",
            "Write Python scripts and automation.",
        ),
    )

    assert result.matched is True
    assert "Python" in result.matched_skills
    assert "Programming: Python" in llm.prompts[0]


def test_agent_rejects_unrelated_stack():

    llm = FakeLLM(
        {
            "jobs": [
                {
                    "job_id": "1",
                    "keep": False,
                    "score": 12,
                    "overlapping_skills": [],
                    "reason": "No overlap with listed skills.",
                }
            ]
        }
    )
    result = CandidateFitPreFilter(llm=llm).match(
        make_candidate(),
        make_job(
            "Computer Vision Engineer",
            "PyTorch, CUDA, OpenCV and TensorFlow.",
        ),
    )

    assert result.matched is False


def test_overlapping_skills_must_appear_in_profile():

    llm = FakeLLM(
        {
            "jobs": [
                {
                    "job_id": "1",
                    "keep": True,
                    "score": 90,
                    "overlapping_skills": ["Python", "InventedSkill"],
                    "reason": "ok",
                }
            ]
        }
    )
    result = CandidateFitPreFilter(llm=llm).match(
        make_candidate(),
        make_job("Python Developer", "Python."),
    )

    assert result.matched_skills == ["Python"]


def test_empty_overlap_is_rejected_even_if_keep_true():

    llm = FakeLLM(
        {
            "jobs": [
                {
                    "job_id": "1",
                    "keep": True,
                    "score": 80,
                    "overlapping_skills": [],
                    "reason": "looks related",
                }
            ]
        }
    )
    result = CandidateFitPreFilter(llm=llm).match(
        make_candidate(),
        make_job("Software Engineer", "Java and Spring."),
    )

    assert result.matched is False


def test_missing_model_keeps_query_title_matches_only():

    llm = FakeLLM({"jobs": []})
    llm.llm_model = ""
    matcher = CandidateFitPreFilter(llm=llm)

    keep = matcher.match(
        make_candidate(),
        make_job("Python Developer", "Python."),
        queries=["Python"],
    )
    drop = matcher.match(
        make_candidate(),
        make_job(
            "Java Developer",
            "Build Java services. Python optional.",
        ),
        queries=["Python"],
    )

    assert keep.matched is True
    assert drop.matched is False
    assert llm.prompts == []
