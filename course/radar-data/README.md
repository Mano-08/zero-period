# radar-data/

The Radar's working files. Only the Radar writes here. The TA reads `quizzes/` to
grade warm-up answers. This folder is private teacher data. Don't share it, and keep
it out of public repositories once real students use the system (see the root
`.gitignore`).

| Path | Written when | Contents |
|---|---|---|
| `state.json` | after each morning radar | `{"last_radar": "<ISO-8601 time>"}`: where the next radar starts reading |
| `escalations.jsonl` | a 🆘/💛 card arrives; the teacher answers it | one JSON object per line (see below) |
| `radars/YYYY-MM-DD.md` | each morning radar | the card exactly as posted to the teacher |
| `quizzes/YYYY-MM-DD.json` | each morning radar | the warm-up quiz with its answer key; schema in `quiz.schema.json` |

`escalations.jsonl` line:

```json
{"id": "E-1105-0942-riya", "type": "stuck", "student": "riya", "topic": "Base case",
 "asked": "why does factorial(0) return 1?", "opened": "2026-11-05T09:42:00+05:30",
 "status": "answered", "answer": "Think of the stack of plates…",
 "answered_at": "2026-11-05T09:44:10+05:30"}
```

`type` is `stuck` (🆘) or `care` (💛). `status` is `open` or `answered`.
