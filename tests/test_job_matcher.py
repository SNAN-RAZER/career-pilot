from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.matching.job_matcher import JobMatcher


def create_candidate():

    return CandidateProfile(
        name="Test Candidate",

        total_experience_years=4,

        target_roles=[
            "Embedded Software Engineer",
            "Embedded Engineer",
            "RTOS Engineer",
            "AI Engineer",
            "Python Automation Engineer"
        ],

        skills=[
            "C",
            "Embedded C",
            "Ada95",
            "VxWorks",
            "RTOS",
            "Python",
            "Git",
            "Docker",
            "Node.js",
            "React",
            "MongoDB",
            "LangChain",
            "LangGraph",
            "RAG",
            "Ollama",
            "Qdrant",
            "LLM"
        ],

        domains=[
            "Embedded Systems",
            "Aerospace",
            "Avionics",
            "RTOS",
            "Software Testing",
            "Software Automation",
            "Artificial Intelligence",
            "Generative AI",
            "RAG"
        ]
    )


def test_embedded_job():

    candidate = create_candidate()

    job = Job(
        job_id="JOB001",

        title="Embedded Software Engineer",

        company="Example Aerospace",

        location="Bangalore",

        required_skills=[
            "C",
            "Embedded C",
            "RTOS",
            "Git"
        ],

        preferred_skills=[
            "VxWorks",
            "Ada95"
        ],

        required_experience_years=3,

        domains=[
            "Embedded Systems",
            "Aerospace",
            "RTOS"
        ]
    )

    matcher = JobMatcher()

    result = matcher.match(
        candidate,
        job
    )

    print(result)

    assert result.overall_score >= 80
    assert result.recommendation == "APPLY"


def test_unrelated_java_job():

    candidate = create_candidate()

    job = Job(
        job_id="JOB002",

        title="Senior Java Backend Developer",

        company="Example Software",

        location="Bangalore",

        required_skills=[
            "Java",
            "Spring Boot",
            "Kafka",
            "Microservices"
        ],

        preferred_skills=[
            "AWS"
        ],

        required_experience_years=8,

        domains=[
            "Backend Development",
            "Java"
        ]
    )

    matcher = JobMatcher()

    result = matcher.match(
        candidate,
        job
    )

    print(result)

    assert result.recommendation == "REJECT"