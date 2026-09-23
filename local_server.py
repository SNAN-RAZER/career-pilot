"""Single-process, loopback-only Career Pilot with a same-origin API."""
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
os.environ.setdefault('CAREER_PILOT_GATEWAY_TOKEN', secrets.token_urlsafe(48))

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from app.api.setup import router as setup_router
from app.api.runs import router as runs_router, active
from pilot_gateway import app as guarded, upstream, TOKEN

upstream.include_router(setup_router)
upstream.include_router(runs_router)


class LocalAPI:
    async def __call__(self, scope, receive, send):
        path = scope['path'].removeprefix('/api/career') or '/'
        if path == '/status':
            return await JSONResponse({'connected': True, 'configured': True,
                'local': True, 'message': 'Local agent connected. Configure and test your models in Agent settings.'})(scope, receive, send)
        scope = dict(scope, path=path, raw_path=path.encode(), root_path='')
        scope['headers'] = [(k, v) for k, v in scope['headers'] if k != b'authorization'] + [
            (b'authorization', ('Bearer ' + TOKEN).encode())]
        if scope['method'] not in ('GET', 'HEAD') and active() and not path.startswith('/runs/'):
            return await JSONResponse({'detail': 'Pause your agent and wait for its current action before making changes.'}, status_code=409)(scope, receive, send)
        await guarded(scope, receive, send)


class LoopbackBoundary:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            headers = dict(scope.get('headers', []))
            host = headers.get(b'host', b'').decode()
            origin = headers.get(b'origin', b'').decode()
            allowed = {'127.0.0.1', 'localhost', '::1'}
            valid = urlsplit('http://' + host).hostname in allowed
            if origin:
                valid = valid and origin in {f'http://{host}', 'http://127.0.0.1:5173', 'http://localhost:5173'}
            if headers.get(b'sec-fetch-site') == b'cross-site':
                valid = False
            if not valid:
                return await JSONResponse({'detail': 'Use Career Pilot on localhost.'}, status_code=403)(scope, receive, send)
        await self.inner(scope, receive, send)


web = ROOT / 'career-pilot-web' / 'dist-local'
routes = [Mount('/api/career', app=LocalAPI())]
if web.exists():
    routes.append(Mount('/', app=StaticFiles(directory=web, html=True)))
app = LoopbackBoundary(Starlette(routes=routes))
