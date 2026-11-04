#!/usr/bin/env python3
"""seed_class: fill the class channel with a realistic day of student messages.

This is for the demo. It creates 18 student accounts on the Mattermost server that
Switch Console runs, adds them to the class channel, and posts about 60 messages as
those students: doubts, logistics questions, chatter, and one student who sounds
low. Then the Radar has a real day to read, and the 7 am card shows what it does.

The messages are fictional and written for this demo. No real students are involved.

Before seeding, type `!unassign-agent` in the class channel, or the TA will answer
all 60 messages. After seeding, type `!assign-agent @ta` again.

  python3 tools/seed_class.py --dry-run          # print the script and its counts
  python3 tools/seed_class.py                    # local server: settings found automatically
  python3 tools/seed_class.py --admin-user admin --admin-password '…' \\
      --team switch --channel cs12b-class        # or say it all yourself

On a server Switch Console runs on this computer, the Mattermost admin account,
team and port are in Console's server settings file. The script finds that file
in the usual places (or pass --console-env). Switch ignores posts from the admin
account, which is why the students get accounts of their own.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Where Switch Console keeps its local server's settings (`switchdash` is its data
# folder name).
CONSOLE_ENV_CANDIDATES = (
    Path.home() / "Library/Application Support/switchdash/local-switch-server/.env",  # macOS
    Path.home() / ".config/switchdash/local-switch-server/.env",  # Linux
    Path(os.environ.get("APPDATA", "~")).expanduser() / "switchdash/local-switch-server/.env",  # Windows
)

# --------------------------------------------------------------------------- data


@dataclass(frozen=True)
class Student:
    username: str
    first: str
    last: str


STUDENTS: tuple[Student, ...] = (
    Student("riya.k", "Riya", "Kapoor"),
    Student("arjun.m", "Arjun", "Mehta"),
    Student("kabir.s", "Kabir", "Singh"),
    Student("meera.p", "Meera", "Pillai"),
    Student("ishaan.r", "Ishaan", "Rao"),
    Student("ananya.g", "Ananya", "Gupta"),
    Student("dev.t", "Dev", "Thakur"),
    Student("sara.a", "Sara", "Ali"),
    Student("rohan.v", "Rohan", "Verma"),
    Student("zoya.h", "Zoya", "Hussain"),
    Student("aditya.n", "Aditya", "Nair"),
    Student("nisha.b", "Nisha", "Bose"),
    Student("tanvi.j", "Tanvi", "Joshi"),
    Student("vikram.c", "Vikram", "Chauhan"),
    Student("farhan.q", "Farhan", "Qureshi"),
    Student("pooja.l", "Pooja", "Lal"),
    Student("neel.d", "Neel", "Desai"),
    Student("kavya.y", "Kavya", "Yadav"),
)


@dataclass(frozen=True)
class Line:
    """One scripted message. `kind` and `topic` are for tests and the README;
    only `user` and `text` are posted."""

    user: str
    text: str
    kind: str  # logistics | concept | chatter | care | note
    topic: str = ""


BASE = "Base case"
RET = "Return values in recursion"
ORDER = "Order of work (before/after the call)"
LOOPS = "Recursion vs loops"
STACK = "The call stack and unwinding"

SCRIPT: tuple[Line, ...] = (
    Line("arjun.m", "is the unit test on friday or monday??", "logistics"),
    Line("kabir.s", "friday 13th lol. cursed", "chatter"),
    Line("meera.p", "wait does the test have file handling also", "logistics"),
    Line("kabir.s", "why does factorial(0) return 1?? 0 times anything is 0 na", "concept", BASE),
    Line("ishaan.r", "same doubt. if n is 0 shouldn't the answer be 0", "concept", BASE),
    Line("ananya.g", "how does the function even know when to stop calling itself", "concept", BASE),
    Line("dev.t", "i wrote if n == 1: return 1 and it works for 5 but factorial(0) gives some RecursionError", "concept", BASE),
    Line("sara.a", "^ me too. maximum recursion depth exceeded. what does that even mean", "concept", BASE),
    Line("rohan.v", "isn't the base case just the last number we multiply? like 1", "concept", BASE),
    Line("tanvi.j", "is hw3 due tuesday or wednesday", "logistics"),
    Line("pooja.l", "tuesday 11:59 i think", "chatter"),
    Line("aditya.n", "my sum_list prints the right total but when i store it in a variable it's None??", "concept", RET),
    Line("nisha.b", "same!! i get TypeError int + NoneType", "concept", RET),
    Line("vikram.c", "where does the value go after return? like who receives it", "concept", RET),
    Line("zoya.h", "for count_vowels what is the base case, empty string or one letter", "concept", BASE),
    Line("neel.d", "do we need to know memoization for the test? sir from the other section taught it", "logistics"),
    Line("farhan.q", "bro is tail recursion in syllabus", "logistics"),
    Line("meera.p", "my sum_even never stops running. i think i'm not making the list smaller?", "concept", BASE),
    Line("kavya.y", "why does countup print 1 2 3 when the print is literally after the call. shouldn't it print 3 first", "concept", ORDER),
    Line("sara.a", "and countdown prints 3 2 1. i don't get why moving one line flips it", "concept", ORDER),
    Line("dev.t", "the trace thing on p.14 makes sense but i can't do it for countup", "concept", ORDER),
    Line("arjun.m", "how many marks is the test", "logistics"),
    Line("ishaan.r", "40", "chatter"),
    Line("rohan.v", "honestly why would anyone use recursion if a loop works", "concept", LOOPS),
    Line("neel.d", "^^ fr. loops are so much easier", "concept", LOOPS),
    Line("ishaan.r", "is recursion faster than loops?", "concept", LOOPS),
    Line("pooja.l", "in sum_list, after sum_list([]) returns 0 where does the 0 go? does it go to the first call directly?", "concept", RET),
    Line("farhan.q", "my power function returns None for power(2,3) but i'm doing b * power(b, e-1)", "concept", RET),
    Line("ananya.g", "is the test open book", "logistics"),
    Line("tanvi.j", "lol no", "chatter"),
    Line("kabir.s", "when are office hours", "logistics"),
    Line("zoya.h", "can we use loops inside the recursive function in hw3", "logistics"),
    Line("arjun.m", "if n == 0 return 1 is the base case. but WHY 1. i just don't get the 1", "concept", BASE),
    Line("tanvi.j", "for power(7, 0) is the answer 0 or 1", "concept", BASE),
    Line("vikram.c", "late submission is how much minus", "logistics"),
    Line("nisha.b", "does the practical file count for this term", "logistics"),
    Line("meera.p", "this is so confusing yaar", "chatter"),
    Line("dev.t", "😭😭", "chatter"),
    Line("aditya.n", "is the unit test in period 3 or 4", "logistics"),
    Line("rohan.v", "will they ask trace the output for recursion?", "logistics"),
    Line("kavya.y", "is there class on saturday", "logistics"),
    Line("sara.a", "no it's the school event", "chatter"),
    Line("neel.d", "my reverse string works but i don't understand WHY it works. it feels like magic", "concept", BASE),
    Line("ishaan.r", "anyone done hw3 q4 the triangle one", "chatter"),
    Line("pooja.l", "can we discuss hw answers with friends or is that cheating", "logistics"),
    Line("farhan.q", "radar if ur reading this tell ma'am the whole class wants the test postponed 🙏", "note"),
    Line("kabir.s", "LOL", "chatter"),
    Line("vikram.c", "what's the difference between the call stack and like a normal stack", "concept", STACK),
    Line("zoya.h", "do we get the formula for factorial in the test or we have to remember", "logistics"),
    Line("arjun.m", "ok i'll just memorize it", "chatter"),
    Line("riya.k", "base case for factorial is 1 right? since it stops at 1", "concept", BASE),
    Line("riya.k", "wait no then fact(0) breaks. i'm confused", "concept", BASE),
    Line("riya.k", "honestly been staring at this since 11 and i still don't get why fact(0) is 1. i'm just dumb at coding", "care", BASE),
    Line("meera.p", "riya you're not dumb it's confusing for everyone", "chatter"),
    Line("tanvi.j", "what time does homework close exactly", "logistics"),
    Line("nisha.b", "thank god someone else is lost", "chatter"),
    Line("aditya.n", "so return hands the value back and print just shows it? then why does my code print the right answer", "concept", RET),
    Line("dev.t", "ok gn guys", "chatter"),
    Line("kavya.y", "gn", "chatter"),
    Line("riya.k", "gn", "chatter"),
)


# --------------------------------------------------------------------- mattermost


class SeedError(RuntimeError):
    pass


class Mattermost:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base = base_url.rstrip("/") + "/api/v4"
        self.token = token

    def call(
        self, method: str, path: str, body: Any = None, *, token: str | None = None
    ) -> tuple[Any, dict[str, str]]:
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        auth = token or self.token
        if auth:
            headers["Authorization"] = f"Bearer {auth}"
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
                return (json.loads(raw) if raw else None), dict(resp.headers)
        except urllib.error.HTTPError as err:
            detail = err.read().decode(errors="replace")[:300]
            raise SeedError(f"{method} {path} → {err.code}: {detail}") from err
        except urllib.error.URLError as err:
            raise SeedError(f"can't reach Mattermost at {self.base} ({err.reason})") from err

    def login(self, login_id: str, password: str) -> str:
        _, headers = self.call("POST", "/users/login", {"login_id": login_id, "password": password})
        token = headers.get("Token") or headers.get("token")
        if not token:
            raise SeedError(f"login for {login_id} returned no token")
        return token

    def user_by_username(self, username: str) -> dict[str, Any] | None:
        try:
            user, _ = self.call("GET", f"/users/username/{username}")
            return user
        except SeedError as err:
            if "→ 404" in str(err):
                return None
            raise


def find_channel(mm: Mattermost, team_id: str, wanted: str) -> dict[str, Any]:
    try:
        channel, _ = mm.call("GET", f"/teams/{team_id}/channels/name/{wanted}")
        return channel
    except SeedError:
        pass
    channels, _ = mm.call("GET", f"/teams/{team_id}/channels?per_page=200")
    for ch in channels or []:
        if wanted.lower() in (str(ch.get("name")).lower(), str(ch.get("display_name")).lower()):
            return ch
    raise SeedError(
        f"no channel {wanted!r} in that team. Use the channel's URL name (the last part "
        "of its link in Mattermost)."
    )


def seed(args: argparse.Namespace) -> None:
    mm = Mattermost(args.mm_url, args.admin_token)
    if not args.admin_token:
        mm.token = mm.login(args.admin_user, args.admin_password)

    team, _ = mm.call("GET", f"/teams/name/{args.team}")
    channel = find_channel(mm, team["id"], args.channel)
    print(f"seeding #{channel['name']} in team {team['name']}")

    tokens: dict[str, str] = {}
    for s in STUDENTS:
        user = mm.user_by_username(s.username)
        if user is None:
            user, _ = mm.call(
                "POST",
                "/users",
                {
                    "username": s.username,
                    "email": f"{s.username}@students.example.com",
                    "password": args.student_password,
                    "first_name": s.first,
                    "last_name": s.last,
                },
            )
            print(f"  created {s.username}")
        mm.call("POST", f"/teams/{team['id']}/members", {"team_id": team["id"], "user_id": user["id"]})
        mm.call("POST", f"/channels/{channel['id']}/members", {"user_id": user["id"]})
        tokens[s.username] = mm.login(s.username, args.student_password)

    for i, line in enumerate(SCRIPT, 1):
        mm.call(
            "POST",
            "/posts",
            {"channel_id": channel["id"], "message": line.text},
            token=tokens[line.user],
        )
        print(f"  [{i:02d}/{len(SCRIPT)}] {line.user}: {line.text[:70]}")
        time.sleep(args.delay)
    print("done. Now type `!assign-agent @ta` in the class channel, and `@radar morning` on the desk.")


def read_console_env(explicit: str | None) -> tuple[Path | None, dict[str, str]]:
    """The local server's settings, or ({}, None) when there's no such file."""
    paths = [Path(explicit).expanduser()] if explicit else list(CONSOLE_ENV_CANDIDATES)
    for path in paths:
        if path.is_file():
            values: dict[str, str] = {}
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    values[key.strip()] = value.strip().strip("'\"")
            return path, values
    if explicit:
        raise SeedError(f"no settings file at {explicit}")
    return None, {}


def fill_from_console(args: argparse.Namespace) -> None:
    """Fill whatever the user didn't pass from Switch Console's local server settings."""
    path, env = read_console_env(args.console_env)
    if not env:
        return
    print(f"using local server settings from {path}")
    if not args.admin_token and not args.admin_password:
        args.admin_user = args.admin_user or env.get("MATTERMOST_ADMIN_USER")
        args.admin_password = env.get("MATTERMOST_ADMIN_PASSWORD")
    args.team = args.team or env.get("MATTERMOST_TEAM_NAME")
    if args.mm_url is None and env.get("MATTERMOST_HOST_PORT"):
        args.mm_url = f"http://127.0.0.1:{env['MATTERMOST_HOST_PORT']}"


def summary() -> dict[str, Any]:
    """Counts the README and the tests rely on."""
    by_topic: dict[str, set[str]] = {}
    for line in SCRIPT:
        if line.topic and line.kind in ("concept", "care"):
            by_topic.setdefault(line.topic, set()).add(line.user)
    return {
        "messages": len(SCRIPT),
        "students": len({line.user for line in SCRIPT}),
        "logistics": sum(1 for line in SCRIPT if line.kind == "logistics"),
        "topics": {topic: len(users) for topic, users in sorted(by_topic.items(), key=lambda kv: -len(kv[1]))},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the class channel with a demo day.")
    parser.add_argument("--console-env", help="Switch Console's local server .env (found automatically)")
    parser.add_argument("--mm-url", default=None, help="Mattermost URL (default http://127.0.0.1:8065)")
    parser.add_argument("--admin-user", help="Mattermost admin username or email")
    parser.add_argument("--admin-password", help="Mattermost admin password")
    parser.add_argument("--admin-token", help="or a Mattermost admin personal access token")
    parser.add_argument("--team", help="team URL name (slug)")
    parser.add_argument("--channel", default="cs12b-class", help="class channel URL name")
    parser.add_argument("--student-password", default="Radar-demo-2026!", help="password for demo students")
    parser.add_argument("--delay", type=float, default=0.6, help="seconds between posts")
    parser.add_argument("--dry-run", action="store_true", help="print the script and counts, post nothing")
    args = parser.parse_args(argv)

    if args.dry_run:
        for line in SCRIPT:
            print(f"{line.user:>10}: {line.text}")
        print(json.dumps(summary(), indent=2))
        return 0
    try:
        fill_from_console(args)
        args.mm_url = args.mm_url or "http://127.0.0.1:8065"
        if not args.team or not (args.admin_token or (args.admin_user and args.admin_password)):
            parser.error(
                "couldn't find the local server settings: pass --team and admin credentials "
                "(--admin-user/--admin-password or --admin-token), or --console-env"
            )
        seed(args)
        return 0
    except SeedError as err:
        print(f"seed: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
