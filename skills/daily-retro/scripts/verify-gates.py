#!/usr/bin/env python3
"""Self-test for the registered guards: prove each one actually fires.

The worst failure mode is a check that passes everything while broken. That
happened three times: three staleness detectors, all 18 memories "active"
every time. Without reading the numbers it would have been reported healthy.

So each gate gets input that must trip it, and input that must not.

    python3 verify-gates.py
"""
from __future__ import annotations
import json, pathlib, subprocess, sys, tempfile

HOME = pathlib.Path.home()
HOOKS = HOME / ".claude" / "hooks"
SETTINGS = HOME / ".claude" / "settings.json"
PY = "/usr/bin/python3"

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    results.append((ok, label))
    print(f"  [{'OK' if ok else 'FAIL'}] {label}")


def transcript(text: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    f.write(json.dumps({"type": "assistant",
                        "message": {"content": [{"type": "text", "text": text}]}}))
    f.close()
    return f.name


def run(script: pathlib.Path, payload: dict):
    r = subprocess.run([PY, str(script)], input=json.dumps(payload),
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


print("1. Reply check (reply_check.py)")
rc = HOOKS / "reply_check.py"
if rc.exists():
    _, out, _ = run(rc, {"transcript_path": transcript("Deployed and verified. I cannot proceed.")})
    check("status" in out and "完了を主張" in out, "detects a bad reply")
    _, out2, _ = run(rc, {"transcript_path": transcript(
        "Done.\n\n**Status — running:** nothing. **Waiting:** you. **Stopped:** all.")})
    check(out2 == "", "stays silent on a good reply")
else:
    check(False, "reply_check.py exists")

print("2. Outward-action guard (outward_action_guard.py)")
og = HOOKS / "outward_action_guard.py"
if og.exists():
    for cmd, want, label in [
        ("gh pr create --title x", 2, "blocks PR creation"),
        ("git push origin main", 2, "blocks push"),
        ("gh pr view 1", 0, "allows read-only"),
        ("CLAUDE_OUTWARD_OK=1 gh pr create --title x", 0, "allows explicit override"),
    ]:
        code, _, _ = run(og, {"tool_name": "Bash", "tool_input": {"command": cmd}})
        check(code == want, label)
else:
    check(False, "outward_action_guard.py exists")

print("2b. Exit code after a pipe (outward_action_guard.py)")
if og.exists():
    for cmd, want, label in [
        ("python3 check.py | tail -6; echo $?", 2, "blocks $? after a pipe"),
        ("python3 check.py > /tmp/o.txt 2>&1; echo EXIT=$?", 0, "allows the redirect form"),
        ("ls | head -5", 0, "allows a pipe that ignores $?"),
        ("python3 - <<'PY'\nprint('x | tail -1; echo $?')\nPY", 0, "ignores heredoc contents"),
        ('bash -c "gh pr create -t x"', 2, "still catches a quoted PR create"),
    ]:
        code, _, _ = run(og, {"tool_name": "Bash", "tool_input": {"command": cmd}})
        check(code == want, label)

print("2c. Guard-the-guards (guard_the_guards.py)")
gg = HOOKS / "guard_the_guards.py"
if gg.exists():
    for path, want, label in [
        (str(HOOKS / "reply_check.py"), True, "asks before editing a hook"),
        (str(HOME / ".claude" / "settings.json"), True, "asks before editing settings"),
        ("/tmp/unrelated.md", False, "passes unrelated files"),
    ]:
        _, out, _ = run(gg, {"tool_name": "Edit", "tool_input": {"file_path": path}})
        check(("permissionDecision" in out) == want, label)
else:
    check(False, "guard_the_guards.py exists")

print("3. Daily-report reminder (daily-retro-reminder.sh)")
dr = HOOKS / "daily-retro-reminder.sh"
if dr.exists():
    r = subprocess.run(["sh", str(dr)],
                       input=json.dumps({"tool_input": {"file_path": "/x/日報/a.md"}}),
                       capture_output=True, text=True)
    check("daily-retro" in r.stdout, "fires on a daily-report write")
    r2 = subprocess.run(["sh", str(dr)],
                        input=json.dumps({"tool_input": {"file_path": "/x/other.md"}}),
                        capture_output=True, text=True)
    check(r2.stdout.strip() == "", "silent on unrelated files")
else:
    check(False, "daily-retro-reminder.sh exists")

print("4. Registration (settings.json)")
try:
    conf = json.dumps(json.loads(SETTINGS.read_text(encoding="utf-8")).get("hooks", {}))
    for name in ("reply_check.py", "outward_action_guard.py", "daily-retro-reminder.sh"):
        check(name in conf, f"{name} is registered")
    for name in ("guard_the_guards.py",):
        check(name in conf, f"{name} is registered")
except Exception as e:
    check(False, f"settings.json readable ({e})")

print("5. Applies in every directory")
#
# フックとスキルは ~/.claude 配下にあるので、どのディレクトリで起動しても効く。
# 効かないのは「文字で書いた原則」のほう——memory はディレクトリ単位で分かれる。
# だから共通の原則は ~/.claude/CLAUDE.md（毎回読まれる）に置き、そこから
# memory の絶対パスを指す。この構造が崩れていないかを見る。
#
gmd = HOME / ".claude" / "CLAUDE.md"
if gmd.exists():
    check(True, "~/.claude/CLAUDE.md exists (loaded everywhere)")
    body = gmd.read_text(encoding="utf-8")
    check("memory" in body, "CLAUDE.md points at the memory location")
    check("status" in body.lower(), "CLAUDE.md carries the status-block rule")
    check(len(body.encode()) < 6000, f"injection size sane ({len(body.encode())} bytes < 6000)")
else:
    # 導入直後はまだ無い。壊れているのではなく設定が残っているだけなので
    # 赤にしない（初回導入が失敗に見えると、人は自己テストを信用しなくなる）。
    print("  [--] ~/.claude/CLAUDE.md not installed - adapt CLAUDE.example.md and place it")

# フックがユーザー全体の設定に入っているか（プロジェクト設定だと他所で効かない）
check(SETTINGS.exists(), "hooks live in the user-level settings.json")

# memory のスコープは人によって違うので、最大のものを自動検出する。
# パスを決め打ちすると他人の環境では絶対に通らない検査になる。
projects = HOME / ".claude" / "projects"
scopes = sorted(((len(list((d / "memory").glob("*.md"))), d.name)
                 for d in projects.glob("*") if (d / "memory").is_dir()), reverse=True)
if scopes and scopes[0][0] > 0:
    n, name = scopes[0]
    check(True, f"memory is alive (largest scope {name}: {n} files)")
    if len(scopes) > 1 and sum(c for c, _ in scopes[1:]) > 0:
        others = ", ".join(f"{nm}:{c}" for c, nm in scopes[1:] if c)
        print(f"  [--] other scopes also hold memory ({others}) - what loads depends on where you start")
else:
    print("  [--] no memory yet (normal right after install)")

bad = [l for ok, l in results if not ok]
print(f"\n{len(results) - len(bad)}/{len(results)} passed")
if bad:
    print("failed:")
    for l in bad:
        print("  -", l)
sys.exit(1 if bad else 0)
