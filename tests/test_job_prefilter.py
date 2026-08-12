from app.matching.job_prefilter import JobPreFilter
from app.models.job import JobPosting


def make_job(
    title: str,
    description: str = "",
) -> JobPosting:

    return JobPosting(
        job_id="1",
        title=title,
        company="Test Company",
        description=description,
        source="test",
    )


def test_ai_engineer_is_allowed():

    prefilter = JobPreFilter()

    job = make_job(
        "AI Engineer",
        "Build LLM and RAG applications.",
    )

    assert prefilter.match(job) is True


def test_agentic_ai_engineer_is_allowed():

    prefilter = JobPreFilter()

    job = make_job(
        "Agentic AI Engineer",
        "Build AI agents using LLMs.",
    )

    assert prefilter.match(job) is True


def test_rag_specialist_is_allowed():

    prefilter = JobPreFilter()

    job = make_job(
        "RAG Specialist",
        """
        Build retrieval augmented generation
        systems using vector databases and
        embeddings.
        """,
    )

    assert prefilter.match(job) is True


def test_data_scientist_is_rejected():

    prefilter = JobPreFilter()

    job = make_job(
        "Data Scientist",
        "Build machine learning models.",
    )

    assert prefilter.match(job) is False


def test_data_engineer_is_rejected():

    prefilter = JobPreFilter()

    job = make_job(
        "Data Engineer",
        "Build data pipelines and ETL systems.",
    )

    assert prefilter.match(job) is False


def test_unrelated_software_engineer_is_rejected():

    prefilter = JobPreFilter()

    job = make_job(
        "Software Engineer",
        "Build enterprise applications using Java.",
    )

    assert prefilter.match(job) is False