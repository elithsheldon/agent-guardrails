#!/usr/bin/env bash
# agent-guardrails をこの環境へ入れる。
#
# 既存の ~/.claude/settings.json は壊さない（hooks 配列に追記するだけ）。
# 同じフックが既に登録されていれば重複追加しない。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.claude"
PY="${PYTHON:-/usr/bin/python3}"

command -v "$PY" >/dev/null 2>&1 || { echo "NG: $PY が見つかりません"; exit 1; }

echo "1. フックとスキルをコピー"
mkdir -p "$DEST/hooks" "$DEST/skills/daily-retro/references" "$DEST/skills/daily-retro/scripts"
cp "$HERE"/hooks/* "$DEST/hooks/"
cp "$HERE"/skills/daily-retro/SKILL.md "$DEST/skills/daily-retro/"
cp "$HERE"/skills/daily-retro/references/* "$DEST/skills/daily-retro/references/"
cp "$HERE"/skills/daily-retro/scripts/* "$DEST/skills/daily-retro/scripts/"
chmod +x "$DEST"/hooks/*.sh 2>/dev/null || true
echo "   -> $DEST/hooks, $DEST/skills/daily-retro"

echo "2. settings.json にフックを登録（既存設定は保持）"
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
print(f"   -> {added} 件追加（既存はそのまま）")
PYEOF

echo "3. 自己テスト"
if "$PY" "$DEST/skills/daily-retro/scripts/verify-gates.py" > /tmp/agr_verify.txt 2>&1; then
  tail -2 /tmp/agr_verify.txt | sed 's/^/   /'
else
  echo "   ★一部のゲートが発火していません:"
  grep -E '★NG|落ちた|  -' /tmp/agr_verify.txt | sed 's/^/   /' || true
  echo "   詳細: /tmp/agr_verify.txt"
fi

cat <<'NOTE'

残り1つ、手でやること:
  CLAUDE.example.md を読み、自分の環境（memory の絶対パス・日報の置き場所）に
  合わせてから ~/.claude/CLAUDE.md として置いてください。
  そのまま置くと <project-scope> のようなプレースホルダが残ります。
NOTE
