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


# ── 文体の癖（2026-09-12 追加）────────────────────────────────────
#
# 出典: writing_skills_20260912 の check_voice.py / check_defensive.py。
# あちらは8人のゼロコンテキスト読者が4本の論文を「人が書いたと読めるか」で
# 3-6/10 と採点し、同じ癖を名指しした実測に基づく較正値。
#
# 自分の返信 1702 件 / 13.3万語を測ったところ:
#   「, not 」対比  2.6/千語（目標 0.7）… 3.7倍
#   「, so 」因果尾 4.0/千語（目標 2）
#   数え上げ導入    77 回、cleft 導入 32 回、throat clearing 18 回（目標 0）
# 1返信あたりに直すと、対比は約1回・他はほぼ0回。だから
# 対比は2回以上、他は1回でも出たら知らせる。
VOICE = [
    ("contrast", 2,
     r", not (?:a |an |the |to |of |in |on |by |its |their |that |which )?\w+",
     "「X, not Y」の対比構文が多いです。これは機械が書いた文章の最も分かりやすい signature です。"
     "片方を落として言い切るか、二文に分けてください"),
    ("inventory", 1,
     r"\b(?:Two|Three|Four|Five|Six)\s+\w+(?:\s+\w+)?\s+(?:are|stay|remain|worth|things?)\b",
     "「Two things…」型の数え上げ導入です。数を予告せず、そのまま本題から書き始めてください"),
    ("cleft", 1,
     r"\bWhat \w+(?: \w+){0,5} is\b",
     "「What matters is…」型の cleft 導入です。主語から普通に書き始めてください"),
    ("throat", 1,
     r"\b(?:it\s+is\s+(?:important|worth)\s+(?:to\s+)?(?:not(?:e|ing)|mention(?:ing)?)"
     r"|it\s+should\s+be\s+noted\s+that|worth\s+noting)\b",
     "「worth noting that」型の前置きです。前置きを消して、中身から書いてください"),
]

# ── 機械の痕跡・AI 常套句（2026-09-12 追加）──────────────────────
#
# 出典: writing_skills_20260912 の check_ai_isms.py（P0/P1 tier）。
# 元は conorbronsdon/avoid-ai-writing (MIT) から学術散文向けに絞り込んだもの。
#
# ⚠️ 自分の返信 13.8万語での実測は P0 3件・P1 3件で、ほぼ出ない。
# 頻度で言えば文体の癖（VOICE）のほうが100倍多い。それでも入れるのは、
# ここに1件出るのが日報や Slack 下書きだと事故になるから——回帰の見張り。
# 誤検知はほぼ無いので閾値は1件。
LEAKS = [
    (r"\bas an? (?:ai|artificial intelligence|large language|ai language) (?:language )?model\b"
     r"|\bas of my (?:knowledge )?(?:last update|cut-?off|last training)\b"
     r"|\bi don'?t have access to real-?time (?:data|information)\b",
     "モデル自身についての定型句が混ざっています"),
    (r"\bi hope this helps\b|\bgreat question\b|\bexcellent point\b"
     r"|\bfeel free to reach out\b|\byou'?re absolutely right\b"
     r"|\blet me think step by step\b|\bhere'?s my thought process\b"
     r"|\bto answer your question\b|\blet'?s dive in\b",
     "チャットボット的な決まり文句です。中身だけ書いてください"),
    (r"\[(?:Your|Insert|Add|Enter|Describe|Specify|Choose|Pick)\b[^\]\n]{1,80}\]"
     r"|\b(?:19|20)\d{2}-XX-XX\b",
     "未置換のプレースホルダが残っています"),
    ("[​‌‍﻿⁠]|[A-Za-z][Ѐ-ӿ]|[Ѐ-ӿ][A-Za-z]",
     "不可視文字またはキリル文字の混入です（貼り付け事故）"),
    (r"\bdelve\s+into\b|\bdeep\s+dive\b|\bwhen\s+it\s+comes\s+to\b"
     r"|\bat\s+the\s+end\s+of\s+the\s+day\b|\bdue\s+to\s+the\s+fact\s+that\b"
     r"|\bnot\s+only\b[^.;]{0,120}\bbut\s+also\b|\b(?:firstly|secondly|thirdly)\b",
     "AI 常套句です。普通の言い方に置き換えてください"),
    (r"\b(?:seamless(?:ly)?|pivotal|meticulous(?:ly)?|holistic(?:ally)?|impactful"
     r"|myriad|plethora|cornerstone|multifaceted|showcase[sd]?|showcasing"
     r"|tapestry|beacon|game-chang(?:er|ing)|cutting-edge)\b",
     "中身の無い形容です。具体的な事実に置き換えてください"),
]

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

    # 文体の癖。コードブロックと表は散文ではないので除いてから数える。
    prose = re.sub(r"```.*?```", " ", text, flags=re.S)
    prose = re.sub(r"^\s*\|.*$", " ", prose, flags=re.M)
    prose = re.sub(r"`[^`]*`", " ", prose)
    for _name, limit, pat, msg in VOICE:
        hits = len(re.findall(pat, prose, re.I))
        if hits >= limit:
            flags.append(f"{msg}（{hits}箇所）")
    for pat, msg in LEAKS:
        hits = re.findall(pat, prose, re.I)
        if hits:
            sample = str(hits[0])[:40]
            flags.append(f"{msg}: 「{sample}」")
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
