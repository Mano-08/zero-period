"""The demo seeder against a fake Mattermost."""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import seed_class  # noqa: E402


class FakeMattermost(BaseHTTPRequestHandler):
    users: dict[str, dict] = {}
    posts: list[tuple[str, str, str]] = []  # (token, channel, message)
    members: set[tuple[str, str]] = set()
    open_server = True

    def log_message(self, *args):
        pass

    def _send(self, status, payload=None, headers=None):
        body = json.dumps(payload).encode() if payload is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        p = self.path
        if p == "/api/v4/teams/name/switch":
            return self._send(200, {"id": "t1", "name": "switch"})
        if p == "/api/v4/teams/t1/channels/name/cs12b-class":
            return self._send(200, {"id": "c1", "name": "cs12b-class", "display_name": "cs12b-class"})
        if p.startswith("/api/v4/users/username/"):
            name = p.rsplit("/", 1)[1]
            if name in FakeMattermost.users:
                return self._send(200, FakeMattermost.users[name])
            return self._send(404, {"message": "not found"})
        return self._send(404, {"message": "no route " + p})

    def do_POST(self):
        p, body = self.path, self._body()
        auth = self.headers.get("Authorization", "")
        if p == "/api/v4/users/login":
            login = body["login_id"]
            if login == "admin" and body["password"] == "adminpw":
                return self._send(200, {"id": "admin"}, {"Token": "tok-admin"})
            if login == "user" and body["password"] == "teacherpw":
                return self._send(200, {"id": "teacher"}, {"Token": "tok-user"})
            user = FakeMattermost.users.get(login)
            if user and body["password"] == "Radar-demo-2026!":
                return self._send(200, user, {"Token": f"tok-{login}"})
            return self._send(401, {"message": "bad login"})
        if p == "/api/v4/users":
            if not (auth == "Bearer tok-admin" or (auth == "" and FakeMattermost.open_server)):
                return self._send(403, {"message": "sign-ups are off"})
            user = {"id": "u-" + body["username"], "username": body["username"]}
            FakeMattermost.users[body["username"]] = user
            return self._send(201, user)
        if p == "/api/v4/teams/t1/members" or p == "/api/v4/channels/c1/members":
            own = "Bearer tok-" + body["user_id"].removeprefix("u-")
            if auth not in ("Bearer tok-admin", own):
                return self._send(403, {"message": "can only add yourself"})
            FakeMattermost.members.add((p, body["user_id"]))
            return self._send(201, {})
        if p == "/api/v4/posts":
            FakeMattermost.posts.append((auth, body["channel_id"], body["message"]))
            return self._send(201, {"id": f"post{len(FakeMattermost.posts)}"})
        return self._send(404, {"message": "no route " + p})


@pytest.fixture()
def mm(tmp_path, monkeypatch):
    import mm as mmlib

    monkeypatch.setattr(mmlib, "MATTERMOST_ENV", tmp_path / "no-mattermost.env")
    monkeypatch.setattr(mmlib, "console_data_dirs", lambda: [tmp_path / "no-console"])
    for key in ("MM_URL", "MM_USER", "MM_PASSWORD", "MM_TEAM"):
        monkeypatch.delenv(key, raising=False)
    FakeMattermost.users, FakeMattermost.posts, FakeMattermost.members = {}, [], set()
    FakeMattermost.open_server = True
    httpd = HTTPServer(("127.0.0.1", 0), FakeMattermost)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_seeds_every_line_as_its_student(mm, tmp_path):
    env = tmp_path / ".env"
    port = mm.rsplit(":", 1)[1]
    env.write_text(
        f"MATTERMOST_ADMIN_USER=admin\nMATTERMOST_ADMIN_PASSWORD='adminpw'\n"
        f"MATTERMOST_TEAM_NAME=switch\nMATTERMOST_HOST_PORT={port}\n"
    )
    code = seed_class.main(["--console-env", str(env), "--channel", "cs12b-class", "--delay", "0"])
    assert code == 0
    assert len(FakeMattermost.users) == len(seed_class.STUDENTS)
    assert len(FakeMattermost.members) == 2 * len(seed_class.STUDENTS)
    assert [m for _, _, m in FakeMattermost.posts] == [line.text for line in seed_class.SCRIPT]
    # Each line is posted with that student's own token, never the admin's.
    for (auth, channel, _), line in zip(FakeMattermost.posts, seed_class.SCRIPT):
        assert auth == f"Bearer tok-{line.user}" and channel == "c1"


def test_second_run_reuses_accounts(mm, tmp_path):
    args = ["--mm-url", mm, "--admin-user", "admin", "--admin-password", "adminpw",
            "--team", "switch", "--delay", "0", "--console-env", str(tmp_path / "missing.env")]
    # An explicit --console-env that doesn't exist is an error, said plainly.
    assert seed_class.main(args) == 1
    args = args[:-2]
    assert seed_class.main(args) == 0
    assert seed_class.main(args) == 0
    assert len(FakeMattermost.users) == len(seed_class.STUDENTS)
    assert len(FakeMattermost.posts) == 2 * len(seed_class.SCRIPT)


def test_dry_run_posts_nothing(capsys):
    assert seed_class.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert '"messages": 60' in out


def test_students_sign_up_with_only_the_teacher_login(mm):
    # Today's Switch Console keeps the Mattermost admin password to itself, so the
    # seeder signs in as the teacher and the students sign up on their own.
    args = ["--mm-url", mm, "--teacher-user", "user", "--teacher-password", "teacherpw",
            "--team", "switch", "--delay", "0", "--accounts-only"]
    assert seed_class.main(args) == 0
    assert len(FakeMattermost.users) == len(seed_class.STUDENTS)
    assert len(FakeMattermost.members) == 2 * len(seed_class.STUDENTS)
    assert FakeMattermost.posts == []  # --accounts-only


def test_closed_sign_ups_explain_the_admin_option(mm, capsys):
    FakeMattermost.open_server = False
    args = ["--mm-url", mm, "--teacher-user", "user", "--teacher-password", "teacherpw",
            "--team", "switch", "--delay", "0", "--accounts-only"]
    assert seed_class.main(args) == 1
    assert "--admin-user" in capsys.readouterr().err


def test_no_login_at_all_says_where_to_find_it(mm, capsys):
    assert seed_class.main(["--mm-url", mm, "--team", "switch"]) == 1
    assert "Sign-in details" in capsys.readouterr().err
