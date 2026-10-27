import asyncio
import json
import os
import tempfile
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from unittest.mock import patch

import app


def request_app(method: str, path: str, query: str = "", body: dict | None = None, cookie: str = ""):
    async def send_request():
        response_messages = []
        request_body = json.dumps(body).encode("utf-8") if body is not None else b""
        body_sent = False
        headers = [(b"host", b"testserver")]
        if body is not None:
            headers.append((b"content-type", b"application/json"))
        if cookie:
            headers.append((b"cookie", cookie.encode("ascii")))

        async def receive():
            nonlocal body_sent
            if body_sent:
                return {"type": "http.disconnect"}
            body_sent = True
            return {"type": "http.request", "body": request_body, "more_body": False}

        async def send(message):
            response_messages.append(message)

        await app.app(
            {
                "type": "http",
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": path,
                "raw_path": path.encode("utf-8"),
                "query_string": query.encode("ascii"),
                "headers": headers,
                "client": ("test", 0),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )
        start = next(message for message in response_messages if message["type"] == "http.response.start")
        response_body = b"".join(
            message.get("body", b"")
            for message in response_messages
            if message["type"] == "http.response.body"
        )
        return start["status"], dict(start["headers"]), response_body

    return asyncio.run(send_request())


class TeacherAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.credentials_path = Path(self.temp_dir.name) / "teachers.json"
        self.credentials_path.write_text(
            __import__("json").dumps(
                [{"username": "teacher", **app.hash_teacher_password("a-secure-password") }]
            ),
            encoding="utf-8",
        )
        self.credentials_patch = patch.object(app, "TEACHER_CREDENTIALS_FILE", self.credentials_path)
        self.credentials_patch.start()
        self.environment_patch = patch.dict(
            os.environ, {"TEACHER_SESSION_SECRET": "test-secret-that-is-at-least-32-bytes"}
        )
        self.environment_patch.start()

    def tearDown(self) -> None:
        self.environment_patch.stop()
        self.credentials_patch.stop()
        self.temp_dir.cleanup()

    def test_activity_list_remains_public_and_mutations_require_teacher(self) -> None:
        original_participants = list(app.activities["Chess Club"]["participants"])
        status, _, body = request_app("GET", "/activities")

        self.assertEqual(status, 200)
        self.assertIn(b"Chess Club", body)

        status, _, body = request_app(
            "POST", "/activities/Chess Club/signup", "email=new-student%40mergington.edu"
        )
        self.assertEqual(status, 401)
        self.assertEqual(app.activities["Chess Club"]["participants"], original_participants)

        status, _, _ = request_app(
            "DELETE", "/activities/Chess Club/unregister", "email=michael%40mergington.edu"
        )
        self.assertEqual(status, 401)
        self.assertEqual(app.activities["Chess Club"]["participants"], original_participants)

    def test_teacher_login_allows_registration_mutations(self) -> None:
        status, headers, body = request_app(
            "POST",
            "/auth/login",
            body={"username": "teacher", "password": "a-secure-password"},
        )

        self.assertEqual(status, 200)
        cookie = SimpleCookie()
        cookie.load(headers[b"set-cookie"].decode("ascii"))
        session_cookie = cookie[app.TEACHER_SESSION_COOKIE]
        self.assertTrue(session_cookie["httponly"])
        self.assertEqual(json.loads(body)["username"], "teacher")

        status, _, _ = request_app(
            "POST",
            "/activities/Chess Club/signup",
            "email=new-student%40mergington.edu",
            cookie=f"{app.TEACHER_SESSION_COOKIE}={session_cookie.value}",
        )
        self.assertEqual(status, 200)
        app.activities["Chess Club"]["participants"].remove("new-student@mergington.edu")


if __name__ == "__main__":
    unittest.main()