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
from app.resume.ats_pipeline import ATSResumePipeline
from app.resume.keyword_extractor import extract_keywords


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
    assert ada.tools == ""
    assert not ada.bullets[0].startswith(
        "Aeronautical Development Agency"
    )
    assert "4 years" in resume.summary
    assert "VxWorks" in ada.bullets[0]
    assert "Developed mission software" in ada.bullets[0]


def test_grouped_profile_skills_stay_as_category_lines():

    candidate = make_candidate()
    candidate.skills = [
        "Programming: Python, Embedded C, C, Ada 95, JavaScript",
        "AI / RAG / Agentic AI: Docker, RAG, LangChain, LangGraph, Qdrant, Ollama",
        "Tools & DevOps: LDRA, Git, Jenkins",
    ]

    resume = ResumeTailor().tailor(
        candidate,
        make_job(),
    )

    assert any(
        skill.startswith("Programming:")
        for skill in resume.skills
    )
    assert any(
        skill.startswith("AI / RAG")
        for skill in resume.skills
    )
    assert any(
        skill.startswith("Tools & DevOps:")
        for skill in resume.skills
    )
    assert resume.skills == candidate.skills
    assert resume.competencies == candidate.domains


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
    assert "Profile keywords aligned" not in fw_resume.summary
    assert "format_resume" not in ai_resume.summary


def test_tailor_keeps_every_achievement_bullet():

    candidate = make_candidate()
    candidate.experiences[0].description = [
        "Engineered HUD software on VxWorks 7.",
        "Architected a Python DCN solution that accelerated documentation by 200%.",
        "Collaborated with cross-functional teams.",
    ]
    resume = ResumeTailor().tailor(
        candidate,
        make_job(),
    )
    ada = next(
        block
        for block in resume.experiences
        if "Aeronautical" in block.company
    )

    assert len(ada.bullets) == 3
    assert any("200%" in bullet for bullet in ada.bullets)
    assert any("HUD" in bullet for bullet in ada.bullets)
    assert "TensorFlow" not in " ".join(ada.bullets)


def test_keyword_extractor_skips_jd_filler():

    keywords = extract_keywords(
        "Proficiency in C++ and Python. "
        "Such principles. Bachelors in Electrical Science. "
        "Engineer with HCL One Test Embedded studio."
    )

    lowered = [item.lower() for item in keywords]

    assert "python" in lowered
    assert "c++" in lowered
    assert "such" not in lowered
    assert "proficiency" not in lowered
    assert "principles" not in lowered
    assert "bachelors" not in lowered


def test_llm_tool_call_is_not_a_summary():

    blob = (
        '{"name": "format_resume", "parameters": '
        '{"experience": "Cyient Limited LDRA testing"}}'
    )

    assert ATSResumePipeline._is_tool_call(blob)
    assert ATSResumePipeline._plain_summary(blob) is None
    assert ATSResumePipeline._grounded(
        blob,
        make_candidate(),
    ) is False
    assert ATSResumePipeline._plain_summary(
        "Embedded software developer with VxWorks and Python."
    )


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

    candidate = make_candidate()
    candidate.linkedin = (
        "https://www.linkedin.com/in/nayaab-ahmed-n-22a329173/"
    )
    candidate.github = "https://github.com/SNAN-RAZER"
    candidate.certifications = [
        "• Full-Stack Developer — GUVI"
    ]
    candidate.skills = [
        "Programming: Python, Embedded C, C, Ada 95, JavaScript",
        "AI / RAG / Agentic AI: Docker, RAG, LangChain, Qdrant",
    ]
    candidate.domains = [
        "Embedded Systems",
        "Aerospace",
        "Avionics",
        "RTOS",
        "Software Testing",
        "Software Automation",
    ]

    package = agent.run(
        candidate,
        make_job(),
    )

    assert package.ats.score > 0
    assert package.resume_path is not None
    assert package.resume_path.endswith(".docx")
    assert any(
        "Python" in skill
        for skill in package.resume.skills
    )

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
    assert not any(
        text.strip().startswith("Tools (")
        for text in texts
    )
    assert any(
        "WORK EXPERIENCE" in text.upper()
        for text in texts
    )
    assert any(
        "TECHNICAL SKILLS" in text.upper()
        for text in texts
    )
    assert any(
        text.startswith("Programming:")
        for text in texts
    )
    assert not any(
        text.strip().startswith("•")
        and text.startswith("• Programming")
        for text in texts
    )
    assert any("LinkedIn" in text for text in texts)
    assert any("GitHub" in text for text in texts)
    rels = [
        rel.target_ref
        for rel in document.part.rels.values()
        if "hyperlink" in rel.reltype
    ]
    assert any("linkedin.com" in rel for rel in rels)
    assert any("github.com" in rel for rel in rels)
    assert not any(rel.startswith("mailto:") for rel in rels)
    xml = document.element.xml
    assert 'r:id="' in xml
    assert "ns0:id=" not in xml
    assert any(
        "CERTIFICATIONS" in text.upper()
        for text in texts
    )
    assert any(
        "Full-Stack Developer" in text
        and not text.strip().startswith("•")
        for text in texts
    )
    assert any(
        text.startswith("Programming:")
        for text in texts
    )
    assert any(
        "CORE COMPETENCIES" in text.upper()
        for text in texts
    )
    assert any(
        text.strip().startswith("•")
        and "Embedded Systems" in text
        for text in texts
    )
    assert any(
        text.strip().startswith("•") and "Aerospace" in text
        for text in texts
    )
    assert any(
        text.strip().startswith("•")
        and "Software Automation" in text
        for text in texts
    )


def test_jd_boilerplate_is_not_copied_as_skills():

    resume = ResumeTailor().tailor(
        make_candidate(),
        JobPosting(
            job_id="junk-jd",
            title="AI Python Developer",
            company="Acme",
            location="Chennai",
            description=(
                "LOCATION Chennai Chatbots production "
                "candidate background Matplotlib Python C"
            ),
            source="test",
        ),
    )
    blob = " ".join(resume.skills).lower()

    assert "chennai" not in blob
    assert "chatbots" not in blob
    assert "candidate" not in blob
    assert "background" not in blob
    assert "location" not in blob
    assert "Python" in resume.skills
    assert "Profile keywords aligned" not in resume.summary


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
