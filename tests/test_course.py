"""The sample course folder hangs together: pages, topics, quiz, demo script."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COURSE = ROOT / "course"
sys.path.insert(0, str(ROOT / "tools"))
import seed_class  # noqa: E402


def note_pages() -> set[int]:
    pages: list[int] = []
    for f in (COURSE / "notes").glob("*.md"):
        text = f.read_text(encoding="utf-8")
        pages += [int(p) for p in re.findall(r"^## \[p\.(\d+)\]", text, flags=re.M)]
    assert len(pages) == len(set(pages)), "a page marker appears twice"
    return set(pages)


def syllabus_topics() -> set[str]:
    text = (COURSE / "syllabus.md").read_text(encoding="utf-8")
    return {row.split("|")[2].strip() for row in text.splitlines() if row.startswith("| Unit")}


def test_notes_cover_pages_6_to_20():
    assert note_pages() == set(range(6, 21))


def test_syllabus_pages_exist_in_notes():
    text = (COURSE / "syllabus.md").read_text(encoding="utf-8")
    cited = {int(n) for n in re.findall(r"p\.(\d+)", text)}
    assert cited <= note_pages()


def test_quiz_matches_schema_and_cites_real_pages():
    schema = json.loads((COURSE / "radar-data" / "quiz.schema.json").read_text())
    quiz = json.loads((COURSE / "radar-data" / "quizzes" / "2026-11-05.json").read_text())
    try:
        import jsonschema  # optional
    except ImportError:
        jsonschema = None
    if jsonschema:
        jsonschema.validate(quiz, schema)
    assert set(quiz) == set(schema["required"])
    for i, q in enumerate(quiz["questions"], 1):
        assert q["n"] == i
        assert set(q["options"]) == {"A", "B", "C", "D"}
        assert q["answer"] in q["options"]
        assert q["topic"] in syllabus_topics()
        pages = {int(p) for p in re.findall(r"p\.(\d+)", q["explain"])}
        assert pages and pages <= note_pages(), q["explain"]


def test_teacher_answers_use_syllabus_topics():
    text = (COURSE / "teacher-answers.md").read_text(encoding="utf-8")
    headings = re.findall(r"^## (.+)$", text, flags=re.M)
    assert headings and set(headings) <= syllabus_topics() | {"Logistics"}


def test_demo_script_shape():
    s = seed_class.summary()
    assert s["messages"] == 60
    assert s["students"] == 18
    assert s["logistics"] == 17
    topics = list(s["topics"].items())
    # The card the demo shows: base case far ahead, then return values, then order of work.
    assert topics[0] == ("Base case", 12)
    assert topics[1] == ("Return values in recursion", 5)
    assert set(s["topics"]) <= syllabus_topics()
    users = {line.user for line in seed_class.SCRIPT}
    assert users == {st.username for st in seed_class.STUDENTS}
    assert all("@" not in line.text for line in seed_class.SCRIPT), "seeded text must not address agents"


def test_quiz_option_b_trace_is_true():
    # Q2's claim: total([2, 3]) raises a TypeError because the recursive case doesn't return.
    def total(nums):
        if nums == []:
            return 0
        nums[0] + total(nums[1:])  # noqa: B018 (the bug is the point)

    try:
        total([2, 3])
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError")
