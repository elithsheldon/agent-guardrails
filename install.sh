#!/usr/bin/env bash
# Install agent-guardrails into this machine.
#
# Never clobbers an existing ~/.claude/settings.json: hooks are appended only,
# and an already-registered hook is not added twice.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.claude"
PY="${PYTHON:-/usr/bin/python3}"

command -v "$PY" >/dev/null 2>&1 || { echo "FAIL: $PY not found"; exit 1; }

echo "1. Copying hooks and skill"
mkdir -p "$DEST/hooks" "$DEST/skills/daily-retro/references" "$DEST/skills/daily-retro/scripts"
cp "$HERE"/hooks/* "$DEST/hooks/"
cp "$HERE"/skills/daily-retro/SKILL.md "$DEST/skills/daily-retro/"
cp "$HERE"/skills/daily-retro/references/* "$DEST/skills/daily-retro/references/"
cp "$HERE"/skills/daily-retro/scripts/* "$DEST/skills/daily-retro/scripts/"
chmod +x "$DEST"/hooks/*.sh 2>/dev/null || true
echo "   -> $DEST/hooks, $DEST/skills/daily-retro"

echo "2. Registering hooks in settings.json (existing settings preserved)"
"$PY" - "$DEST" <<'PYEOF'
import json, pathlib, sys
dest = pathlib.Path(sys.argv[1])
sp = dest / "settings.json"
conf = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
hooks = conf.setdefault("hooks", {})
py = "/usr/bin/python3"
h = dest / "hooks"
wanted = [
    ("Stop",        "*",                    f"{py} {h}/reply_check.py"),
    ("PreToolUse",  "Bash",                 f"{py} {h}/outward_action_guard.py"),
    ("PreToolUse",  "Edit|Write|MultiEdit", f"{py} {h}/guard_the_guards.py"),
    ("PostToolUse", "Write|Edit",           f"sh {h}/daily-retro-reminder.sh"),
]
added = 0
for event, matcher, cmd in wanted:
    lst = hooks.setdefault(event, [])
    if any(cmd in json.dumps(e) for e in lst):
        continue
    lst.append({"matcher": matcher, "hooks": [{"type": "command", "command": cmd}]})
    added += 1
sp.write_text(json.dumps(conf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"   -> {added} added, existing entries untouched")
PYEOF

echo "3. Self-test"
if "$PY" "$DEST/skills/daily-retro/scripts/verify-gates.py" > /tmp/agr_verify.txt 2>&1; then
  tail -2 /tmp/agr_verify.txt | sed 's/^/   /'
else
  echo "   Some gates did not fire:"
  grep -E '\[FAIL\]|^failed:' /tmp/agr_verify.txt | sed 's/^/   /' || true
  echo "   Details: /tmp/agr_verify.txt"
fi

cat <<'NOTE'

One step left, by hand:
  Read CLAUDE.example.md, adapt it to your machine (memory path, daily-report
  location), then place it at ~/.claude/CLAUDE.md.
  Copying it unchanged leaves placeholders like <project-scope> in place.
NOTE
