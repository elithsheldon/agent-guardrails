#!/usr/bin/env python3
"""外向きの操作を、依頼されていないのに実行するのを止める。

計測: scope-overreach は過去 9 回指摘されている。メモリ
`unanswered-proposal-is-not-approval` を書いた後にも PR #107 を出して怒られた。
文字の注意書きでは止まらなかったので、実際に止める。

PreToolUse(Bash) で発火。該当コマンドは exit 2 で拒否し、理由を返す。
本当に依頼されているなら、環境変数 CLAUDE_OUTWARD_OK=1 を付けて実行する
（＝「これは頼まれた」と明示的に宣言する一手間を課す）。
"""
from __future__ import annotations
import json, os, re, sys

# 取り消しにくい / 相手に届く操作
GUARDED = [
    (r"\bgh\s+pr\s+create\b",            "PR の作成"),
    (r"\bgh\s+pr\s+merge\b",             "PR のマージ"),
    (r"\bgh\s+(issue|pr)\s+comment\b",   "GitHub へのコメント"),
    (r"\bgh\s+issue\s+create\b",         "Issue の作成"),
    (r"\bgit\s+push\b",                  "push"),
    (r"\bgh\s+repo\s+create\b",          "リポジトリの作成"),
    (r"\bgh\s+release\s+create\b",       "リリースの公開"),
    (r"\bgh\s+gist\s+create\b",          "gist の公開"),
]


# パイプの先の退出コードを見てしまう形。
# 出典: 防错机制_20260911 規則 16b / 28。あちらは同じ誤りを4回繰り返し
# 「覚えている、では足りない。コマンドを書くときの手の形にする」と結論している。
# 自分も今日 verify-gates.py で踏んだ（tail の 0 を自分の 0 と読んだ）。
# `... | tail ...; echo $?` の $? はパイプ最後のコマンドのもので、検査の結果ではない。
PIPE_THEN_STATUS = re.compile(r"\|\s*(head|tail|grep|cut|sed|awk)\b[^|]*(;|&&)\s*(echo\s+)?[\"']?.*\$\?")


def _strip_heredoc(cmd: str) -> str:
    """ヒアドキュメントの本文を落とす（スクリプトやテストデータの中身）。"""
    return re.sub(r"<<-?\s*['\"]?(\w+)['\"]?.*?^\1\s*$", " ", cmd, flags=re.S | re.M)


def _strip_literals(cmd: str) -> str:
    """ヒアドキュメント本文に加えて引用符の中身も落とす。

    これを入れないと、テストデータとして書いた文字列に反応する（最初の版で
    自分のテストコマンドを誤検知した）。

    ⚠️ 落とす強さを2種類に分けている理由:
    パイプ検査は誤検知が邪魔なので強く落とす。外向き操作の検査は
    **見逃しのほうが危険**なので引用符の中は落とさない——
    `bash -c "gh pr create ..."` を素通ししてしまうため。
    """
    cmd = _strip_heredoc(cmd)
    cmd = re.sub(r"'[^']*'", " ", cmd)
    cmd = re.sub(r'"[^"]*"', " ", cmd)
    return cmd


def check_pipe_status(cmd: str) -> str | None:
    if PIPE_THEN_STATUS.search(_strip_literals(cmd)):
        return (
            "[pipe-status-guard] パイプの後で $? を見ています。それはパイプ最後の\n"
            "コマンド（head/tail/grep など）の退出コードで、検査スクリプトのものではありません。\n"
            "合否の判断に使うなら、先にファイルへリダイレクトしてから取ってください:\n"
            "    python3 <検査> > /tmp/out.txt 2>&1; echo \"EXIT=$?\"; tail -3 /tmp/out.txt\n"
            "出力を眺めるだけならパイプで構いません。"
        )
    return None


def main() -> int:
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    if d.get("tool_name") != "Bash":
        return 0
    cmd = (d.get("tool_input") or {}).get("command") or ""

    warn = check_pipe_status(cmd)
    if warn:
        print(warn, file=sys.stderr)
        return 2
    if os.environ.get("CLAUDE_OUTWARD_OK") == "1" or "CLAUDE_OUTWARD_OK=1" in cmd:
        return 0
    scanned = _strip_heredoc(cmd)  # 引用符の中は残す（見逃し防止）
    for pat, label in GUARDED:
        if re.search(pat, scanned):
            print(
                f"[outward-action-guard] {label} をしようとしています。\n"
                "ユーザーがこの成果物を名指しで依頼しましたか。症状の報告や相談は依頼ではありません。\n"
                "依頼されていないなら実行せず、まず提案して承認を取ってください。\n"
                "依頼されているなら CLAUDE_OUTWARD_OK=1 を付けて再実行してください。",
                file=sys.stderr,
            )
            return 2  # PreToolUse で 2 は拒否 + 理由をモデルへ返す
    return 0


if __name__ == "__main__":
    sys.exit(main())
