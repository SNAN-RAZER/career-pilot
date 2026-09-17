"""Integration-check the gateway against a fake ASGI agent; never contacts employers."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "work/gateway-test-deps"))
from starlette.responses import JSONResponse


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        os.environ["CAREER_PILOT_GATEWAY_TOKEN"] = "test-token-not-a-secret-12345678901234567890"
        os.environ["CAREER_PILOT_GATEWAY_DB"] = str(Path(self.temp.name) / "gateway.sqlite3")
        self.calls = 0
        self.behavior = "filled"

        async def fake(scope, receive, send):
            if scope["path"].endswith("/auto-apply"):
                self.calls += 1
                if self.behavior == "crash":
                    raise RuntimeError("Uncertain upstream submission")
                result = {"status": "applied", "detail": "Web agent (filled)" if self.behavior == "filled" else "Naukri Easy Apply"}
            elif scope["path"] == "/applications":
                result = [{"job_id": "123", "status": "PENDING", "title": "Test role"}]
            else:
                result = {"status": "ok", "service": "career-pilot"}
            await JSONResponse(result)(scope, receive, send)

        stub = types.ModuleType("app.main")
        stub.app = fake
        sys.modules["app.main"] = stub
        spec = importlib.util.spec_from_file_location("pilot_gateway_under_test", ROOT / "integrations/pilot_gateway.py")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.gateway = self.module.app

    def tearDown(self):
        self.temp.cleanup()

    async def request(self, path, method="GET", token=True):
        messages = []
        async def send(message):
            messages.append(message)
        async def receive():
            return {"type": "http.request", "body": b"{}", "more_body": False}
        headers = [(b"authorization", ("Bearer " + os.environ["CAREER_PILOT_GATEWAY_TOKEN"]).encode())] if token else []
        await self.gateway({"type": "http", "method": method, "path": path, "headers": headers}, receive, send)
        status = next(m["status"] for m in messages if m["type"] == "http.response.start")
        data = json.loads(b"".join(m.get("body", b"") for m in messages))
        return status, data

    async def test_authentication_and_unguarded_routes(self):
        self.assertEqual((await self.request("/health", token=False))[0], 401)
        self.assertEqual((await self.request("/health"))[0], 200)
        self.assertEqual((await self.request("/applications/123/apply", "POST"))[0], 403)
        self.assertEqual(self.calls, 0)

    async def test_filled_result_is_durable_and_does_not_resubmit(self):
        await self.request("/applications/123/auto-apply", "POST")
        await self.request("/applications/123/auto-apply", "POST")
        self.assertEqual(self.calls, 1)
        status, records = await self.request("/applications")
        self.assertEqual(status, 200)
        self.assertEqual(records[0]["status"], "PREPARED")

    async def test_confirmed_result_replays_and_counts_as_applied(self):
        self.behavior = "success"
        await self.request("/applications/123/auto-apply", "POST")
        await self.request("/applications/123/auto-apply", "POST")
        self.assertEqual(self.calls, 1)
        self.assertEqual((await self.request("/applications"))[1][0]["status"], "APPLIED")

    async def test_uncertain_submission_cannot_be_blindly_retried(self):
        self.behavior = "crash"
        with self.assertRaises(RuntimeError):
            await self.request("/applications/123/auto-apply", "POST")
        self.behavior = "success"
        self.assertEqual((await self.request("/applications/123/auto-apply", "POST"))[0], 409)
        self.assertEqual(self.calls, 1)
        self.assertEqual((await self.request("/applications"))[1][0]["status"], "NEEDS_REVIEW")

    async def test_running_mutation_blocks_second_action(self):
        with self.module.database() as db:
            db.execute("INSERT INTO mutation_lock VALUES (1, 123)")
        db.close()
        self.assertEqual((await self.request("/profile/store", "POST"))[0], 409)

if __name__ == "__main__":
    unittest.main()
