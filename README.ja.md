# agent-guardrails

[English](README.md) · **日本語** · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Bahasa Melayu](README.ms.md) · [ไทย](README.th.md)

Claude Code 用の**防御フック集**。エージェントが同じ失敗を繰り返さないように、
覚え書きではなく**機械で止める**ための最小セット。

> 人の注意力ではなく、機械で担保する。

## なぜ作ったか

30セッション・ユーザー発言 887 件を実測したところ、ユーザーに訂正された箇所が
**44 件**あり、パターンは 6 種に収束した。そして**そのすべてが「文章で書いた注意書き」
だけで守られていた**。注意書きは既に書いてあり、それでも同じ失敗が起きていた。

| 実測回数 | パターン | 対策 |
| --- | --- | --- |
| 12 | 文章・提示の質 | `reply_check.py` が検出 |
| 9 | 早すぎる完了主張 | `reply_check.py` が検出 |
| 9 | 頼まれていない成果物を出す | `outward_action_guard.py` が拒否 |
| 7 | 試さずに「できない」と言う | `reply_check.py` が検出 |
| 4 | 指示の読み落とし | 基準ファイルに記載（閾値未満） |
| 3 | 対象の取り違え | 基準ファイルに記載（閾値未満） |

**5回以上＝繰り返している＝注意書きでは直らない**、を採否の線にしている。
注意書きは既に一度失敗している。4回以下は文章のまま残す。全部をゲートにすると
警告が飽和して読まれなくなる。

## 入っているもの

### フック（`~/.claude/settings.json` に登録して常時稼働）

| ファイル | イベント | 何をするか |
| --- | --- | --- |
| `reply_check.py` | Stop | status ブロックの欠落、根拠のない完了主張、試さずの「できない」、機械が書いたと読める構文（`X, not Y` 対比・数え上げ導入・cleft 導入・前置き）、チャットボット的な決まり文句を検出。**警告のみ**（Stop で止めるとループの危険） |
| `outward_action_guard.py` | PreToolUse(Bash) | 取り消しにくい外向き操作（PR / push / リポジトリ作成 / リリース / gist）を**拒否**。あわせて `<検査> \| tail; echo $?` も拒否——それは検査ではなく `tail` の終了コード |
| `guard_the_guards.py` | PreToolUse(Edit/Write) | 検査器・フック・設定・memory の編集時に確認を求める。**検査に落ちたとき産物ではなく採点者を書き換える**のを防ぐ |
| `daily-retro-reminder.sh` | PostToolUse | 日報を書いたら振り返り手順を催促 |

### スキル

`skills/daily-retro/` — 日報を書くタイミングを起点にした改善ループ。
ミスを次のはしごの**できるだけ下**へ落とす:

> memory → doc → script → preflight → test → 権限

### スクリプト

| ファイル | 用途 |
| --- | --- |
| `mistake-frequency.py` | 過去の全会話から訂正パターンを**数える**。「もう直した」を印象でなく実測で判断するため |
| `verify-gates.py` | **ゲート自身の自己テスト**。落ちるべき入力と通るべき入力の両方を食わせる |

### 参考資料

`reference/anti-self-deception/` — 別チームの成熟した防錯機構一式（24規則・15スクリプト・
29の常駐チェック）。許諾を得て匿名化のうえ収録。詳細は同ディレクトリの `ATTRIBUTION.md`。

## 特に効いた2つ

**`guard_the_guards.py`** — 他の防御はすべて「産物」を見ていて、
**審査される側が採点者を書き換える**のを止める段が無かった。
フックと自己テストを作った直後、それらを自由に書き換えられる状態だった。

**`verify-gates.py`** — 陳腐化検出を3通り書いて、3回とも18件全部パスした。
数字を読まなければ「健全」と3回報告していた。
**一度も落ちたことのない検査は、何も守っていない可能性がある。**

## 導入

取得して `bash install.sh`。`~/.claude/hooks/` と `~/.claude/skills/` へコピーし、
`~/.claude/settings.json` にフックを登録する（追記のみ・既存設定は保持）。

`CLAUDE.example.md` は中身を読み、自分の環境（memory の絶対パス・日報の置き場所）に
合わせてから `~/.claude/CLAUDE.md` に置くこと。

導入後は必ず自己テストを走らせる:

    python3 ~/.claude/skills/daily-retro/scripts/verify-gates.py

新規環境 21/21、設定済み環境 26/26 で通している。

## 注意

- フックは `~/.claude/` に置くので**全ディレクトリで効く**。一方 memory は起動
  ディレクトリ単位で分かれるため、共通の原則は毎回読まれる `~/.claude/CLAUDE.md` に置く。
- `outward_action_guard.py` は push を止める。意図したものは `CLAUDE_OUTWARD_OK=1` を付ける。
  煩わしければ `GUARDED` の一覧から外す。
- `reply_check.py` は正規表現なので誤検知する。うるさければ**消さずに狭める**こと。

## 謝辞

`reference/anti-self-deception/` の規則・スクリプト・常駐チェックは
[@Karas-cnk](https://github.com/Karas-cnk) の著作物で、許諾を得て収録しています。`guard_the_guards.py` と
`outward_action_guard.py` のパイプ／終了コード規則はここから移植したものです。

## ライセンス

MIT
