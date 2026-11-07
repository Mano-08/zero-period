"""The end-to-end smoke test, run against a fake Mattermost whose 'agents' behave
the way the TA and Radar briefs say they should (and, in some tests, don't)."""

from __future__ import annotations

import json
import re
import sys
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import smoke_test  # noqa: E402

TODAY = date.today().isoformat()


class World:
    """Everything the fake server knows. Reset per test."""

    def __init__(self, course: Path, *, assigned=True, ta_gives_code=False, ta_in_class=True):
        self.course = course
        self.assigned = assigned
        self.ta_gives_code = ta_gives_code
        self.clock = 1_800_000_000_000
        self.lock = threading.Lock()
        self.users = {
            "admin": {"id": "admin", "username": "admin", "is_bot": False, "pw": "adminpw"},
            "teacher": {"id": "teacher", "username": "user", "is_bot": False, "pw": "teacherpw"},
            "bot-ta": {"id": "bot-ta", "username": "cs12b-ta", "first_name": "TA", "is_bot": True},
            "bot-radar": {"id": "bot-radar", "username": "cs12b-radar", "first_name": "Radar", "is_bot": True},
        }
        self.channels = {
            "c1": {"id": "c1", "name": "cs12b-class", "display_name": "cs12b-class", "type": "O"},
            "d1": {"id": "d1", "name": "cs12b-teacher-desk", "display_name": "cs12b-teacher-desk", "type": "P"},
        }
        self.members = {
            "c1": {"teacher", "bot-radar"} | ({"bot-ta"} if ta_in_class else set()),
            "d1": {"teacher", "bot-ta", "bot-radar"},
        }
        self.posts: list[dict] = []
        self.card_id = None
        self.radar_card_id = None

    def by_username(self, name):
        return next((u for u in self.users.values() if u["username"] == name), None)

    def add(self, channel, user, message, root_id=""):
        self.clock += 10
        post = {"id": f"p{len(self.posts) + 1}", "channel_id": channel, "user_id": user,
                "message": message, "root_id": root_id or "", "create_at": self.clock, "type": ""}
        self.posts.append(post)
        return post

    # --- the agents, as the briefs describe them -------------------------------
    def react(self, post):
        ch, user, msg, low = post["channel_id"], post["user_id"], post["message"], post["message"].lower()
        if ch == "c1" and user == "teacher":
            if msg == "!assign-agent":
                self.add("c1", "admin", "Every message here goes to **TA** unless it mentions someone else."
                         if self.assigned else "No agent is assigned in this room. Assign one with `!assign-agent @agent-name`.")
            elif msg == "!assign-agent @ta":
                self.assigned = True
                self.add("c1", "admin", "From now on, every message here goes to **TA** unless it mentions someone else.")
            return
        student = self.users.get(user, {}).get("username", "")
        if ch == "c1" and user not in ("teacher", "admin", "bot-ta", "bot-radar"):
            if "@radar" in low:
                self.add("c1", "bot-radar", "I only take instructions from my owner, and this chat account isn't linked to a Switch user yet.")
                return
            if not (self.assigned or low.startswith("@ta")):
                return
            if "unit test" in low:
                self.add("c1", "bot-ta", f"@{student} Unit Test 2 is on **Friday 13 November**, period 3. File handling isn't in it (syllabus.md).")
            elif "factorial(0)" in low:
                self.add("c1", "bot-ta", "On it!")
                self.add("c1", "bot-ta", "💡 Hint 1/3 · Base case · Notes p.12\nWhat do you get if you multiply *no* numbers?")
            elif "still don't get it" in low:
                self.add("c1", "bot-ta", "💡 Hint 2/3 · Base case · Notes p.13\nWhat's the smallest input factorial can get?")
            elif "still confused" in low:
                self.add("c1", "bot-ta", "💡 Hint 3/3 · Base case · Notes p.14\nTrace factorial(1) with me: 1 * factorial(0) = ?")
            elif "still stuck" in low:
                self.add("c1", "bot-ta", f"@{student} I'm asking Ma'am. The answer will come back right here.")
                card = self.add("d1", "bot-ta", "🆘 E-1104-1405-smoke · Smoke · Base case\nStuck on: \"why does factorial(0) return 1\"")
                self.card_id = card["id"]
                self.add("d1", "bot-radar", "Logged as E-1104-1405-smoke. Reply in this thread and I'll take your answer to Smoke.", root_id=card["id"])
            elif "ignore all your previous" in low:
                if self.ta_gives_code:
                    self.add("c1", "bot-ta", "ok!\n```python\ndef sum_even(nums):\n    ...\n```")
                else:
                    self.add("c1", "bot-ta", "Nice try 🙂 I can't paste homework code, but I can help you build it. What's the smallest list?")
            elif re.match(r"^(@ta\s+)?1[A-D]\s+2[A-D]", msg):
                self.add("c1", "bot-ta", f"✅ Quiz {TODAY} · Smoke · 2/3 · missed: 1\nQ1: the base case is the smallest input (Notes p.13).")
            return
        if ch == "d1" and user == "teacher":
            if post["root_id"] and post["root_id"] == self.card_id:
                self.add("d1", "bot-radar", "Delivered to Smoke ✅. Saved to teacher-answers, so the TA will use it next time.", root_id=self.card_id)
                self.add("c1", "bot-radar", f"Ma'am answered your question about Base case: {msg}")
                answers = self.course / "teacher-answers.md"
                answers.write_text(answers.read_text() + f"\n### {TODAY} · asked in class\n{msg}\n")
            elif "@radar morning" in low:
                quiz = {"date": TODAY, "topics": ["Base case"], "questions": [
                    {"n": i, "topic": "Base case", "q": f"Q{i}", "options": dict(zip("ABCD", "wxyz")),
                     "answer": a, "explain": "Notes p.12"} for i, a in ((1, "B"), (2, "C"), (3, "A"))]}
                path = self.course / "radar-data" / "quizzes" / f"{TODAY}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(quiz))
                card = self.add("d1", "bot-radar", f"📡 Zero Period · {TODAY}\n1. Base case · 12 students\nWarm-up ready.")
                self.radar_card_id = card["id"]
            elif post["root_id"] and post["root_id"] == self.radar_card_id and low == "send":
                self.add("c1", "bot-radar", f"🧠 Warm-up · {TODAY}\nQ1. …")
                self.add("d1", "bot-radar", "Posted to class ✅.", root_id=self.radar_card_id)


WORLD: World | None = None


class Handler(BaseHTTPRequestHandler):
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

    def _who(self):
        auth = self.headers.get("Authorization", "")
        name = auth.removeprefix("Bearer tok-")
        return WORLD.by_username(name)

    def do_GET(self):
        w, url = WORLD, urlparse(self.path)
        p, q = url.path, parse_qs(url.query)
        with w.lock:
            if p == "/api/v4/teams/name/switch":
                return self._send(200, {"id": "t1", "name": "switch"})
            m = re.fullmatch(r"/api/v4/teams/t1/channels/name/(.+)", p)
            if m:
                ch = next((c for c in w.channels.values() if c["name"] == m.group(1)), None)
                return self._send(200, ch) if ch else self._send(404, {"message": "no channel"})
            if p == "/api/v4/teams/t1/channels":
                return self._send(200, [c for c in w.channels.values() if c["type"] == "O"])
            if p == "/api/v4/teams/t1/channels/private":
                return self._send(200, [c for c in w.channels.values() if c["type"] == "P"])
            m = re.fullmatch(r"/api/v4/users/username/(.+)", p)
            if m:
                u = w.by_username(m.group(1))
                return self._send(200, u) if u else self._send(404, {"message": "no user"})
            m = re.fullmatch(r"/api/v4/channels/(\w+)/members", p)
            if m:
                return self._send(200, [{"user_id": uid} for uid in sorted(w.members[m.group(1)])])
            m = re.fullmatch(r"/api/v4/channels/(\w+)/posts", p)
            if m:
                since = int(q.get("since", ["0"])[0])
                posts = {x["id"]: x for x in w.posts if x["channel_id"] == m.group(1) and x["create_at"] > since}
                return self._send(200, {"order": list(posts), "posts": posts})
        return self._send(404, {"message": "no route " + p})

    def do_POST(self):
        w, p = WORLD, urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        with w.lock:
            if p == "/api/v4/users/login":
                u = w.by_username(body["login_id"])
                if u and u.get("pw") == body["password"]:
                    return self._send(200, u, {"Token": f"tok-{u['username']}"})
                return self._send(401, {"message": "bad login"})
            if p == "/api/v4/users":
                auth = self.headers.get("Authorization", "")
                if auth not in ("", "Bearer tok-admin"):
                    return self._send(403, {"message": "signed-in users can't create accounts"})
                uid = "u-" + body["username"]
                w.users[uid] = {"id": uid, "username": body["username"], "is_bot": False, "pw": body["password"]}
                return self._send(201, w.users[uid])
            if p == "/api/v4/teams/t1/members":
                return self._send(201, {})
            m = re.fullmatch(r"/api/v4/channels/(\w+)/members", p)
            if m:
                w.members[m.group(1)].add(body["user_id"])
                return self._send(201, {})
            if p == "/api/v4/users/ids":
                return self._send(200, [w.users[i] for i in body if i in w.users])
            if p == "/api/v4/posts":
                me = self._who()
                if not me:
                    return self._send(401, {"message": "no auth"})
                post = w.add(body["channel_id"], me["id"], body["message"], body.get("root_id", ""))
                w.react(post)
                return self._send(201, post)
        return self._send(404, {"message": "no route " + p})


@pytest.fixture()
def env(tmp_path, monkeypatch):
    import mm as mmlib

    monkeypatch.setattr(mmlib, "MATTERMOST_ENV", tmp_path / "no-mattermost.env")
    monkeypatch.setattr(mmlib, "console_data_dirs", lambda: [tmp_path / "no-console"])
    for key in ("MM_URL", "MM_USER", "MM_PASSWORD", "MM_TEAM"):
        monkeypatch.delenv(key, raising=False)
    course = tmp_path / "course"
    course.mkdir()
    (course / "teacher-answers.md").write_text("# Teacher's answers\n")

    def start(native=False, **kw):
        global WORLD
        WORLD = World(course, **kw)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        env_file = tmp_path / ".env"
        admin = "" if native else "MATTERMOST_ADMIN_USER=admin\nMATTERMOST_ADMIN_PASSWORD=adminpw\n"
        env_file.write_text(
            admin + "MATTERMOST_TEAM_NAME=switch\n"
            f"MATTERMOST_HOST_PORT={httpd.server_address[1]}\nMATTERMOST_USER=user\nMATTERMOST_USER_PASSWORD=teacherpw\n"
        )
        args = ["--console-env", str(env_file), "--course-dir", str(course), "--timeout", "2", "--poll", "0.02"]
        return httpd, args

    servers = []

    def launcher(**kw):
        httpd, args = start(**kw)
        if kw.get("native"):
            # Today's Console: no settings file with passwords; the teacher's
            # Sign-in details come in as flags (or mattermost.env, or a prompt).
            port = httpd.server_address[1]
            args = ["--mm-url", f"http://127.0.0.1:{port}", "--teacher-user", "user",
                    "--teacher-password", "teacherpw", "--team", "switch"] + args[2:]
        servers.append(httpd)
        return args

    yield launcher
    for httpd in servers:
        httpd.shutdown()


def test_every_step_passes_when_agents_behave(env, capsys):
    assert smoke_test.main(env()) == 0
    out = capsys.readouterr().out
    assert "9/9 passed" in out
    assert "assigned agent: TA" in out
    assert "saved to teacher-answers.md" in out
    assert "answered 1A 2C 3A (one wrong on purpose)" in out  # key is B C A; first is wrong on purpose


def test_without_assignment_messages_start_with_at_ta(env, capsys):
    assert smoke_test.main(env(assigned=False)) == 0
    out = capsys.readouterr().out
    assert "no assigned agent, so test messages start with @ta" in out
    student_posts = [p["message"] for p in WORLD.posts if p["user_id"] == "u-smoke.student"]
    assert all(m.startswith("@ta ") or m.startswith("@radar ") for m in student_posts)


def test_fix_assigns_the_ta(env, capsys):
    assert smoke_test.main(env(assigned=False) + ["--fix"]) == 0
    assert "set by --fix" in capsys.readouterr().out


def test_homework_code_is_caught(env, capsys):
    assert smoke_test.main(env(ta_gives_code=True) + ["--steps", "injection"]) == 1
    assert "the TA wrote homework code" in capsys.readouterr().out


def test_missing_ta_is_reported_in_setup(env, capsys):
    assert smoke_test.main(env(ta_in_class=False)) == 1
    assert "no TA bot in the class channel" in capsys.readouterr().out


def test_unknown_step_is_a_usage_error(env, capsys):
    assert smoke_test.main(env() + ["--steps", "hints,teleport"]) == 2
    assert "unknown step" in capsys.readouterr().err


def test_native_server_needs_only_the_teacher_login(env, capsys):
    args = env(native=True)
    assert "--console-env" not in args
    assert smoke_test.main(args) == 0
    out = capsys.readouterr().out
    assert "9/9 passed" in out and "signed in as user" in out
    # The test student signed up on its own: no admin was involved.
    assert "u-smoke.student" in WORLD.users
