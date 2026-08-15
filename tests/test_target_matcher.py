from app.matching.target_matcher import (
    TargetMatcher,
)
from app.models.job import JobPosting
from app.models.target_profile import (
    TargetProfile,
)


def make_job(title, description=""):

    return JobPosting(
        job_id="1",
        title=title,
        company="Test Company",
        description=description,
        source="test",
    )


def make_profile():

    return TargetProfile(
        target_roles=[
            "AI Engineer",
            "Generative AI Engineer",
            "RAG Engineer",
            "Avionics Software Engineer",
        ],

        excluded_roles=[
            "ML Research Scientist",
        ],

        target_domains=[
            "AI",
            "Generative AI",
            "RAG",
            "Avionics",
            "Aerospace",
        ],
    )


def test_firmware_title_is_target_match():

    matcher = TargetMatcher()

    profile = TargetProfile(
        target_roles=[
            "Embedded Software Engineer",
            "RTOS Engineer",
        ],
        target_domains=[
            "Embedded Systems",
        ],
    )

    result = matcher.match(
        make_job("Firmware Engineer"),
        profile,
        queries=["Firmware Engineer"],
    )

    assert result.matched is True


def test_target_ai_engineer():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job("AI Engineer"),
        make_profile(),
    )

    assert result.matched is True
    assert result.score == 100.0


def test_target_rag_engineer():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job("RAG Engineer"),
        make_profile(),
    )

    assert result.matched is True


def test_excluded_research_role():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job(
            "ML Research Scientist"
        ),
        make_profile(),
    )

    assert result.matched is False
    assert result.score == 0.0


def test_ai_domain_fallback():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job(
            "Software Engineer",
            "Build AI and RAG applications."
        ),
        make_profile(),
    )

    assert result.matched is True
    assert result.score == 70.0


def test_genai_does_not_match_ai_engineer_substring():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job("GenAi Engineer"),
        make_profile(),
        queries=["Avionics Software Engineer"],
    )

    assert result.matched is False


def test_technician_is_rejected():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job(
            "Electrical technician",
            "Avionics CAN UART Ethernet",
        ),
        make_profile(),
        queries=["Avionics Software Engineer"],
    )

    assert result.matched is False


def test_ada_query_does_not_match_radar_job():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job(
            "Automotive - AI Engineer",
            "Computer vision, YOLO, radar and "
            "semantic segmentation.",
        ),
        make_profile(),
        queries=["Ada"],
    )

    assert result.matched is False


def test_ada_query_matches_ada95_job():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job(
            "Embedded Software Engineer",
            "Develop avionics software using Ada95 "
            "and VxWorks.",
        ),
        make_profile(),
        queries=["Ada"],
    )

    assert result.matched is True


def test_ai_engineer_query_does_not_match_edge_ai_title():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job(
            "C++ Quantization Engineer - Edge AI"
        ),
        make_profile(),
        queries=["AI Engineer"],
    )

    assert result.matched is False


def test_customer_care_title_is_rejected():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job("Customer Care Executive"),
        make_profile(),
        queries=["RTOS"],
    )

    assert result.matched is False


def test_python_query_matches_python_developer_title():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job("Python Developer"),
        make_profile(),
        queries=["python"],
    )

    assert result.matched is True


def test_python_query_matches_backend_job_with_python_in_jd():

    matcher = TargetMatcher()

    result = matcher.match(
        make_job(
            "Backend Engineer",
            "Build APIs using Python and Django.",
        ),
        make_profile(),
        queries=["python"],
    )

    assert result.matched is True

    matcher = TargetMatcher()

    result = matcher.match(
        make_job(
            "Firmware Engineer",
            "Develop drivers on an RTOS and UART.",
        ),
        make_profile(),
        queries=["RTOS"],
    )

    assert result.matched is True
