"""Place beside the upstream app/ directory; run uvicorn pilot_gateway:app.

Single-owner token boundary, one-at-a-time mutations, and conservative durable
submission protection. It deliberately does not hide MFA or browser blockers.
"""
import json
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path

from dotenv import load_dotenv
from starlette.responses import JSONResponse, Response
from app.main import app as upstream

load_dotenv()
TOKEN = os.environ.get("CAREER_PILOT_GATEWAY_TOKEN", "")
if len(TOKEN) < 32:
    raise RuntimeError("Set CAREER_PILOT_GATEWAY_TOKEN to a random secret of at least 32 characters.")
DB = Path(os.environ.get("CAREER_PILOT_GATEWAY_DB", "data/pilot_gateway.sqlite3"))
DB.parent.mkdir(parents=True, exist_ok=True)


def database():
    connection = sqlite3.connect(DB, timeout=10)
    connection.execute("CREATE TABLE IF NOT EXISTS submissions (job_id TEXT PRIMARY KEY, outcome TEXT NOT NULL, response TEXT NOT NULL, created REAL NOT NULL)")
    connection.execute("CREATE TABLE IF NOT EXISTS mutation_lock (id INTEGER PRIMARY KEY CHECK(id=1), started REAL NOT NULL)")
    return connection


def outcome(result):
    detail = str(result.get("detail", result.get("message", ""))).lower()
    if any(word in detail for word in ("filled", "prepared", "submit in chrome")):
        return "PREPARED"
    status = str(result.get("status", "")).lower()
    if status in ("applied", "submitted"):
        return "APPLIED"
    if status in ("failed", "skipped"):
        return "NEEDS_REVIEW"
    return "UNCERTAIN"


class PilotGateway:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.inner(scope, receive, send)
        headers = dict(scope.get("headers", []))
        expected = ("Bearer " + TOKEN).encode()
        if not secrets.compare_digest(headers.get(b"authorization", b""), expected):
            return await JSONResponse({"detail": "Agent authentication required."}, status_code=401)(scope, receive, send)
        path = scope.get("path", "")
        method = scope.get("method", "GET")
        mutation = method not in ("GET", "HEAD", "OPTIONS") and not path.startswith('/runs/')
        # Submission routes are deliberately restricted to the guarded action.
        if mutation and re.fullmatch(r"/applications/(bulk-apply|[^/]+/(apply|web-apply|company-apply))", path):
            return await JSONResponse({"detail": "Use the guarded auto-apply action."}, status_code=403)(scope, receive, send)
        match = re.fullmatch(r"/applications/([^/]+)/auto-apply", path) if method == "POST" else None
        job_id = match.group(1) if match else None
        db = database()
        locked = False
        try:
            if mutation:
                db.execute("BEGIN IMMEDIATE")
                if db.execute("SELECT 1 FROM mutation_lock WHERE id=1").fetchone():
                    db.rollback()
                    return await JSONResponse({"detail": "Another action is running or was interrupted. Reconcile its outcome before starting another."}, status_code=409)(scope, receive, send)
                if job_id:
                    previous = db.execute("SELECT outcome, response FROM submissions WHERE job_id=?", (job_id,)).fetchone()
                    if previous:
                        db.rollback()
                        if previous[0] in ("APPLIED", "PREPARED"):
                            return await JSONResponse(json.loads(previous[1]))(scope, receive, send)
                        return await JSONResponse({"detail": "This role has a previous or uncertain submission attempt. Review it before retrying."}, status_code=409)(scope, receive, send)
                    db.execute("INSERT INTO submissions VALUES (?, 'IN_PROGRESS', '{}', ?)", (job_id, time.time()))
                db.execute("INSERT INTO mutation_lock VALUES (1, ?)", (time.time(),))
                db.commit()
                locked = True
            chunks = []
            start = None

            async def capture(message):
                nonlocal start
                if message["type"] == "http.response.start":
                    start = message
                elif message["type"] == "http.response.body":
                    chunks.append(message.get("body", b""))

            await self.inner(scope, receive, capture)
            raw = b"".join(chunks)
            status = start["status"] if start else 502
            try:
                data = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                data = None
            if job_id:
                state = outcome(data) if status < 400 and isinstance(data, dict) else "UNCERTAIN"
                db.execute("UPDATE submissions SET outcome=?, response=? WHERE job_id=?", (state, json.dumps(data or {}), job_id))
                db.commit()
            # Include guarded outcomes in the existing dashboard contract.
            if method == "GET" and status == 200 and (path == "/applications" or re.fullmatch(r"/applications/[^/]+", path)):
                entries = data if isinstance(data, list) else [data]
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    remembered = db.execute("SELECT outcome, response FROM submissions WHERE job_id=?", (entry.get("job_id"),)).fetchone()
                    if remembered and entry.get("status") == "PENDING":
                        entry["status"] = remembered[0] if remembered[0] in ("APPLIED", "PREPARED") else "NEEDS_REVIEW"
                        entry["apply_message"] = json.loads(remembered[1]).get("detail", "A previous attempt needs review.")
                    elif entry.get("status") == "PENDING" and entry.get("tailored_summary"):
                        entry["status"] = "PREPARED"
                raw = json.dumps(data).encode()
            response_headers = {k.decode(): v.decode() for k, v in (start or {}).get("headers", []) if k.lower() not in (b"content-length", b"transfer-encoding")}
            response_headers["cache-control"] = "no-store"
            return await Response(raw, status_code=status, headers=response_headers)(scope, receive, send)
        finally:
            if locked:
                db.execute("DELETE FROM mutation_lock WHERE id=1")
                db.commit()
            db.close()


app = PilotGateway(upstream)
