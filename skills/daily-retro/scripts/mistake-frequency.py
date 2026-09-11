#!/usr/bin/env python3
"""過去の会話から「ユーザーに訂正された回数」をパターン別に数える。

印象で「もう直った」と判断しないための計測。1回だけのミスと、何度も繰り返している
ミスを区別する。繰り返しているものは、メモを増やしても直らない。機械で止める。

    python3 mistake-frequency.py            # 集計
    python3 mistake-frequency.py --stale    # 参照されなくなったメモリを出す

新しい訂正パターンに気付いたら SIGNALS に追加すること。
"""
from __future__ import annotations
import collections, json, pathlib, re, sys

PROJECTS = pathlib.Path.home() / ".claude" / "projects"

# ユーザーが訂正しているときの強いシグナルだけ。広く取るとノイズに埋もれる。
SIGNALS = {
    "writing-quality":    r"writing problem|reader'?s perspective|too long|clear indication|hard to understand|読みづらい|分かりにく",
    "premature-claim":    r"not doing it right|i don'?t think you|make sure you'?ve|are you sure|本当に|確認した",
    "scope-overreach":    r"did i ask|didn'?t ask|why did you (decide|implement)|close the pr|勝手に",
    "unverified-blocked": r"can you solve|i don'?t think you could|avoiding these process|maximize your effort",
    "missed-instruction": r"i (already )?(told|asked) you|as i said|もう一度|さっき言った",
    "wrong-target":       r"i mean |wrong (project|repo|env)|案件.*違",
}


def user_messages():
    for f in sorted(PROJECTS.rglob("*.jsonl")):
        try:
            with f.open(encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if '"user"' not in line:
                        continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    if d.get("type") != "user":
                        continue
                    c = (d.get("message") or {}).get("content")
                    if isinstance(c, list):
                        txt = " ".join(x.get("text", "") for x in c
                                       if isinstance(x, dict) and x.get("type") == "text")
                    elif isinstance(c, str):
                        txt = c
                    else:
                        continue
                    if not txt.strip() or len(txt) > 4000:
                        continue
                    if txt.lstrip().startswith(("<system-reminder", "Caveat:", "<command-")):
                        continue
                    yield f, txt
        except Exception:
            continue


def frequency():
    counts, examples, total = collections.Counter(), collections.defaultdict(list), 0
    for _f, txt in user_messages():
        total += 1
        low = txt.lower()
        for name, pat in SIGNALS.items():
            if re.search(pat, low):
                counts[name] += 1
                if len(examples[name]) < 2:
                    examples[name].append(txt.strip().replace("\n", " ")[:100])
    print(f"ユーザー発言 {total} 件 / 訂正シグナル {sum(counts.values())} 件\n")
    print(f"{'回数':>4}  パターン              扱い")
    for name, n in counts.most_common():
        verdict = "★機械で止める" if n >= 5 else "基準に残す"
        print(f"{n:>4}  {name:<20} {verdict}")
        for e in examples[name]:
            print(f"        「{e}」")
    print("\n5回以上 = 繰り返している = メモでは直らない。preflight / hook / 権限にする。")


def stale():
    """直近セッションで一度も触れられていないメモリを出す。

    判定は「ファイル名の最も特徴的な語」が出るかどうか。ゆるい一致だと全部
    『現役』になって何も検出できない (実際に一度それで失敗した)。
    """
    mem = PROJECTS / "<project-scope>" / "memory"
    recent = sorted(PROJECTS.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
    # 会話本文だけを集める。JSONL 全体を数えるとツール出力やコードに埋もれて
    # 全部「現役」になる (2回それで失敗した)。
    parts = []
    for f in recent:
        try:
            with f.open(encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    if d.get("type") not in ("user", "assistant"):
                        continue
                    c = (d.get("message") or {}).get("content")
                    if isinstance(c, list):
                        for x in c:
                            if isinstance(x, dict) and x.get("type") == "text":
                                parts.append(x.get("text", ""))
                    elif isinstance(c, str):
                        parts.append(c)
        except Exception:
            continue
    blob = "\n".join(parts).lower()
    common = {"access", "required", "config", "paths", "setup", "loop", "name", "semantics"}
    #
    # ⚠️ この指標の限界 (実測して分かったこと)
    #
    # 絶対しきい値では判定できない。ファイル名の語が普通の会話語 (benchmark, server,
    # access 等) と重なるため、どんなしきい値でも全部「現役」になる。3回試して3回とも
    # 全件パスした。全部通る検査は、何も検査していない。
    #
    # そこで相対順位にしている。「死んでいる」ではなく「相対的に参照が薄い」としか
    # 言えない。退役の判断は人が見ること。本当に必要なのは「そのメモリが実際に
    # 想起されたか」のログで、それは今は取れていない。
    #
    scored = []
    for m in sorted(mem.glob("*.md")):
        if m.name == "MEMORY.md":
            continue
        toks = [t for t in m.stem.split("-") if len(t) > 4 and t not in common]
        hits = sum(blob.count(t) for t in toks) if toks else -1
        scored.append((hits, m.stem))
    scored.sort()
    n = len(scored)
    print(f"直近10セッションの会話本文での言及（相対順位 / {n}件）:\n")
    for i, (hits, stem) in enumerate(scored):
        mark = "★参照が薄い" if i < n // 3 else ("中位" if i < 2 * n // 3 else "よく出る")
        print(f"  {mark:<12} {stem}  (出現 {hits})")
    print("\n下位1/3は退役候補。ただし相対値なので、消す前に必ず中身を読むこと。")
    print("この指標は『使われたか』ではなく『話題に出たか』しか見ていない。")


if __name__ == "__main__":
    stale() if "--stale" in sys.argv else frequency()
