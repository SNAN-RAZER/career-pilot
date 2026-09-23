"""User-facing local launcher; installs missing dependencies and serves the app."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
WEB = ROOT / 'career-pilot-web'
NOPE_REVISION = '8c3d7f55ee34d4ea6fabd950598b66628b49db41'


def run(args, cwd=ROOT):
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def main():
    os.chdir(ROOT)
    if sys.version_info < (3, 12):
        raise RuntimeError('Install Python 3.12 or newer.')
    url = 'http://127.0.0.1:8765'
    venv = ROOT / '.venv'
    python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if Path(sys.prefix).resolve() != venv.resolve():
        if not python.exists():
            run([sys.executable, '-m', 'venv', venv])
        run([python, Path(__file__).resolve()])
        return
    required = ['fastapi', 'uvicorn', 'pydantic_settings', 'qdrant_client', 'multipart',
                'playwright', 'httpcloak', 'curl_cffi', 'Crypto', 'docx', 'pypdf', 'httpx', 'dotenv']
    if any(importlib.util.find_spec(name) is None for name in required):
        print('Installing backend dependencies. First launch may take several minutes.', flush=True)
        run([python, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    source = ROOT / 'third_party/NopeRi'
    if not source.exists():
        run(['git', 'clone', 'https://github.com/Traverser25/NopeRi.git', source])
        run(['git', '-C', source, 'checkout', NOPE_REVISION])
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Install Node.js 22 or newer, then relaunch.')
    # Resolve dependencies from this checkout (or an existing parent workspace).
    probe = subprocess.run([node, '-e', "require.resolve('vite/package.json')"], cwd=WEB,
                           capture_output=True)
    if probe.returncode:
        npm = Path(node).parent / 'node_modules/npm/bin/npm-cli.js'
        if npm.exists():
            run([node, npm, 'ci'], WEB)
        else:
            raise RuntimeError('Run npm ci in career-pilot-web, then relaunch.')
    print('Building your local workspace…', flush=True)
    run([node, 'scripts/build-local.mjs'], WEB)
    try:
        with urllib.request.urlopen(url + '/api/career/status', timeout=2) as response:
            if response.status == 200:
                webbrowser.open(url)
                print('Career Pilot is already running:', url)
                return
    except OSError:
        pass
    def open_when_ready():
        for _ in range(60):
            try:
                with urllib.request.urlopen(url + '/api/career/status', timeout=1):
                    webbrowser.open(url)
                    return
            except OSError:
                time.sleep(0.5)
    threading.Thread(target=open_when_ready, daemon=True).start()
    print(f'Career Pilot: {url}\nKeep this window open. Press Ctrl+C to stop.', flush=True)
    import uvicorn
    uvicorn.run('local_server:app', host='127.0.0.1', port=8765, log_level='info')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError) as exc:
        print(f'Could not start Career Pilot: {exc}', file=sys.stderr)
        sys.exit(1)
