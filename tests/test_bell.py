"""The bell against a fake Switch agent API."""

from __future__ import annotations

import json
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import bell  # noqa: E402

AGENT_ID = "agt_bell_123"
API_KEY = "sk-test-key"
ROOMS = [
    {"room_id": "!desk:switch", "name": "cs12b-teacher-desk", "description": "", "connected": False},
    {"room_id": "!class:switch", "name": "cs12b-class", "description": "", "connected": False},
]


class FakeSwitch(BaseHTTPRequestHandler):
    posted: list[dict] = []
    auths: list[str] = []
    message_status = 200

    def log_message(self, *args):  # keep test output clean
        pass

    def _send(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        return self._send(404, {"detail": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        auth = self.headers.get("Authorization", "")
        FakeSwitch.auths.append(auth)
        if auth != f"Bearer {API_KEY}":
            return self._send(401, {"detail": "invalid api key"})
        if self.path == f"/agents/{AGENT_ID}/ops/list_rooms":
            assert body == {}
            return self._send(200, {"result": ROOMS})
        if self.path == f"/agents/{AGENT_ID}/message":
            if FakeSwitch.message_status != 200:
                return self._send(FakeSwitch.message_status, {"detail": "nope"})
            FakeSwitch.posted.append(body)
            return self._send(200, {"ok": True, "event_id": "$evt1"})
        return self._send(404, {"detail": "no route"})


@pytest.fixture()
def server():
    FakeSwitch.posted = []
    FakeSwitch.auths = []
    FakeSwitch.message_status = 200
    httpd = HTTPServer(("127.0.0.1", 0), FakeSwitch)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def cfg(base: str, **over) -> bell.Config:
    values = dict(base_url=base, agent_id=AGENT_ID, api_key=API_KEY, room="cs12b-teacher-desk",
                  text=bell.DEFAULT_TEXT)
    values.update(over)
    return bell.Config(**values)


def test_posts_morning_ping_to_the_desk(server):
    out = bell.ring(cfg(server), dry_run=False, now=datetime(2026, 11, 5, 7, 0))
    assert FakeSwitch.posted == [
        {"room_id": "!desk:switch", "content": "@radar morning: time for today's Radar card (Thu 05 Nov)."}
    ]
    assert "posted to cs12b-teacher-desk" in out
    assert all(a == f"Bearer {API_KEY}" for a in FakeSwitch.auths)


def test_dry_run_posts_nothing(server):
    out = bell.ring(cfg(server), dry_run=True)
    assert FakeSwitch.posted == []
    assert out.startswith("[dry run]")


def test_room_matched_by_id_and_case_insensitive_name(server):
    bell.ring(cfg(server, room="!class:switch"), dry_run=False)
    bell.ring(cfg(server, room="CS12B-Teacher-Desk"), dry_run=False)
    assert [p["room_id"] for p in FakeSwitch.posted] == ["!class:switch", "!desk:switch"]


def test_unknown_room_names_the_rooms_it_is_in(server):
    with pytest.raises(bell.BellError) as err:
        bell.ring(cfg(server, room="cs12b-staff"), dry_run=False)
    assert "cs12b-class" in str(err.value) and "invite-agent" in str(err.value)


def test_bad_key_is_explained(server):
    with pytest.raises(bell.BellError) as err:
        bell.ring(cfg(server, api_key="wrong"), dry_run=False)
    assert "401" in str(err.value)


def test_not_a_member_is_explained(server):
    FakeSwitch.message_status = 403
    with pytest.raises(bell.BellError) as err:
        bell.ring(cfg(server), dry_run=False)
    assert "invite-agent" in str(err.value)


def test_unreachable_server_is_explained():
    with pytest.raises(bell.BellError) as err:
        bell.ring(cfg("http://127.0.0.1:9"), dry_run=False)
    assert "can't reach Switch" in str(err.value)


def test_env_file_and_flags(tmp_path, monkeypatch):
    env = tmp_path / "bell.env"
    env.write_text(
        "# comment\nSWITCH_URL='http://127.0.0.1:8000/'\nBELL_AGENT_ID=a1\nBELL_API_KEY=\"k1\"\n"
    )
    for key in ("SWITCH_URL", "BELL_AGENT_ID", "BELL_API_KEY", "BELL_ROOM", "BELL_TEXT"):
        monkeypatch.delenv(key, raising=False)
    parser_args = type("A", (), dict(env_file=str(env), base_url=None, agent_id=None, room="desk-x", text=None))
    c = bell.resolve_config(parser_args)
    assert (c.base_url, c.agent_id, c.api_key, c.room) == ("http://127.0.0.1:8000", "a1", "k1", "desk-x")
    assert c.text == bell.DEFAULT_TEXT


def test_missing_config_is_explained(tmp_path, monkeypatch):
    for key in ("SWITCH_URL", "BELL_AGENT_ID", "BELL_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    parser_args = type("A", (), dict(env_file=str(tmp_path / "none.env"), base_url=None, agent_id=None, room=None, text=None))
    with pytest.raises(bell.BellError) as err:
        bell.resolve_config(parser_args)
    assert "BELL_API_KEY" in str(err.value)
