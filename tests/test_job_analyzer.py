from app.matching.job_analyzer import JobAnalyzer


JOB_DESCRIPTION = """
We are looking for an AI Engineer with 3 to 5 years
of software development experience.

Required:
- Strong Python programming experience
- Experience with Large Language Models
- Experience building RAG applications
- Experience with vector databases
- Experience with LangChain
- Good understanding of REST APIs

Preferred:
- Experience with PyTorch
- Experience with AWS
- Experience deploying AI applications using Docker

The candidate should have a Bachelor's degree in Computer
Science, Information Technology, Electronics or a related
engineering field.

Experience in Generative AI is preferred.
"""


def test_job_analyzer():

    analyzer = JobAnalyzer()

    result = analyzer.analyze(
        JOB_DESCRIPTION
    )

    print("\nRequired skills:")

    for skill in result.required_skills:
        print(
            f"  {skill.requirement}"
            f" | mandatory={skill.mandatory}"
        )

    print("\nPreferred skills:")

    for skill in result.preferred_skills:
        print(
            f"  {skill.requirement}"
            f" | mandatory={skill.mandatory}"
        )

    print(
        "\nRequired experience:",
        result.required_experience_years
    )

    print(
        "\nMaximum experience:",
        result.maximum_experience_years
    )

    print(
        "\nDomains:",
        result.domains
    )

    print(
        "\nEducation:",
        result.education_requirements
    )

    assert result.required_experience_years == 3

    assert (
        result.maximum_experience_years == 5
    )

    required_names = {
    item.requirement.lower()
    for item in result.required_skills
    }

    assert "python" in required_names
    assert "rag" in required_names
    assert "llm" in required_names
    assert "vector databases" in required_names

    preferred_names = {
    item.requirement.lower()
    for item in result.preferred_skills
    }

    assert "pytorch" in preferred_names
    assert "aws" in preferred_names
    assert "docker" in preferred_names


def test_analyzer_drops_skills_not_written_in_the_job():

    built = JobAnalyzer._build_requirements(
        {
            "required_skills": [
                "Python",
                "AWS KIRO",
                "Spec Driven Development",
            ],
            "preferred_skills": [],
            "domains": [],
            "required_experience_years": 3,
            "maximum_experience_years": None,
            "education_requirements": [],
            "certifications": [],
            "hard_requirements": [],
            "role_type": "engineer",
        },
        "Required: Strong Python programming experience.",
    )
    names = [
        item.requirement
        for item in built.required_skills
    ]

    assert names == ["Python"]