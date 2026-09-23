"""Local configuration; credentials never appear in responses."""
import os
import importlib.util
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from dotenv import set_key
from app.api.dependencies import application_dependencies
from app.llm.lmstudio_client import LMStudioClient
from app.llm.provider_store import get_active, public_provider

router = APIRouter(prefix='/setup', tags=['setup'])


def missing_dependencies():
    return [package for module, package in [('Crypto', 'pycryptodome'), ('httpcloak', 'httpcloak'),
            ('playwright', 'playwright')] if importlib.util.find_spec(module) is None]


class Account(BaseModel):
    username: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


@router.get('/status')
def status():
    return {
        'provider': public_provider(get_active()),
        'account_configured': bool(os.getenv('NAUKRI_USERNAME') and os.getenv('NAUKRI_PASSWORD')),
        'job_source_installed': Path('third_party/NopeRi/src/client/naukri_client.py').exists(),
        'profile_saved': Path('data/profile/candidate.json').exists(),
        'missing_dependencies': missing_dependencies(),
    }


@router.post('/account')
def save_account(payload: Account):
    for key, value in [('NAUKRI_USERNAME', payload.username.strip()), ('NAUKRI_PASSWORD', payload.password)]:
        set_key('.env', key, value)
        os.environ[key] = value
    application_dependencies.reset_naukri_client()
    return {'status': 'saved', 'message': 'Account saved locally in .env.'}


@router.post('/test-account')
def test_account():
    missing = missing_dependencies()
    if missing:
        raise HTTPException(400, 'Missing packages: ' + ', '.join(missing) + '. Double-click Start Career Pilot.cmd to install them.')
    try:
        application_dependencies.reset_naukri_client()
        application_dependencies.get_naukri_client()
        return {'status': 'ok', 'message': 'Naukri login succeeded.'}
    except Exception:
        raise HTTPException(400, 'Naukri login failed. Check your credentials and complete any verification on Naukri before retrying.')


@router.post('/test-model')
def test_model():
    client = LMStudioClient()
    if not client.reachable():
        raise HTTPException(400, 'Model server is unavailable. Start LM Studio or Ollama and check its server URL.')
    if not client.llm_model or not client.embedding_model:
        raise HTTPException(400, 'Select both a chat model and an embedding model, then save.')
    try:
        reply = client.chat([{'role': 'user', 'content': 'Reply with OK.'}], max_tokens=64)
        if not reply.strip():
            raise ValueError('Chat model returned an empty response.')
        vector = client.embed('Career Pilot connection test')
        if not vector:
            raise ValueError('Embedding model returned no vector.')
    except Exception as exc:
        raise HTTPException(400, f'Model test failed ({type(exc).__name__}). Check the model IDs and server logs.') from exc
    return {'status': 'ok', 'message': f'Chat and embeddings work. Embedding dimensions: {len(vector)}.'}
