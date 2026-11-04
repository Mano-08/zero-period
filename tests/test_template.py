"""The Switch template: built from its sources, valid for Switch, and safe."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_template  # noqa: E402

TEMPLATE = ROOT / "template" / "confusion-radar.template.yaml"
BUILTINS = {"$creator", "$creator_email", "$date", "$timestamp", "$agents_dir"}


@pytest.fixture(scope="module")
def doc() -> dict:
    return yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))


def test_committed_template_matches_its_sources():
    assert TEMPLATE.read_text(encoding="utf-8") == build_template.render(), (
        "template is stale: run python3 tools/build_template.py"
    )


@pytest.mark.parametrize("rel", ["agents/ta.md", "agents/radar.md", "rooms/class.md", "rooms/teacher-desk.md"])
def test_no_live_mentions_in_briefs(rel):
    # Switch re-reads text an agent sees, and a literal at-sign before a name
    # addresses that agent for real. Briefs and room instructions must have none.
    assert "@" not in (ROOT / rel).read_text(encoding="utf-8")


def test_every_placeholder_is_declared(doc):
    declared = set(doc["params"]) | BUILTINS
    used = set(re.findall(r"\{(\$?[A-Za-z_][A-Za-z0-9_]*)\}", TEMPLATE.read_text(encoding="utf-8")))
    assert used - declared == set()
    assert set(doc["params"]) <= used, "a declared param is never used"


def test_ta_is_read_only_and_never_asks(doc):
    ta = next(a for a in doc["agents"] if a["name"].endswith("-ta"))
    assert ta["addressing"] == "anyone"
    assert ta["advanced_config"]["tools"] == ["Read", "Grep", "Glob"]
    assert ta["advanced_config"]["permissionMode"] == "dontAsk"
    banned = set(ta["advanced_config"]["disallowedTools"])
    for op in ("add_users_to_room", "archive_room", "create_room", "invite_agent_to_room",
               "update_room_document", "run_template", "update_agent_detail"):
        assert f"mcp__switch__{op}" in banned


def test_radar_is_owner_only(doc):
    radar = next(a for a in doc["agents"] if a["name"].endswith("-radar"))
    assert radar["addressing"] == "owner-agents"
    assert "Bash" not in radar["advanced_config"]["tools"]
    assert "mcp__switch__add_users_to_room" in radar["advanced_config"]["disallowedTools"]


def test_rooms_and_links(doc):
    rooms = {r["name"]: r for r in doc["rooms"]}
    assert rooms["{class_name}-class"]["channel_type"] == "channel_public"
    assert rooms["{class_name}-teacher-desk"]["channel_type"] == "channel_private"
    for room in rooms.values():
        assert room["aliases"] == {"{class_name}-ta": "ta", "{class_name}-radar": "radar"}
        assert room["kickoff"].startswith("@{class_name}-")
    assert {(l["from"], l["to"]) for l in doc["links"]} == {
        ("{class_name}-class", "{class_name}-teacher-desk"),
        ("{class_name}-teacher-desk", "{class_name}-class"),
    }


# ---- checks that use Switch's own code, when switch-core is installed ----------

switch_core = pytest.importorskip("switch_core", reason="switch-core not installed")


def test_switch_linter_is_clean():
    from switch_core.template_lint import lint_template

    result = lint_template(TEMPLATE.read_text(encoding="utf-8"))
    assert result.errors == [] and result.warnings == []


def test_advanced_config_is_valid_for_claude(doc):
    from switch_core.management.advanced_config import validate_advanced_config

    for agent in doc["agents"]:
        validate_advanced_config("claude", agent["advanced_config"])


def test_server_plans_the_run_and_parses_the_rooms():
    from switch_core.agent_templates import plan_template
    from switch_core.rooms_yaml import GroupSpec, RoomYamlService

    machines = [{"id": "m1", "name": "laptop", "state": "online",
                 "providers": [{"provider": "claude", "installed": True, "auth": "ok"}]}]
    inputs = {"class_name": "cs12b", "course_dir": "/Users/priya/confusion-radar/course", "bridge": "Discord"}
    plan = plan_template(TEMPLATE.read_text(encoding="utf-8"), {}, inputs,
                         builtins={"$creator": "priya"}, machines=machines)
    assert [a.name for a in plan.new_agents] == ["cs12b-ta", "cs12b-radar"]
    assert {a.directory for a in plan.new_agents} == {"/Users/priya/confusion-radar/course"}

    svc = RoomYamlService(room_service=None, resource_service=None, room_store=None, agent_store=None,
                          bridge_store=None, external_user_store=None, room_role_store=None,
                          session_factory=None, room_group_store=None)
    parsed = svc.parse_template(plan.document, inputs=plan.inputs, builtins={"$creator": "priya"})
    assert isinstance(parsed.spec, GroupSpec)
    names = [r.name for r in parsed.spec.rooms]
    assert names == ["cs12b-class", "cs12b-teacher-desk"]
    for room in parsed.spec.rooms:
        assert room.agents == ["cs12b-ta", "cs12b-radar"]
        assert room.users == ["priya"]
        assert room.bridge == "Discord"
        assert "{" not in (room.instructions or "")
        assert room.kickoff and "{" not in room.kickoff
    assert "Ma'am's notes" in parsed.spec.rooms[0].kickoff
    for agent in plan.new_agents:
        assert "{class_name}" not in agent.instructions and "{teacher_title}" not in agent.instructions
        assert "cs12b-class" in agent.instructions
