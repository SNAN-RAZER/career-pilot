from app.matching.candidate_fit_prefilter import CandidateFitPreFilter
from app.models.candidate import CandidateProfile, Experience, Project
from app.models.job import JobPosting


def make_candidate() -> CandidateProfile:
    return CandidateProfile(
        name="Test Candidate",
        skills=[
            "Python",
            "Embedded C",
            "VxWorks",
            "RTOS",
            "LangChain",
            "Qdrant",
            "RAG",
            "LLM",
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
                technologies=[
                    "Embedded C",
                    "VxWorks",
                    "RTOS",
                ],
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
                technologies=[
                    "Python",
                    "LangChain",
                    "Qdrant",
                    "RAG",
                    "LLM",
                ],
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
) -> JobPosting:

    return JobPosting(
        job_id="1",
        title=title,
        company="Test Company",
        description=description,
        source="test",
    )


def test_ai_rag_job_is_good_candidate_fit():

    candidate = make_candidate()

    job = make_job(
        "AI Engineer",
        """
        Build production RAG applications using
        Python, LangChain, LLMs and vector databases.
        """,
    )

    matcher = CandidateFitPreFilter()

    result = matcher.match(
        candidate,
        job,
    )

    assert result.matched is True
    assert result.score >= 70


def test_job_using_candidate_professional_skills_is_good_fit():

    candidate = make_candidate()

    job = make_job(
        "Embedded Software Engineer",
        """
        Develop RTOS drivers using Embedded C
        and VxWorks for aerospace systems.
        """,
    )

    matcher = CandidateFitPreFilter()

    result = matcher.match(
        candidate,
        job,
    )

    assert result.matched is True
    assert result.score >= 70


def test_unrelated_ai_stack_is_low_fit():

    candidate = make_candidate()

    job = make_job(
        "Computer Vision Engineer",
        """
        Develop computer vision models using
        PyTorch, CUDA, OpenCV and TensorFlow.
        """,
    )

    matcher = CandidateFitPreFilter()

    result = matcher.match(
        candidate,
        job,
    )

    assert result.matched is False


def test_candidate_fit_uses_project_evidence():

    candidate = make_candidate()

    job = make_job(
        "Generative AI Engineer",
        """
        Build LLM applications using RAG,
        LangChain, Qdrant and Python.
        """,
    )

    matcher = CandidateFitPreFilter()

    result = matcher.match(
        candidate,
        job,
    )

    assert result.matched is True
    assert "RAG" in result.matched_skills


def test_empty_candidate_has_no_fit():

    candidate = CandidateProfile(
        name="Empty Candidate",
    )

    job = make_job(
        "AI Engineer",
        """
        Python, LLM, RAG, LangChain,
        vector databases.
        """,
    )

    matcher = CandidateFitPreFilter()

    result = matcher.match(
        candidate,
        job,
    )

    assert result.matched is False