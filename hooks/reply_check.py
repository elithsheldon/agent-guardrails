#!/usr/bin/env python3
"""返信を出す直前に、繰り返し指摘されているパターンを機械的に検出する。

対象は mistake-frequency.py で5回以上計測されたものだけ:
  writing-quality(12) / premature-claim(9) / unverified-blocked(7)
4回以下は基準ファイルに留める。全部入れると警告が飽和して読まれなくなる。

止めはしない (Stop フックで止めるとループの危険)。検出して知らせるだけ。
文章の良し悪しは自動判定できないが「構造が欠けている」ことは判定できる。
"""
from __future__ import annotations
import json, pathlib, re, sys


def last_assistant_text(transcript: pathlib.Path) -> str:
    last = ""
    with transcript.open(encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if '"assistant"' not in line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") != "assistant":
                continue
            c = (e.get("message") or {}).get("content")
            if isinstance(c, list):
                t = " ".join(x.get("text", "") for x in c
                             if isinstance(x, dict) and x.get("type") == "text")
                if t.strip():
                    last = t
    return last


CHECKS = [
    # (名前, 検出パターン, 指摘文)
    ("premature-claim",
     r"\bverified\b|\bconfirmed\b|\bdeployed\b|確認済み|完了しました|直りました|解消しています",
     "完了を主張しています。変更点だけでなく『操作そのものが壊していないか』も確かめましたか。"
     "根拠（コマンド出力・スクリーンショット）を本文に置いていますか"),
    ("unverified-blocked",
     r"can'?t\b|cannot\b|\bblocked\b|できません|実行できない",
     "できない/ブロックされたと述べています。実際に試した結果ですか。試さずに判断していませんか"),
]


def review(text: str) -> list[str]:
    low = text.lower()
    flags = []
    if not re.search(r"status\s*[—\-–]|\*\*status", low):
        flags.append("status ブロックがありません（毎回必須 / memory: status-block-required）")
    for _name, pat, msg in CHECKS:
        if re.search(pat, low):
            flags.append(msg)
    if "```bash" in text and not re.search(r"次|next|手順|step|実行して|run ", low):
        flags.append("コマンドを提示していますが、誰が何の順で実行するかが書かれていません")
    return flags


def main() -> int:
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    tp = d.get("transcript_path") or ""
    p = pathlib.Path(tp)
    if not tp or not p.exists():
        return 0
    try:
        text = last_assistant_text(p)
    except Exception:
        return 0
    if not text.strip():
        return 0
    flags = review(text)
    if flags:
        print("返信チェック（繰り返し指摘されているパターン）:")
        for f in flags:
            print("  - " + f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
