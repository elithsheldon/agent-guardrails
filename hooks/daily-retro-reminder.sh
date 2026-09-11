#!/bin/sh
# 日報を書いたら、その場で自己改善ループを走らせるよう促す。
#
# 「毎日やる」を記憶に頼ると必ず抜けるので、ファイル書き込みを検知して機械的に出す。
# 人の注意力ではなく、機械で担保する。
#
# PostToolUse (Write|Edit) で発火。stdin に tool 呼び出しの JSON が来る。
/usr/bin/python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
path = (d.get("tool_input") or {}).get("file_path") or ""
if "/日報/" not in path:
    sys.exit(0)
print(
    "日報を更新しました。daily-retro スキルの手順2〜4がまだ残っています:\n"
    "  2. 今日のミス・指摘を1件ずつ、はしごのできるだけ下（preflight / test / 権限）へ落とす\n"
    "  3. 今日の文章を references/writing-criteria.md と突き合わせ、新しい基準があれば追記する\n"
    "  4. 恒久的な学びは memory / skill / 対象リポジトリのゲートへ書き、何を追加したか1〜2行で報告する\n"
    "メモを足すだけで終わらせないこと。チェックやテストにできるなら、そちらにする。"
)
'
exit 0
