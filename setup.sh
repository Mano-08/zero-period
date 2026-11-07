#!/usr/bin/env bash
# Zero Period: one-time setup on the Mac (or Linux box) where Switch Console runs.
#
#   bash setup.sh            # class id cs12b
#   bash setup.sh myclass    # if you'll use another Class id in the template form
#
# It checks the tools you need, makes sure the course folder is complete, finds your
# local Switch server and its Mattermost, saves your Mattermost login for the test
# scripts (if you paste it), prepares bell.env, and prints (and copies) the Course
# folder path to paste into the template form. Safe to run again.

set -u
CLASS_ID="${1:-cs12b}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
COURSE="$ROOT/course"
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; }

echo "Zero Period setup · class id: $CLASS_ID"
echo
echo "1. Tools"
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
  ok "python3 $(python3 -c 'import platform; print(platform.python_version())')"
else
  bad "python3 3.9+ not found. Install it from python.org, then run this again."
  exit 1
fi
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then ok "Docker is running (Mattermost runs in it)"; else warn "Docker is installed but not running. Open Docker Desktop: Mattermost needs it."; fi
else
  warn "Docker not found. Install Docker Desktop: Switch Console runs Mattermost in it."
fi
if command -v claude >/dev/null 2>&1; then
  ok "Claude Code CLI found ($(claude --version 2>/dev/null | head -n 1))"
else
  warn "Claude Code CLI not found. Install it, run 'claude' once and sign in. Both agents run on it."
fi

echo
echo "2. Course folder"
mkdir -p "$COURSE/notes" "$COURSE/homework" "$COURSE/radar-data/radars" "$COURSE/radar-data/quizzes"
[ -f "$COURSE/radar-data/state.json" ] || echo '{"last_radar": null}' > "$COURSE/radar-data/state.json"
[ -f "$COURSE/radar-data/escalations.jsonl" ] || : > "$COURSE/radar-data/escalations.jsonl"
[ -f "$COURSE/teacher-answers.md" ] || printf '# Teacher'"'"'s answers\n\n' > "$COURSE/teacher-answers.md"
missing=""
for f in class-info.md syllabus.md schedule.md notes/unit2-functions.md notes/unit3-recursion.md homework/hw3.md radar-data/quiz.schema.json; do
  [ -f "$COURSE/$f" ] || missing="$missing $f"
done
if [ -n "$missing" ]; then
  bad "missing from course/:$missing. Download the repo again."
else
  ok "notes, syllabus, schedule, homework, class info and radar-data are all there"
fi

echo
echo "3. Local Switch server and Mattermost"
# Python reads Switch Console's files (tools/mm.py knows both the current and the older layout).
eval "$(cd "$ROOT/tools" && python3 - <<'PY'
import mm, shlex
path, v = mm.read_console_env()
print(f"FOUND={shlex.quote(str(path or ''))}")
print(f"API_PORT={shlex.quote(v.get('API_HOST_PORT', ''))}")
print(f"MM_PORT={shlex.quote(v.get('MATTERMOST_HOST_PORT', ''))}")
PY
)"
API_URL="http://127.0.0.1:${API_PORT:-8000}"
MM_URL=""
[ -n "$MM_PORT" ] && MM_URL="http://localhost:$MM_PORT"
if [ -n "$FOUND" ]; then
  ok "found your local Switch server"
  echo "     Agent API:  $API_URL"
  if command -v curl >/dev/null 2>&1 && ! curl -fsS -m 5 "$API_URL/health" >/dev/null 2>&1; then
    warn "the server isn't answering. Start it in Switch Console."
  fi
  if [ -n "$MM_URL" ]; then
    echo "     Mattermost: $MM_URL   (open it in your browser)"
    if command -v curl >/dev/null 2>&1 && ! curl -fsS -m 5 "$MM_URL/api/v4/system/ping" >/dev/null 2>&1; then
      warn "Mattermost isn't answering. Is Docker Desktop running, and the Mattermost switch on?"
    fi
  else
    warn "no Mattermost yet: on your server's page in Switch Console, turn the Mattermost switch on (Docker Desktop must be running)"
  fi
else
  warn "no local server found yet. In Switch Console: Add a server → Run a server on this computer. Then run this again."
fi

echo
echo "4. Your Mattermost login (used by the test scripts, stays on this Mac)"
if [ -f "$ROOT/mattermost.env" ]; then
  ok "mattermost.env is there"
elif [ -t 0 ]; then
  echo "     Switch Console → Home → Messaging apps → Mattermost → Sign-in details…"
  echo "     Paste them here, or just press Enter to skip (the scripts will ask later)."
  read -r -p "     Server [${MM_URL:-http://localhost:8065}]: " in_url
  read -r -p "     Username [user]: " in_user
  read -r -s -p "     Password: " in_pw; echo
  if [ -n "$in_pw" ]; then
    ( umask 077
      printf '# Your Mattermost Sign-in details from Switch Console. Git-ignored; keep it private.\nMM_URL=%s\nMM_USER=%s\nMM_PASSWORD=%s\n' \
        "${in_url:-${MM_URL:-http://localhost:8065}}" "${in_user:-user}" "$in_pw" > "$ROOT/mattermost.env" )
    ok "saved to mattermost.env (git-ignored)"
  else
    warn "skipped. The test scripts will ask for it."
  fi
else
  warn "no mattermost.env. Copy mattermost.env.example to it, or let the scripts ask."
fi

echo
echo "5. Bell (optional 7 am ping)"
[ -f "$ROOT/bell.env" ] || cp "$ROOT/bell.env.example" "$ROOT/bell.env"
python3 - "$ROOT/bell.env" "$API_URL" "$CLASS_ID" <<'PY'
import sys, re
path, api, cls = sys.argv[1:4]
text = open(path, encoding="utf-8").read()
text = re.sub(r"(?m)^SWITCH_URL=.*$", f"SWITCH_URL={api}", text)
text = re.sub(r"(?m)^BELL_ROOM=.*$", f"BELL_ROOM={cls}-teacher-desk", text)
open(path, "w", encoding="utf-8").write(text)
PY
ok "bell.env ready (add BELL_AGENT_ID and BELL_API_KEY after registering the bell; see README)"

echo
echo "6. Paste this as the Course folder in the template form:"
echo
echo "     $COURSE"
echo
if command -v pbcopy >/dev/null 2>&1; then printf '%s' "$COURSE" | pbcopy && ok "copied to your clipboard"; fi

cat <<EOF

Next:
  a. Switch Console → Templates → Use "Zero period": Class id $CLASS_ID, Course folder (above), Mattermost → Create
  b. In the $CLASS_ID-class channel, type:  !assign-agent @ta
  c. Test it all:  python3 tools/smoke_test.py --class-id $CLASS_ID
     Or test by hand, step by step: see TESTING.md
EOF
