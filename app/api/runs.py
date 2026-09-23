"""Durable run status, with one worker that survives closing the browser tab."""
import asyncio
import json
import threading
from pathlib import Path
from urllib.parse import quote
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix='/runs', tags=['runs'])
STATE_FILE = Path('data/agent-run.json')
lock = threading.RLock()
stop = threading.Event()
state = {'status': 'idle', 'message': '', 'events': []}
if STATE_FILE.exists():
    try:
        state.update(json.loads(STATE_FILE.read_text(encoding='utf-8')))
        if state['status'] in ('running', 'pausing'):
            state.update(status='interrupted', message='The agent stopped unexpectedly. Review application outcomes before starting another run.')
    except (ValueError, OSError):
        pass


class RunRequest(BaseModel):
    roles: str = Field(min_length=1, max_length=500)
    location: str = Field(default='', max_length=200)
    experience: int = Field(default=2, ge=0, le=50)
    minMatch: int = Field(default=85, ge=70, le=100)
    limit: int = Field(default=5, ge=1, le=20)
    autoApply: bool = False


def save(message=None, **values):
    with lock:
        state.update(values)
        if message:
            state['message'] = message
            state['events'] = [message, *state.get('events', [])][:100]
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp = STATE_FILE.with_suffix('.tmp')
        temp.write_text(json.dumps(state), encoding='utf-8')
        temp.replace(STATE_FILE)


def active():
    with lock:
        return state['status'] in ('running', 'pausing')


@router.get('/current')
def current():
    with lock:
        return dict(state)


@router.post('/pause')
def pause():
    with lock:
        if active():
            stop.set()
            save('Pause requested; finishing the current action.', status='pausing')
        return dict(state)


@router.post('/start')
def start(payload: RunRequest):
    from app.api.setup import status
    from app.llm.lmstudio_client import LMStudioClient
    ready = status()
    if ready['missing_dependencies']:
        raise HTTPException(400, 'Run Start Career Pilot.cmd to install: ' + ', '.join(ready['missing_dependencies']))
    if not ready['profile_saved']:
        raise HTTPException(400, 'Upload and save your resume first.')
    if not ready['account_configured']:
        raise HTTPException(400, 'Save your Naukri account in Agent settings first.')
    if not ready['job_source_installed']:
        raise HTTPException(400, 'Job source dependency is missing. Run Start Career Pilot.cmd again.')
    if not LMStudioClient().reachable():
        raise HTTPException(400, 'Your model server is not running. Start it and test your models in Agent settings.')
    with lock:
        if active():
            raise HTTPException(409, 'An agent run is already active.')
        stop.clear()
        save('Searching for matching jobs…', status='running', events=[])
        threading.Thread(target=lambda: asyncio.run(execute(payload)), daemon=True, name='career-pilot-run').start()
        return dict(state)


async def execute(p):
    from pilot_gateway import app, TOKEN, outcome
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://agent',
                               headers={'Authorization': 'Bearer ' + TOKEN}, timeout=None) as client:
        async def request(path, body=None):
            response = await client.request('POST' if body is not None else 'GET', path, json=body)
            if response.is_error:
                try:
                    detail = response.json().get('detail', 'Agent request failed.')
                except ValueError:
                    detail = 'Agent request failed. Check the local server log.'
                raise RuntimeError(str(detail))
            return response.json()
        try:
            await request('/jobs/search', {'queries': [s.strip() for s in p.roles.split(',') if s.strip()],
                'location': p.location, 'experience': p.experience, 'pages': 1, 'job_age': 7})
            jobs = await request('/applications')
            eligible = sorted((j for j in jobs if j['status'] in (('PENDING', 'PREPARED') if p.autoApply else ('PENDING',)) and j['recommendation'] == 'APPLY'
                and j['match_score'] >= p.minMatch and j['eligibility_score'] >= p.minMatch),
                key=lambda j: j['match_score'], reverse=True)[:p.limit]
            save(f'{len(jobs)} opportunities found; {len(eligible)} meet your rules.')
            for job in eligible:
                if stop.is_set():
                    break
                save(('Applying to ' if p.autoApply else 'Preparing resume for ') + job['company'])
                try:
                    result = await request('/applications/' + quote(job['job_id'], safe='') +
                        ('/auto-apply' if p.autoApply else '/tailor'), {})
                    label = outcome(result) if p.autoApply else 'PREPARED'
                    save(f"{job['company']}: {label.lower().replace('_', ' ')}.")
                except Exception as exc:
                    save(f"{job['company']}: needs review — {exc}")
            save('Agent paused.' if stop.is_set() else 'Run complete. Review Applications for results.',
                 status='paused' if stop.is_set() else 'complete')
        except Exception as exc:
            save(str(exc), status='failed')
