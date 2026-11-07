# Build plan: until Nov 7, 11:59 pm IST

Aim to submit by **8 pm on Nov 7**. Everything after that is buffer.

## Nov 4 (today): get it running

- [ ] Install Docker Desktop and Switch Console, start a local server (bundled Mattermost).
- [ ] Claude Code installed and signed in on the same machine.
- [ ] Unzip the repo into your home folder and run `bash setup.sh`.
- [ ] Import `template/zero-period.template.yaml` and create it with the Course folder `setup.sh` printed.
- [ ] `!assign-agent @ta` in the class channel.
- [ ] `python3 tools/smoke_test.py`, then fix what's red (see TESTING.md).
- [ ] **Check first:** the TA can read the notes under `dontAsk`. If it says it can't read
      files, set its Permission mode to *Default* in Console (agent → Advanced) and keep
      its tools at Read, Grep, Glob.
- [ ] Tell me what broke. Paste the agent's reply or the error, and we fix it.

## Nov 5: the full loop

- [ ] Escalation round trip: card → thread reply → delivered → `teacher-answers.md` grows.
- [ ] `@radar morning` on seeded data (`tools/seed_class.py`), then tune `agents/radar.md`
      until the card fits a phone screen.
- [ ] Warm-up: `send` → quiz in class → TA grades.
- [ ] Register the bell agent and run `tools/bell.py`.

## Nov 6: Discord and polish

- [ ] Connect Discord. Run the template again with Discord as the messaging app.
- [ ] Get one real teacher or senior and 3–5 students to use it for 30–60 minutes.
      Note one quote and one number (e.g. "12 doubts handled, 2 reached the teacher").
- [ ] README: add screenshots, the video link, and the real-user quote.

## Nov 7: ship

- [ ] Record the video (`docs/demo-script.md`). Keep it under 3 minutes.
- [ ] Push the repo publicly. Check that `pytest` passes on a clean clone.
- [ ] Side tracks: Wispr Flow Insights screenshot, blog post ("Building a classroom on
      Switch"), and #HowISwitch posts.
- [ ] Submit by 8 pm IST.
