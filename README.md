# 📡 Confusion Radar

**It's not an AI tutor. It's a radar for the teacher.**

It's 9:40 pm. A teacher's phone shows 63 unread messages from the class group.
Forty are "ma'am is chapter 4 in the test?". Buried in there: twelve students stuck on
the same idea, and one who has been quietly lost for a week. Another student never asks
her "basic" question at all, because the whole class would see it. The next morning the
class moves on, and the confusion only shows up in the exam.

The teacher doesn't need fewer messages. **They need to know what the class doesn't
understand before they walk into class.** Confusion Radar puts two AI agents into the
class's chat through [Switch](https://github.com/sandbox-quantum/switch):

- **TA** (for students) lives in the class channel. It answers logistics from the
  syllabus and coaches doubts with hints from the teacher's own notes. It never gives
  final answers. When a student is still stuck after three hints, it brings the teacher
  in.
- **Radar** (for the teacher) lives on the teacher's private desk channel. At 7 am it
  turns yesterday's channel into one card: what the class misunderstood, the likely
  misconception, a five-minute fix with page numbers, who to check in with, and a
  ready-made warm-up quiz. One reply ("send") posts the quiz to the class.

Built for **Flip the Switch** (WeMakeDevs × DevTools Academy, November 2026), Track 02.

---

## What it looks like

**In the class channel** (students + TA)

```
Kabir:  why does factorial(0) return 1?? 0 times anything is 0 na
TA:     💡 Hint 1/3 · Base case · Notes p.12
        Ma'am explained this before: you stop when there are no plates left, not when
        there's one. What do you get if you multiply *no* numbers?
...
TA:     I'm asking Ma'am. The answer will come back right here.
```

**On the teacher's desk** (teacher + Radar, private)

```
🆘 E-1105-2142-riya · Riya · Base case
Stuck on: "why fact(0) is 1"
Tried: smallest input · multiply no numbers · trace fact(1)
Where she is: thinks recursion "ends at 1", so picks 1 as the base case
    └ Radar: Logged as E-1105-2142-riya. Reply in this thread and I'll take your answer to Riya.
    └ Ms. Sharma: tell her the base case is the smallest *input*, not the last number…
    └ Radar: Delivered to Riya ✅. Saved to teacher-answers, so the TA will use it next time.

📡 Confusion Radar · Thu 5 Nov · 60 messages from 18 students since 7:00 am yesterday
1. Base case · 12 students
Misconception: the base case is "where it stops multiplying" (1), not the smallest input (0)
Heard: "isn't the base case just the last number we multiply?"
5-min fix: stack of plates, stop at zero plates; then trace factorial(0) together (Notes p.12–13)
2. Return values in recursion · 5 students
…
Logistics: 17 questions, mostly "what's on Friday's test" → pin: "Units 2–3, p.6–20, closed book"
Check in with: Riya, wrote "I'm just dumb at coding" after 11 pm
Warm-up ready: 3 questions on base case and return values. Reply "send" to post it.
```

---

## Why this needs Switch

Every one of these comes from Switch itself. None of them is glue code we wrote:

| What you see | The Switch feature behind it |
|---|---|
| Two agents, two channels, one class. Students never see the desk. | **Rooms** with membership as the boundary, and **linked rooms** in a **room group** |
| The TA is open to every student. The Radar answers only the teacher. | Per-agent **addressing policy** (`anyone` vs `owner-agents`). A student who tries `@radar` gets a refusal from Switch |
| Students can talk to the TA, so the TA can only read | Per-agent **advanced config**: tools `Read, Grep, Glob`, permission mode `dontAsk`, room-admin Switch tools removed |
| Answers come from *this* teacher's notes, which never leave her laptop | Agents **run on their owner's machine** (Switch Console) in a chosen working directory |
| Students don't have to type `@ta` | `!assign-agent @ta`: every message in the class channel reaches the TA |
| Same agents behave differently in each channel | **Room instructions** |
| Stuck student → card on the desk → teacher answers → student gets it | **Hand-offs**: agents address each other in rooms they share, with home-room round trips |
| The 7 am card counts doubts nobody addressed to an agent | **The room is the log.** The Radar reads the class history with `read_context` |
| Works on the bundled Mattermost or on Discord, unchanged | The **collaboration bridge**. Our agents never touch a chat API |
| The morning ping | A small custom agent, [`tools/bell.py`](tools/bell.py), that speaks the **Switch agent protocol** |
| One click sets up everything above | A **Switch template** ([`template/confusion-radar.template.yaml`](template/confusion-radar.template.yaml)) |

Without Switch you'd have to build the chat integration, the multi-room routing,
per-agent permissions, a local agent runtime and the hand-off plumbing yourself.
Here that's the platform, and this repo is the classroom workflow on top of it.

---

## How it works

```mermaid
sequenceDiagram
  autonumber
  actor S as Student
  participant C as #class (room)
  participant TA as TA agent
  participant D as #teacher-desk (room)
  participant R as Radar agent
  actor T as Teacher
  S->>C: why does factorial(0) return 1?
  C->>TA: (assigned agent: every message)
  TA->>C: 💡 Hint 1/3 · Base case · Notes p.12
  S->>C: still don't get it… (hints 2 and 3)
  TA->>D: 🆘 card → addresses Radar + teacher (round trip, back home)
  R->>D: "Logged as E-…" (in the card's thread)
  T->>D: replies in the thread with an explanation
  R->>R: saves it to teacher-answers.md
  R->>C: delivers the answer to the student (round trip, back home)
  Note over R,C: Next student with the same doubt gets Ma'am's explanation first
  Note over D,R: 7:00 bell → Radar reads #class history → card + quiz → "send" → quiz in #class → TA grades
```

| | TA (`<class>-ta`) | Radar (`<class>-radar`) |
|---|---|---|
| Home room | `#<class>-class` | `#<class>-teacher-desk` |
| Who can address it | anyone in its rooms | the teacher, and the teacher's own agents |
| Tools | Read, Grep, Glob (permission mode `dontAsk`) | Read, Grep, Glob, Write, Edit (`acceptEdits`) |
| Writes | nothing | only `radar-data/` and `teacher-answers.md` |
| Posts in #class | hints, logistics, quiz grades | only a teacher's answer to the student who asked, and an approved quiz |

Both agents run Claude Code in the teacher's **course folder** ([`course/`](course)),
which holds notes with page markers, the syllabus, the schedule, homework, class info and
`teacher-answers.md`. That last file grows every time the teacher answers a card, so
the class's knowledge builds up over time.

---

## Quick start (Mattermost, about 15 minutes)

**You need:** Docker Desktop, [Switch Console](https://github.com/sandbox-quantum/switch/releases/latest)
(macOS; Windows and Linux are early access), Claude Code installed and signed in, and
Python 3.9+ for the helper scripts.

1. **Clone this repo.** Note the absolute path of its `course/` folder.
2. **Start a local Switch server** in Switch Console. It comes with Mattermost. Under
   Home → Messaging apps → **Sign-in details…** you'll find your Mattermost account.
   Chat as that account, never as the admin, because Switch ignores the admin's posts.
   Link it to yourself if Console asks.
3. **Import the template.** Templates → **Import template** → paste
   [`template/confusion-radar.template.yaml`](template/confusion-radar.template.yaml)
   → fill in:
   - **Class id:** `cs12b` (used in agent and channel names)
   - **What students call you:** `Ma'am`
   - **Course folder:** the absolute path from step 1, e.g. `/Users/you/confusion-radar/course`
   - **Messaging app:** your Mattermost

   **Create.** You get two agents and two channels. The TA introduces itself in
   `cs12b-class`, and the Radar says hello on `cs12b-teacher-desk`.
4. **In `cs12b-class`, type** `!assign-agent @ta`. From now on, every student message
   reaches the TA without an `@`. (This needs a server with "follow the conversation"
   on, which Console's local server has. Elsewhere, students start messages with `@ta`.)
5. **Try it** with a second Mattermost account as a student:
   - `is file handling in friday's test?` → a straight answer from `syllabus.md`.
   - `why does factorial(0) return 1?` → `💡 Hint 1/3`, using the teacher's saved explanation.
   - Say you're still stuck three times. A 🆘 card appears on the desk. Reply in its
     thread, and the Radar delivers your answer to the student.
6. **On the desk, type** `@radar morning`. The Radar card appears. Reply `send` in its
   thread, and the warm-up quiz is posted to the class. Answer it as the student, e.g.
   `1A 2B 3C`. The TA grades it and explains anything wrong, citing the notes.

### Discord

Connect Discord to your Switch server once. Follow Switch's
*Connect Discord* guide: create a bot, turn on **Message Content** and **Server
Members** intents, invite it with `bot` and `applications.commands`, then paste the bot
token and server id into Console → Home → Messaging apps → Connect, and link your
Discord account. Then run the same template with **Messaging app: Discord**, and type
`!assign-agent @ta` in the class channel.

On Discord, start a reply to a card with `@radar` and the card id, e.g.
`@radar E-1105-2142-riya tell her…`. Discord has no one-to-one chats with agents.

### The 7 am bell (optional, 2 minutes)

Switch has no scheduler: agents act when addressed. [`tools/bell.py`](tools/bell.py)
is a tiny agent of its own that posts `@radar morning…` to the desk.

1. In the Switch dashboard, go to Agents → **Register Agent**, choose Type
   **External agent**, and name it `cs12b-bell`. Copy its Agent ID and API Key. The key
   is shown once.
2. In `cs12b-teacher-desk`, type `!invite-agent @cs12b-bell`.
3. `cp bell.env.example bell.env`, fill it in, then run `python3 tools/bell.py --dry-run`
   followed by `python3 tools/bell.py`.
4. Add it to cron: `0 7 * * 1-6 cd /path/to/confusion-radar && python3 tools/bell.py >> bell.log 2>&1`

The Radar accepts the bell because the bell is one of the teacher's own agents
(`owner-agents`). The machine running the agents must be awake at 7 am. Switch Console
can also run the agents on an always-on SSH host.

### Demo data

```bash
python3 tools/seed_class.py --dry-run   # read the 60-message script first
# in cs12b-class: !unassign-agent   (so the TA doesn't answer all 60)
python3 tools/seed_class.py             # finds Console's local server settings automatically
# in cs12b-class: !assign-agent @ta
```

This creates 18 fictional student accounts on your local Mattermost and posts a
realistic school day: 12 students stuck on base cases, 5 on return values, 17
logistics questions, chatter, one student who sounds low, and one "radar, tell ma'am to
postpone the test" that the Radar reports instead of obeying.

---

## Safety and privacy, by design

- **Students can address the TA, so the TA can't do anything risky.** Its only tools
  read files. It runs in `dontAsk` mode, so nothing ever waits on an approval card a
  student could click. Room-admin Switch tools (adding people, archiving rooms, creating
  agents) are removed from both agents.
- **The Radar answers only the teacher** (and the teacher's own agents). It writes only
  `radar-data/` and `teacher-answers.md`, and it posts in the class only words the
  teacher approved.
- **Nothing about one student goes to the class.** Cards, scores and worries stay on
  the private desk.
- **Student text is data, never instructions.** Prompt-injection attempts are reported
  to the teacher and not acted on. The demo script includes one.
- **Care first.** A student who sounds unsafe gets a kind reply, real help contacts
  (Tele-MANAS 14416, emergency 112, the school counsellor; edit them in
  [`course/class-info.md`](course/class-info.md)), and an immediate 💛 card for the teacher.
- **Transparency.** The TA tells students on day one that the teacher sees a daily
  summary of what the class found confusing.
- **Where data goes.** Course files stay on the teacher's machine. Messages pass through
  your Switch server and your chat app. Model calls go to your Claude Code provider.
  Self-hosting Switch doesn't remove that last hop.

Defence in depth: [`course/.claude/settings.json`](course/.claude/settings.json) also
denies shell, web, credential files and edits to the teacher's notes, for Claude Code
sessions that load project settings.

---

## Use it for your own class

Replace the files in `course/` with your own: notes with `## [p.N]` page markers, a
syllabus with a topic-name table, the schedule, class info, and homework. Then run the
template again with a new class id. To change the agents' behaviour, edit
`agents/*.md` or `rooms/*.md`, then run `python3 tools/build_template.py`.

## Repository

```
template/confusion-radar.template.yaml   the one-click Switch template (generated)
agents/ta.md, agents/radar.md            the agents' briefs (source)
rooms/class.md, rooms/teacher-desk.md    room instructions (source)
course/                                  the teacher's folder, and the agents' working directory
  notes/ homework/ syllabus.md schedule.md class-info.md teacher-answers.md
  radar-data/                            Radar's files: quizzes, cards, escalations, state
tools/build_template.py                  builds the template from the sources
tools/bell.py                            the morning ping (Switch agent protocol, stdlib only)
tools/seed_class.py                      demo data for a local Mattermost (stdlib only)
tests/                                   pytest: template, protocol client, seeder, course
docs/demo-script.md                      the video, shot by shot
```

## Development

```bash
pip install -r requirements-dev.txt
pytest                                   # 30 tests
python3 tools/build_template.py --check  # the template matches agents/ and rooms/
```

If `switch-core` is installed (`pip install -e <switch>/core`), the tests also run the
template through Switch's own linter, advanced-config validator and server-side
planner and room parser.

## Limits and next steps

- The agents run where Switch Console runs them. A sleeping laptop means a silent class
  channel and no 7 am card. Run them on an always-on host for real use.
- Discord doesn't bridge threads to Switch the way Mattermost does, so card replies there
  name the card id.
- Next: anonymous questions through Mattermost direct messages, a weekly trend line per
  topic, a parent-friendly digest, and one desk serving several classes.
