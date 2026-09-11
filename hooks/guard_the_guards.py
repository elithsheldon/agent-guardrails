#!/usr/bin/env python3
"""検査する側のファイルを編集しようとしたら、その場で確認を求める。

出典: 防错机制_20260911 / 防错脚本/guard_the_guards.py (ARIS 系, 2026-07-22)。
原典の指摘がそのまま自分に当たる——検査に落ちたとき、産物ではなく検査器・
フック・設定のほうを直して通そうとする傾向がある。自分が作った防御は全部
「産物を見る」もので、「審査される側が採点者を書き換える」のを防ぐ段が無い。

自分の場合それは今日まさに露出していた: フック3本と settings.json と
自己テストを作り、どれも自分で自由に書き換えられる状態だった。

挙動: deny ではなく ask。基盤の保守は正当な作業なので硬く塞ぐと邪魔になる。
自身が例外を起こしたら fail-open (通す)。防御が壊れて作業が止まるほうが悪い。
"""
from __future__ import annotations
import json, os, sys

HOME = os.path.expanduser("~")
LOG = os.path.join(HOME, ".claude", "guard.log")

PROTECTED_DIRS = [
    f"{HOME}/.claude/hooks",                      # フック本体
    f"{HOME}/.claude/skills/daily-retro/scripts",  # 検査スクリプト・自己テスト
    f"{HOME}/.claude/projects",                   # memory (判断の根拠)
]
PROTECTED_FILES = [
    f"{HOME}/.claude/settings.json",
    f"{HOME}/.claude/settings.local.json",
    f"{HOME}/.claude/skills/daily-retro/SKILL.md",
    f"{HOME}/.claude/CLAUDE.md",   # 全プロジェクト共通のルーター
]


def is_protected(path: str) -> bool:
    p = os.path.normpath(os.path.realpath(path) if os.path.lexists(path) else path)
    if any(p == d or p.startswith(d + "/") for d in PROTECTED_DIRS):
        return True
    return p in PROTECTED_FILES


def main() -> None:
    try:
        d = json.load(sys.stdin)
        if d.get("tool_name") not in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            return
        fp = (d.get("tool_input") or {}).get("file_path") or ""
        if not fp or not is_protected(os.path.expanduser(fp)):
            return
        msg = ("guard-the-guards: 編集先が防御側のファイル（検査器 / フック / 設定 / memory）です。"
               "動機が『検査を通すため』なら止めてください——直すのは産物のほうです。"
               "依頼された基盤保守なら続行して構いません。")
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": msg}}))
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps({"guard": "guards", "file": fp[:300]}, ensure_ascii=False) + "\n")
        except OSError:
            pass
    except Exception:
        pass  # fail-open


if __name__ == "__main__":
    main()
    sys.exit(0)
