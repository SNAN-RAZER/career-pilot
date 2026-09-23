import asyncio
import json
from unittest.mock import patch
import httpx
from fastapi import FastAPI
import pytest
import local_server
import pilot_gateway
from app.api import runs, profile
from app.llm import provider_store


def call(path, method='GET', **kwargs):
    async def request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=local_server.app),
                                    base_url='http://127.0.0.1:8765') as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(request())


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot_gateway, 'DB', tmp_path / 'gateway.sqlite3')
    monkeypatch.setattr(runs, 'STATE_FILE', tmp_path / 'run.json')
    monkeypatch.setattr(runs, 'state', {'status': 'idle', 'message': '', 'events': []})
    monkeypatch.setattr(provider_store, 'SETTINGS_PATH', tmp_path / 'settings.json')
    monkeypatch.setattr(profile, 'PROFILE_DIR', tmp_path)
    monkeypatch.setattr(profile, 'PROFILE_PATH', tmp_path / 'candidate.json')
    monkeypatch.setattr(profile, 'PREVIEW_PATH', tmp_path / 'preview.json')
    runs.stop.clear()


def test_real_local_api_and_static_app():
    assert call('/api/career/status').json()['local'] is True
    assert call('/api/career/health').json()['status'] == 'ok'
    assert call('/api/career/profile').json()['json_exists'] is False
    assert call('/api/career/runs/current').json()['status'] == 'idle'
    assert call('/').status_code == 200


def test_dns_rebinding_and_cross_site_mutations_rejected():
    for headers in ({'host': 'evil.example'}, {'origin': 'https://evil.example'}, {'sec-fetch-site': 'cross-site'}):
        assert call('/api/career/setup/account', 'POST', headers=headers, json={}).status_code == 403


def test_model_settings_round_trip_and_secrets_redacted():
    data = {'id': 'ollama-local', 'kind': 'ollama', 'label': 'Test', 'base_url': 'http://localhost:11434/v1',
            'api_key': 'test-secret', 'chat_model': 'chat', 'embedding_model': 'embed'}
    result = call('/api/career/llm/providers', 'POST', json=data)
    assert result.status_code == 200
    assert 'test-secret' not in result.text
    assert call('/api/career/llm/activate', 'POST', json={'provider_id': 'ollama-local'}).status_code == 200
    settings = call('/api/career/llm/settings')
    assert settings.json()['active']['chat_model'] == 'chat'
    assert 'test-secret' not in settings.text


def test_failed_model_does_not_destroy_existing_resume():
    original = profile.PROFILE_DIR / 'source_resume.txt'
    original.write_text('Existing resume')
    with patch('app.llm.lmstudio_client.LMStudioClient.reachable', return_value=False):
        response = call('/api/career/profile/parse', 'POST', files={'resume_file': ('new.txt', b'New resume', 'text/plain')})
    assert response.status_code == 400
    assert original.read_text() == 'Existing resume'


def test_active_run_blocks_configuration_changes_and_can_pause():
    runs.save('Working', status='running')
    assert call('/api/career/llm/activate', 'POST', json={}).status_code == 409
    assert call('/api/career/runs/pause', 'POST', json={}).json()['status'] == 'pausing'
    assert runs.stop.is_set()


def test_worker_prepares_only_qualified_jobs_and_persists_results(monkeypatch):
    fake = FastAPI()
    actions = []
    @fake.post('/jobs/search')
    def search():
        return {'applications_queued': 3}
    @fake.get('/applications')
    def jobs():
        return [dict(job_id=str(i), company='Fixture', status='PENDING', recommendation='APPLY',
                     match_score=score, eligibility_score=score) for i, score in enumerate([95, 90, 60])]
    @fake.post('/applications/{job_id}/tailor')
    def tailor(job_id: str):
        actions.append(job_id)
        return {'status': 'PENDING'}
    monkeypatch.setattr(pilot_gateway, 'app', fake)
    asyncio.run(runs.execute(runs.RunRequest(roles='Engineer', limit=1, autoApply=False)))
    assert actions == ['0']
    saved = json.loads(runs.STATE_FILE.read_text())
    assert saved['status'] == 'complete'
    assert any('prepared' in e for e in saved['events'])


def test_worker_marks_failure_instead_of_claiming_completion(monkeypatch):
    fake = FastAPI()
    monkeypatch.setattr(pilot_gateway, 'app', fake)
    asyncio.run(runs.execute(runs.RunRequest(roles='Engineer')))
    assert runs.state['status'] == 'failed'
