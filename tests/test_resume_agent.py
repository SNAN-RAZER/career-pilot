from app.models.candidate import (
    CandidateProfile,
    Experience,
    Project,
)
from app.models.job import JobPosting
from app.models.tailored_resume import TailoredResume
from app.resume.ats_validator import ATSValidator
from app.resume.resume_agent import ResumeAgent
from app.resume.resume_tailor import ResumeTailor


def make_candidate() -> CandidateProfile:

    return CandidateProfile(
        name="Nayaab Ahmed N",
        target_roles=["AI Engineer"],
        total_experience_years=4,
        professional_summary=(
            "Software developer with embedded "
            "and AI/RAG project experience."
        ),
        skills=[
            "Python",
            "VxWorks",
            "RAG",
            "LangChain",
            "Qdrant",
            "LLM",
        ],
        domains=["Embedded Systems", "RAG"],
        experiences=[
            Experience(
                company=(
                    "Aeronautical Development Agency"
                ),
                role="Embedded Software Engineer",
                start_date="2022-12",
                end_date="2024-02",
                description=[
                    "Developed mission software "
                    "using VxWorks and Python."
                ],
                technologies=[
                    "VxWorks",
                    "Python",
                ],
                domains=["Aerospace"],
            ),
            Experience(
                company="Cyient Limited",
                role="Software Developer",
                start_date="2024-05",
                end_date="Present",
                description=[
                    "Conduct integration testing "
                    "using LDRA."
                ],
                technologies=["LDRA"],
                domains=["Software Testing"],
            ),
        ],
        projects=[
            Project(
                name="AI/RAG Engineering Projects",
                description=(
                    "Built local RAG applications "
                    "using LangChain and Qdrant."
                ),
                technologies=[
                    "Python",
                    "LangChain",
                    "Qdrant",
                    "RAG",
                ],
                domains=["Generative AI"],
            )
        ],
    )


def make_job() -> JobPosting:

    return JobPosting(
        job_id="resume-1",
        title="AI Engineer",
        company="AI Company",
        location="Bangalore",
        description=(
            "Python RAG LLM LangChain Qdrant"
        ),
        source="test",
    )


def test_tailor_prioritizes_job_skills():

    resume = ResumeTailor().tailor(
        make_candidate(),
        make_job(),
    )

    assert resume.skills[:4] == [
        "Python",
        "RAG",
        "LangChain",
        "Qdrant",
    ]

    assert "TensorFlow" not in resume.skills

    assert any(
        "RAG" in highlight
        for highlight in resume.project_highlights
    )


def test_experience_is_grouped_by_company():

    resume = ResumeTailor().tailor(
        make_candidate(),
        make_job(),
    )

    companies = [
        block.company
        for block in resume.experiences
    ]

    assert companies == [
        "Aeronautical Development Agency",
        "Cyient Limited",
    ]

    assert all(
        " | " not in " ".join(block.bullets)
        for block in resume.experiences
    )

    ada = resume.experiences[0]
    assert ada.role == "Embedded Software Engineer"
    assert ada.dates.startswith("Dec 2022")
    assert "month" in ada.dates.lower()
    assert ada.tools.startswith("Tools (")
    assert not ada.bullets[0].startswith(
        "Aeronautical Development Agency"
    )
    assert "4 years" in resume.summary
    assert "%" not in " ".join(ada.bullets)
    assert "VxWorks" not in resume.skills


def test_resume_changes_with_the_job():

    tailor = ResumeTailor()
    ai_resume = tailor.tailor(
        make_candidate(),
        make_job(),
    )
    firmware_job = JobPosting(
        job_id="fw-1",
        title="Firmware Developer",
        company="HRP",
        location="Bengaluru",
        description=(
            "C Embedded C RTOS Unit Testing LDRA"
        ),
        source="test",
    )
    fw_resume = tailor.tailor(
        make_candidate(),
        firmware_job,
    )

    assert "RAG" in ai_resume.skills
    assert "LDRA" in fw_resume.skills
    assert ai_resume.skills != fw_resume.skills
    assert "Firmware Developer" in fw_resume.summary
    assert "AI Engineer" in ai_resume.summary


def test_ats_rejects_invented_skills():

    candidate = make_candidate()
    job = make_job()

    resume = TailoredResume(
        summary="Invented TensorFlow expert.",
        skills=["Python", "TensorFlow"],
        experience_highlights=[
            "Used Python for automation."
        ],
        project_highlights=[],
        grounded=True,
    )

    result = ATSValidator().score(
        resume,
        job,
        candidate,
    )

    assert "TensorFlow" not in resume.skills
    assert resume.grounded is False
    assert result.issues


def test_resume_agent_exports_docx(tmp_path):

    from app.resume.docx_exporter import (
        ResumeExporter,
    )

    agent = ResumeAgent(
        exporter=ResumeExporter(
            str(tmp_path)
        )
    )

    package = agent.run(
        make_candidate(),
        make_job(),
    )

    assert package.ats.score > 0
    assert package.resume_path is not None
    assert package.resume_path.endswith(".docx")
    assert "Python" in package.resume.skills
    assert package.ats.score == 100.0

    from docx import Document

    document = Document(package.resume_path)
    texts = [
        paragraph.text
        for paragraph in document.paragraphs
    ]

    assert any(
        "Aeronautical Development Agency" in text
        for text in texts
    )
    assert any(
        "Cyient Limited" in text
        for text in texts
    )
    assert not any(
        "Cyient Limited | Software Developer:"
        in text
        for text in texts
    )
    assert document.tables == []
    assert any(
        "WORK EXPERIENCE" in text.upper()
        for text in texts
    )
    assert any(
        "TECHNICAL SKILLS" in text.upper()
        for text in texts
    )


def test_ats_is_100_without_inventing_job_skills():

    job = JobPosting(
        job_id="resume-firmware",
        title="Firmware Developer",
        company="HRP",
        location="Bengaluru",
        description=(
            "C Embedded C RTOS Unit Testing "
            "C++ Arm Cortex-M Linux UART I2C"
        ),
        source="test",
    )

    package = ResumeAgent().run(
        make_candidate(),
        job,
        export=False,
    )

    assert package.ats.score == 100.0
    assert "C++" not in package.resume.skills
    assert "TensorFlow" not in package.resume.skills
    assert "RAG" not in package.resume.skills
