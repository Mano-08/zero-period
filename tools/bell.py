#!/usr/bin/env python3
"""bell: the morning ping that wakes the Radar.

Switch has no scheduler. An agent acts when something addresses it. The bell is a
tiny agent of its own that speaks the Switch agent protocol: it posts one message
into the teacher-desk room ("@radar morning …"), and the Radar wakes up and builds
the day's Radar card. Run it from cron at 7 am.

Standard library only, so it runs on any laptop with Python 3.9+.

One-time setup (about 2 minutes):
  1. Switch dashboard → Agents → Register Agent → Type "External agent", named
     e.g. cs12b-bell. Copy its Agent ID and API Key. The key is shown once.
  2. In the teacher-desk channel, type:  !invite-agent @cs12b-bell
  3. cp bell.env.example bell.env  and fill it in.
  4. python3 tools/bell.py --dry-run   then   python3 tools/bell.py

Cron (Mon–Sat, 7:00 am):
  0 7 * * 1-6  cd /path/to/zero-period && /usr/bin/python3 tools/bell.py >> bell.log 2>&1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = ROOT / "bell.env"
DEFAULT_TEXT = "@radar morning: time for today's Radar card ({date})."
TIMEOUT_SECONDS = 20


class BellError(RuntimeError):
    """A failure with a message a teacher can act on."""


@dataclass
class Config:
    base_url: str
    agent_id: str
    api_key: str
    room: str
    text: str


def load_env_file(path: Path) -> dict[str, str]:
    """Read KEY=VALUE lines. Blank lines and # comments are skipped, and
    surrounding quotes are removed."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def resolve_config(args: argparse.Namespace) -> Config:
    """CLI flags win over environment variables, which win over the env file."""
    file_values = load_env_file(Path(args.env_file))

    def pick(flag: str | None, key: str, default: str | None = None) -> str | None:
        if flag:
            return flag
        if os.environ.get(key):
            return os.environ[key]
        return file_values.get(key, default)

    base_url = pick(args.base_url, "SWITCH_URL")
    agent_id = pick(args.agent_id, "BELL_AGENT_ID")
    api_key = pick(None, "BELL_API_KEY")
    room = pick(args.room, "BELL_ROOM", "cs12b-teacher-desk")
    text = pick(args.text, "BELL_TEXT", DEFAULT_TEXT)

    missing = [
        name
        for name, value in (
            ("SWITCH_URL", base_url),
            ("BELL_AGENT_ID", agent_id),
            ("BELL_API_KEY", api_key),
        )
        if not value
    ]
    if missing:
        raise BellError(
            f"missing {', '.join(missing)}. Set them in {args.env_file} "
            "(see bell.env.example) or in the environment."
        )
    assert base_url and agent_id and api_key and room and text
    return Config(base_url.rstrip("/"), agent_id, api_key, room, text)


def _request(
    cfg: Config, method: str, path: str, body: dict[str, Any] | None = None
) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        cfg.base_url + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "zero-period-bell/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as err:
        detail = err.read().decode(errors="replace")[:300]
        raise BellError(_explain_http(err.code, path, detail)) from err
    except urllib.error.URLError as err:
        raise BellError(
            f"can't reach Switch at {cfg.base_url} ({err.reason}). Is Switch "
            "running, and is SWITCH_URL the server's API URL (not the dashboard)?"
        ) from err
    return json.loads(raw) if raw else None


def _explain_http(status: int, path: str, detail: str) -> str:
    if status == 401:
        return (
            "Switch refused the API key (401). Check BELL_AGENT_ID and BELL_API_KEY. "
            f"The key is shown once, when the agent is registered. [{detail}]"
        )
    if status == 403:
        return (
            "the bell isn't allowed in that room (403). Type `!invite-agent @<bell-name>` "
            f"in the teacher-desk channel. [{detail}]"
        )
    if status == 404 and path.endswith("/message"):
        return f"Switch doesn't know that room (404). Check BELL_ROOM. [{detail}]"
    if status == 404:
        return (
            "404 from Switch. SWITCH_URL is probably the dashboard address, not the "
            f"API address. [{detail}]"
        )
    if status == 429:
        return f"Switch's budget for this agent is used up (429). [{detail}]"
    return f"Switch answered {status} on {path}. [{detail}]"


def check_health(cfg: Config) -> None:
    """GET /health is public: a 200 means this is the agent API base URL."""
    req = urllib.request.Request(cfg.base_url + "/health", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS):
            return
    except urllib.error.HTTPError as err:
        if err.code == 401:
            raise BellError(
                "SWITCH_URL reaches Switch but not the agent API (401 on /health). "
                "Use the server's API URL."
            ) from err
        raise BellError(f"/health answered {err.code}") from err
    except urllib.error.URLError as err:
        raise BellError(
            f"can't reach Switch at {cfg.base_url} ({err.reason}). Is the server running?"
        ) from err


def list_rooms(cfg: Config) -> list[dict[str, Any]]:
    """The rooms this agent belongs to, through the `list_rooms` operation."""
    reply = _request(cfg, "POST", f"/agents/{cfg.agent_id}/ops/list_rooms", {})
    rooms = reply.get("result") if isinstance(reply, dict) else None
    if not isinstance(rooms, list):
        raise BellError(f"unexpected list_rooms reply: {reply!r}"[:300])
    return rooms


def find_room(rooms: list[dict[str, Any]], wanted: str) -> dict[str, Any]:
    """Match by room id first, then by exact name, then by name ignoring case."""
    for room in rooms:
        if room.get("room_id") == wanted:
            return room
    for room in rooms:
        if room.get("name") == wanted:
            return room
    folded = [r for r in rooms if str(r.get("name", "")).lower() == wanted.lower()]
    if len(folded) == 1:
        return folded[0]
    names = ", ".join(sorted(str(r.get("name")) for r in rooms)) or "none"
    raise BellError(
        f"the bell isn't in a room called {wanted!r}. Rooms it is in: {names}. "
        "Invite it with `!invite-agent @<bell-name>` in the teacher-desk channel."
    )


def ring(cfg: Config, *, dry_run: bool, now: datetime | None = None) -> str:
    text = cfg.text.replace("{date}", (now or datetime.now()).strftime("%a %d %b"))
    check_health(cfg)
    room = find_room(list_rooms(cfg), cfg.room)
    if dry_run:
        return f"[dry run] would post to {room.get('name')} ({room.get('room_id')}): {text}"
    reply = _request(
        cfg,
        "POST",
        f"/agents/{cfg.agent_id}/message",
        {"room_id": room["room_id"], "content": text},
    )
    event = reply.get("event_id") if isinstance(reply, dict) else None
    return f"posted to {room.get('name')}: {text} (event {event})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wake the Radar with its morning ping.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="KEY=VALUE config file")
    parser.add_argument("--base-url", help="Switch API URL (SWITCH_URL)")
    parser.add_argument("--agent-id", help="the bell agent's id (BELL_AGENT_ID)")
    parser.add_argument("--room", help="room name or id (BELL_ROOM)")
    parser.add_argument("--text", help="message to post; {date} is filled in (BELL_TEXT)")
    parser.add_argument("--dry-run", action="store_true", help="check everything, post nothing")
    args = parser.parse_args(argv)

    try:
        cfg = resolve_config(args)
        print(ring(cfg, dry_run=args.dry_run))
        return 0
    except BellError as err:
        print(f"bell: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
