#!/usr/bin/env python3
"""登録されている防御が、本当に発火するかを確かめる。

一番危ないのは「壊れているのに全部通る検査」。実際に3回やらかした:
陳腐化検出を3通り書いて、3回とも18件全部『現役』と出した。読まなければ
「健全」と報告していた。

だからここでは、わざと引っかかる入力を食わせて、止まることを確認する。
通る入力も食わせて、誤検知しないことも確認する。

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
    print(f"  [{'OK' if ok else '★NG'}] {label}")


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


print("1. 返信チェック (reply_check.py)")
rc = HOOKS / "reply_check.py"
if rc.exists():
    _, out, _ = run(rc, {"transcript_path": transcript("Deployed and verified. I cannot proceed.")})
    check("status" in out and "完了を主張" in out, "悪い返信を検出する")
    _, out2, _ = run(rc, {"transcript_path": transcript(
        "Done.\n\n**Status — running:** nothing. **Waiting:** you. **Stopped:** all.")})
    check(out2 == "", "良い返信では黙る（誤検知しない）")
else:
    check(False, "reply_check.py が存在する")

print("2. 外向き操作のガード (outward_action_guard.py)")
og = HOOKS / "outward_action_guard.py"
if og.exists():
    for cmd, want, label in [
        ("gh pr create --title x", 2, "PR 作成を止める"),
        ("git push origin main", 2, "push を止める"),
        ("gh pr view 1", 0, "読み取りは通す"),
        ("CLAUDE_OUTWARD_OK=1 gh pr create --title x", 0, "明示宣言なら通す"),
    ]:
        code, _, _ = run(og, {"tool_name": "Bash", "tool_input": {"command": cmd}})
        check(code == want, label)
else:
    check(False, "outward_action_guard.py が存在する")

print("2b. パイプ後の $? (outward_action_guard.py)")
if og.exists():
    for cmd, want, label in [
        ("python3 check.py | tail -6; echo $?", 2, "パイプ後の $? を止める"),
        ("python3 check.py > /tmp/o.txt 2>&1; echo EXIT=$?", 0, "リダイレクト形は通す"),
        ("ls | head -5", 0, "$? を見ないパイプは通す"),
        ("python3 - <<'PY'\nprint('x | tail -1; echo $?')\nPY", 0, "ヒアドキュメント内は誤検知しない"),
        ('bash -c "gh pr create -t x"', 2, "引用符内の PR 作成も見逃さない"),
    ]:
        code, _, _ = run(og, {"tool_name": "Bash", "tool_input": {"command": cmd}})
        check(code == want, label)

print("2c. 防御側ファイルの保護 (guard_the_guards.py)")
gg = HOOKS / "guard_the_guards.py"
if gg.exists():
    for path, want, label in [
        (str(HOOKS / "reply_check.py"), True, "フックの編集で確認を求める"),
        (str(HOME / ".claude" / "settings.json"), True, "設定の編集で確認を求める"),
        ("/tmp/unrelated.md", False, "無関係なファイルは素通し"),
    ]:
        _, out, _ = run(gg, {"tool_name": "Edit", "tool_input": {"file_path": path}})
        check(("permissionDecision" in out) == want, label)
else:
    check(False, "guard_the_guards.py が存在する")

print("3. 日報リマインダ (daily-retro-reminder.sh)")
dr = HOOKS / "daily-retro-reminder.sh"
if dr.exists():
    r = subprocess.run(["sh", str(dr)],
                       input=json.dumps({"tool_input": {"file_path": "/x/日報/a.md"}}),
                       capture_output=True, text=True)
    check("daily-retro" in r.stdout, "日報の書き込みで発火する")
    r2 = subprocess.run(["sh", str(dr)],
                        input=json.dumps({"tool_input": {"file_path": "/x/other.md"}}),
                        capture_output=True, text=True)
    check(r2.stdout.strip() == "", "無関係なファイルでは黙る")
else:
    check(False, "daily-retro-reminder.sh が存在する")

print("4. 登録状態 (settings.json)")
try:
    conf = json.dumps(json.loads(SETTINGS.read_text(encoding="utf-8")).get("hooks", {}))
    for name in ("reply_check.py", "outward_action_guard.py", "daily-retro-reminder.sh"):
        check(name in conf, f"{name} が登録されている")
    for name in ("guard_the_guards.py",):
        check(name in conf, f"{name} が登録されている")
except Exception as e:
    check(False, f"settings.json を読めた ({e})")

print("5. 全プロジェクトに効いているか（ディレクトリを問わず）")
#
# フックとスキルは ~/.claude 配下にあるので、どのディレクトリで起動しても効く。
# 効かないのは「文字で書いた原則」のほう——memory はディレクトリ単位で分かれる。
# だから共通の原則は ~/.claude/CLAUDE.md（毎回読まれる）に置き、そこから
# memory の絶対パスを指す。この構造が崩れていないかを見る。
#
gmd = HOME / ".claude" / "CLAUDE.md"
if gmd.exists():
    check(True, "~/.claude/CLAUDE.md がある（全ディレクトリ共通）")
    body = gmd.read_text(encoding="utf-8")
    check("memory" in body, "CLAUDE.md が memory の場所を指している")
    check("status" in body.lower(), "CLAUDE.md に status ブロックの規則がある")
    check(len(body.encode()) < 6000, f"注入サイズが妥当（{len(body.encode())}バイト < 6000）")
else:
    # 導入直後はまだ無い。壊れているのではなく設定が残っているだけなので
    # 赤にしない（初回導入が失敗に見えると、人は自己テストを信用しなくなる）。
    print("  [--] ~/.claude/CLAUDE.md が未設置 — CLAUDE.example.md を自環境に合わせて置く")

# フックがユーザー全体の設定に入っているか（プロジェクト設定だと他所で効かない）
check(SETTINGS.exists(), "フックがユーザー全体の settings.json にある")

# memory のスコープは人によって違うので、最大のものを自動検出する。
# パスを決め打ちすると他人の環境では絶対に通らない検査になる。
projects = HOME / ".claude" / "projects"
scopes = sorted(((len(list((d / "memory").glob("*.md"))), d.name)
                 for d in projects.glob("*") if (d / "memory").is_dir()), reverse=True)
if scopes and scopes[0][0] > 0:
    n, name = scopes[0]
    check(True, f"memory が生きている（最大スコープ {name}: {n} 件）")
    if len(scopes) > 1 and sum(c for c, _ in scopes[1:]) > 0:
        others = ", ".join(f"{nm}:{c}" for c, nm in scopes[1:] if c)
        print(f"  [--] 別スコープにも memory があります（{others}）— 起動場所で読まれ方が変わる")
else:
    print("  [--] memory がまだありません（導入直後なら正常）")

bad = [l for ok, l in results if not ok]
print(f"\n{len(results) - len(bad)}/{len(results)} 通過")
if bad:
    print("落ちた項目:")
    for l in bad:
        print("  -", l)
sys.exit(1 if bad else 0)
