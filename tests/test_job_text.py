from app.matching.job_analyzer import JobAnalyzer
from app.matching.job_text import strip_job_html
from app.matching.job_analysis_input import (
    build_job_analysis_input,
)
from app.models.job import JobPosting


HTML_JOB = """
<b>Must have skills :</b>.Net Full Stack Development<br />
<b>Good to have skills :</b>NA<br />
Minimum <b>2</b> year(s) of experience is required<br />
<li>Hands-On Coding in .NET Core (C#, ASP.NET), and Python</li>
"""


def test_strip_job_html_keeps_skills_not_tags():

    text = strip_job_html(HTML_JOB)

    assert "<b>" not in text
    assert "<br" not in text
    assert ".Net Full Stack Development" in text
    assert "Python" in text


def test_build_job_analysis_input_strips_html():

    job = JobPosting(
        job_id="1",
        title="Custom Software Engineer",
        company="Accenture",
        description=HTML_JOB,
        source="naukri",
    )

    blob = build_job_analysis_input(job)

    assert "<b>" not in blob
    assert "Must have skills" in blob


def test_clean_skills_drops_tool_calls_and_html():

    cleaned = JobAnalyzer._clean_skills(
        [
            "extract_requirements",
            "job_description",
            "<b>Must have skills :</b>.Net Full Stack Development<br />",
            "Python",
            ".NET",
            "React",
        ]
    )

    assert cleaned == ["Python", ".NET", "React"]


def test_parse_json_rejects_tool_call_payload():

    parsed = JobAnalyzer._parse_json(
        """
        {
          "name": "extract_requirements",
          "parameters": {
            "job_description": "<b>Must have skills</b>"
          }
        }
        """
    )

    assert parsed is None
