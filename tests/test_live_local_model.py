"""Opt-in smoke test; uses synthetic data and never searches or submits jobs."""
import asyncio
import os
from pathlib import Path
import httpx
import pytest
from app.main import app
from app.api import profile
from app.models.candidate import CandidateProfile
from app.models.job import JobPosting
from app.matching.job_evaluator import JobEvaluator
from app.resume.resume_agent import ResumeAgent

pytestmark = pytest.mark.skipif(os.getenv('CAREER_PILOT_LIVE_MODEL_TEST') != '1', reason='Requires a running local model server')


def test_parse_store_match_and_tailor_with_live_model(tmp_path, monkeypatch):
    monkeypatch.setattr(profile, 'PROFILE_DIR', tmp_path)
    monkeypatch.setattr(profile, 'PROFILE_PATH', tmp_path / 'candidate.json')
    monkeypatch.setattr(profile, 'PREVIEW_PATH', tmp_path / 'preview.json')
    resume = b'''Alex Example
alex@example.com
+91 9000000000
Bangalore, India
Software Engineer
Skills
Python, FastAPI, SQL, Docker, Git
Experience
Example Software | Software Engineer
Jan 2022 - Dec 2025
- Built Python and FastAPI services backed by SQL databases.
- Wrote automated tests and deployed services using Docker.
Education
Bachelor of Computer Science, Example University, 2021
'''
    async def parse_and_store():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test', timeout=None) as client:
            response = await client.post('/profile/parse', files={'resume_file': ('fixture.txt', resume, 'text/plain')})
            assert response.status_code == 200, response.text
            assert response.json()['facts']['name'] == 'Alex Example'
            response = await client.post('/profile/store')
            assert response.status_code == 200, response.text
            assert response.json()['complete']
    asyncio.run(parse_and_store())
    candidate = CandidateProfile.model_validate_json((tmp_path / 'candidate.json').read_text())
    job = JobPosting(job_id='fixture-never-submit', title='Python Software Engineer', company='Example Software',
        source='test', location='Bangalore', description='Build Python services with FastAPI and SQL. Requires 2 years of software engineering experience. Docker is preferred.')
    result = JobEvaluator().evaluate(candidate, job)
    assert 0 <= result.overall_score <= 100
    package = ResumeAgent().run(candidate, job, export=False)
    assert package.resume.skills
    assert 'Python' in package.resume.skills
