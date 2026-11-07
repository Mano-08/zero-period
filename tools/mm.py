"""A small Mattermost client, and how to find your local Switch server's Mattermost.

Shared by seed_class.py (student logins and demo data) and smoke_test.py (the
end-to-end test). Standard library only.

Where the login comes from, first match wins:
  1. command-line flags (--mm-url, --teacher-user, --teacher-password)
  2. environment variables MM_URL, MM_USER, MM_PASSWORD
  3. mattermost.env in the repo folder (setup.sh writes it; git-ignored)
  4. Switch Console's local server files (address always; passwords only on older,
     Docker-based servers)
  5. asking you, when you run it in a terminal

The login is the one under Switch Console → Home → Messaging apps → Mattermost →
Sign-in details. It's you, the teacher. Student accounts are created by signing
up, which the local Mattermost allows, so no admin password is needed.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MATTERMOST_ENV = ROOT / "mattermost.env"


def console_data_dirs() -> list[Path]:
    """Switch Console's data folder (`switchdash`) on each platform."""
    return [
        Path.home() / "Library/Application Support/switchdash",  # macOS
        Path.home() / ".config/switchdash",  # Linux
        Path(os.environ.get("APPDATA", "~")).expanduser() / "switchdash",  # Windows
    ]


class MMError(RuntimeError):
    """A failure with a message a person can act on."""


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip("'\"")
    return values


def read_console_env(explicit: str | None = None) -> tuple[Path | None, dict[str, str]]:
    """What Switch Console's local server files say, as one dict.

    Docker-based servers (older Consoles) keep `local-switch-server/.env` with the
    Mattermost passwords. Current Consoles run the server natively: the API port is
    in `native/run/switch-core.env`, and Mattermost's address is in
    `native/mattermost-compose.yml`. Their passwords stay in Console's encrypted store.
    """
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise MMError(f"no settings file at {explicit}")
        return path, read_env_file(path)
    for base in console_data_dirs():
        server = base / "local-switch-server"
        legacy = server / ".env"
        if legacy.is_file():
            return legacy, read_env_file(legacy)
        core_env = server / "native" / "run" / "switch-core.env"
        compose = server / "native" / "mattermost-compose.yml"
        if core_env.is_file() or compose.is_file():
            values: dict[str, str] = {"MATTERMOST_TEAM_NAME": "switch", "MATTERMOST_USER": "user"}
            if core_env.is_file():
                core = read_env_file(core_env)
                if core.get("SERVER_PORT"):
                    values["API_HOST_PORT"] = core["SERVER_PORT"]
            if compose.is_file():
                site = re.search(r"MM_SERVICESETTINGS_SITEURL:\s*\"?http://[^:\"]+:(\d+)", compose.read_text("utf-8"))
                if site:
                    values["MATTERMOST_HOST_PORT"] = site.group(1)
            return server, values
    return None, {}


@dataclass
class Login:
    url: str
    user: str
    password: str
    team: str | None
    admin_user: str | None = None
    admin_password: str | None = None


def resolve_login(
    *,
    mm_url: str | None,
    user: str | None,
    password: str | None,
    team: str | None,
    console_env: str | None = None,
    admin_user: str | None = None,
    admin_password: str | None = None,
    admin_token: str | None = None,
    teacher_optional: bool = False,
    interactive: bool | None = None,
) -> Login:
    """Work out the Mattermost address and the teacher's login (see the module docstring).

    `teacher_optional`: a script that can do everything as an admin (the seeder) doesn't
    need the teacher's password when admin credentials are there."""
    file_values = read_env_file(MATTERMOST_ENV) if MATTERMOST_ENV.is_file() else {}
    _, console = read_console_env(console_env)

    def first(*candidates: str | None) -> str | None:
        return next((c for c in candidates if c), None)

    url = first(
        mm_url,
        os.environ.get("MM_URL"),
        file_values.get("MM_URL"),
        f"http://localhost:{console['MATTERMOST_HOST_PORT']}" if console.get("MATTERMOST_HOST_PORT") else None,
    )
    user = first(user, os.environ.get("MM_USER"), file_values.get("MM_USER"), console.get("MATTERMOST_USER"))
    password = first(
        password, os.environ.get("MM_PASSWORD"), file_values.get("MM_PASSWORD"), console.get("MATTERMOST_USER_PASSWORD")
    )
    team = first(team, os.environ.get("MM_TEAM"), file_values.get("MM_TEAM"), console.get("MATTERMOST_TEAM_NAME"))
    admin_user = first(admin_user, console.get("MATTERMOST_ADMIN_USER") if console.get("MATTERMOST_ADMIN_PASSWORD") else None)
    admin_password = first(admin_password, console.get("MATTERMOST_ADMIN_PASSWORD"))

    has_admin = bool(admin_token or (admin_user and admin_password))
    if teacher_optional and has_admin and url:
        return Login(url=url.rstrip("/"), user=user or "", password=password or "", team=team,
                     admin_user=admin_user, admin_password=admin_password)
    if interactive is None:
        interactive = sys.stdin.isatty()
    if interactive and not (url and user and password):
        print("Paste your Mattermost Sign-in details (Switch Console → Home → Messaging apps → Sign-in details…)")
        url = url or input("  Server [http://localhost:8065]: ").strip() or "http://localhost:8065"
        user = user or input("  Username [user]: ").strip() or "user"
        password = password or getpass.getpass("  Password (hidden): ").strip()
        if password and input("  Save these to mattermost.env for next time? [y/N] ").strip().lower() == "y":
            save_login(url, user, password, team)
    if not (url and user and password):
        raise MMError(
            "no Mattermost login. Put your Sign-in details (Switch Console → Home → Messaging apps → "
            "Sign-in details…) in mattermost.env (see mattermost.env.example), or pass --mm-url, "
            "--teacher-user and --teacher-password."
        )
    return Login(url=url.rstrip("/"), user=user, password=password, team=team,
                 admin_user=admin_user, admin_password=admin_password)


def save_login(url: str, user: str, password: str, team: str | None) -> None:
    lines = ["# Your Mattermost Sign-in details from Switch Console. Git-ignored; keep it private.",
             f"MM_URL={url}", f"MM_USER={user}", f"MM_PASSWORD={password}"]
    if team:
        lines.append(f"MM_TEAM={team}")
    MATTERMOST_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        MATTERMOST_ENV.chmod(0o600)
    except OSError:
        pass
    print(f"  saved to {MATTERMOST_ENV.name}")


class Mattermost:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base = base_url.rstrip("/") + "/api/v4"
        self.token = token

    def call(
        self,
        method: str,
        path: str,
        body: Any = None,
        *,
        token: str | None = None,
        anonymous: bool = False,
    ) -> tuple[Any, dict[str, str]]:
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        auth = None if anonymous else (token or self.token)
        if auth:
            headers["Authorization"] = f"Bearer {auth}"
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
                return (json.loads(raw) if raw else None), dict(resp.headers)
        except urllib.error.HTTPError as err:
            detail = err.read().decode(errors="replace")[:300]
            raise MMError(f"{method} {path} → {err.code}: {detail}") from err
        except urllib.error.URLError as err:
            raise MMError(
                f"can't reach Mattermost at {self.base[:-7]} ({err.reason}). Is Mattermost running "
                "(Switch Console → your server → Mattermost switch on, Docker Desktop running)?"
            ) from err

    def login(self, login_id: str, password: str) -> tuple[str, dict[str, Any]]:
        try:
            user, headers = self.call(
                "POST", "/users/login", {"login_id": login_id, "password": password}, anonymous=True
            )
        except MMError as err:
            if "→ 401" in str(err):
                raise MMError(f"Mattermost refused the login for {login_id}: wrong username or password") from err
            raise
        token = headers.get("Token") or headers.get("token")
        if not token:
            raise MMError(f"login for {login_id} returned no token")
        return token, user

    def user_by_username(self, username: str) -> dict[str, Any] | None:
        try:
            user, _ = self.call("GET", f"/users/username/{username}")
            return user
        except MMError as err:
            if "→ 404" in str(err):
                return None
            raise

    def team(self, name: str | None) -> dict[str, Any]:
        """The named team, or the signed-in user's only (or 'switch') team."""
        if name:
            team, _ = self.call("GET", f"/teams/name/{name}")
            return team
        teams, _ = self.call("GET", "/users/me/teams")
        teams = teams or []
        if len(teams) == 1:
            return teams[0]
        named = [t for t in teams if t.get("name") == "switch"]
        if named:
            return named[0]
        raise MMError(
            "can't tell which Mattermost team to use: pass --team with one of "
            + ", ".join(sorted(t.get("name", "?") for t in teams))
        )

    def ensure_student(
        self,
        username: str,
        password: str,
        first: str,
        last: str,
        team_id: str,
        channel_ids: list[str],
        *,
        as_admin: bool = False,
    ) -> tuple[dict[str, Any], str]:
        """Make sure a student account exists and is in the team and channels.

        With an admin token the admin creates it. Otherwise the student signs up,
        which the local Mattermost allows, and joins the open team and public
        channels itself. Returns (user, the student's own token)."""
        user = self.user_by_username(username)
        if user is None:
            body = {
                "username": username,
                "email": f"{username}@students.example.com",
                "password": password,
                "first_name": first,
                "last_name": last,
            }
            try:
                user, _ = self.call("POST", "/users", body, anonymous=not as_admin)
            except MMError as err:
                if "→ 403" in str(err) or "→ 501" in str(err):
                    raise MMError(
                        "this Mattermost doesn't allow sign-ups, so student accounts need an admin: "
                        "pass --admin-user and --admin-password"
                    ) from err
                raise
        token, _ = self.login(username, password)
        joiner = None if as_admin else token
        self.call("POST", f"/teams/{team_id}/members", {"team_id": team_id, "user_id": user["id"]}, token=joiner)
        for channel_id in channel_ids:
            self.call("POST", f"/channels/{channel_id}/members", {"user_id": user["id"]}, token=joiner)
        return user, token

    def find_channel(self, team_id: str, wanted: str) -> dict[str, Any]:
        """By URL name, then by name or display name among public and private channels."""
        try:
            channel, _ = self.call("GET", f"/teams/{team_id}/channels/name/{wanted}")
            return channel
        except MMError:
            pass
        pools: list[dict[str, Any]] = []
        for path in (
            "/users/me/teams/" + team_id + "/channels",
            f"/teams/{team_id}/channels?per_page=200",
            f"/teams/{team_id}/channels/private?per_page=200",
        ):
            try:
                found, _ = self.call("GET", path)
                pools += found or []
            except MMError:
                continue
        folded = wanted.lower()
        for ch in pools:
            if folded in (str(ch.get("name")).lower(), str(ch.get("display_name")).lower()):
                return ch
        for ch in pools:
            if folded in str(ch.get("name")).lower() or folded in str(ch.get("display_name")).lower():
                return ch
        raise MMError(
            f"no channel {wanted!r} that this account can see. Did the template run with this Class id, "
            "and is this the account you created it with?"
        )

    def post(self, token: str, channel_id: str, message: str, root_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"channel_id": channel_id, "message": message}
        if root_id:
            body["root_id"] = root_id
        created, _ = self.call("POST", "/posts", body, token=token)
        return created

    def posts_since(self, channel_id: str, since_ms: int) -> list[dict[str, Any]]:
        """Posts created after `since_ms`, oldest first."""
        reply, _ = self.call("GET", f"/channels/{channel_id}/posts?since={since_ms}")
        posts = list(((reply or {}).get("posts") or {}).values())
        posts = [p for p in posts if int(p.get("create_at", 0)) > since_ms and not p.get("delete_at")]
        return sorted(posts, key=lambda p: int(p.get("create_at", 0)))

    def channel_members(self, channel_id: str) -> list[dict[str, Any]]:
        members, _ = self.call("GET", f"/channels/{channel_id}/members?per_page=200")
        ids = [m["user_id"] for m in members or []]
        if not ids:
            return []
        users, _ = self.call("POST", "/users/ids", ids)
        return users or []
