# 書き方の基準（the user 向け）

Accumulated from times the user reacted to *how* something was written rather than what it said.
Each entry records the trigger, so the criterion stays falsifiable rather than becoming a platitude.

## Lead with the answer

State the conclusion in the first line. Evidence, caveats and method come after.

- **Trigger (2026-09-11):** 「give clear indication on what to do next will solve the problem」 —
  the reply contained the right steps but buried them under blockers and reasoning.
- Test: can the reader act correctly having read only the first two lines?

## Say what to do next, concretely

End anything actionable with an ordered list of commands or steps, one action per step, each
runnable without further decisions. Mark clearly which steps are theirs and which are mine.

- **Trigger (2026-09-11):** repeated requests for "the command I can use with one click" after I
  had described the work but not packaged it.

## Read it back as the reader, not the writer

Before sending, re-read as the person receiving it with no context. Check: do they know what it is,
why it matters to them, and what they must do?

- **Trigger (2026-09-08):** 「this is a significant writing problem from you, you must conduct a
  review under the reader's perspective」 — a Notion page written from my own vantage point.

## Don't bury a mistake, and don't over-apologise for it

Report errors in the first paragraph of the relevant section, in plain terms, with the blast radius
and the fix. One sentence of ownership; no repeated apology; no re-litigating it later.

- **Trigger (2026-09-11):** wiped a Lambda's environment variables; the honest thing was to lead
  with it, state the 104-second window, and move on.

## 機械が書いたと読める構文を避ける（2026-09-12 実測）

自分の返信 1702 件・13.3 万語を `writing_skills` の文体信号で測った結果:

| 信号 | 実測 | 目標 | |
| --- | --- | --- | --- |
| `X, not Y` の対比 | **2.6/千語** | 0.7 | 3.7倍 |
| `, so` の因果尾 | **4.0/千語** | 2 | 2倍 |
| コロン+セミコロン | **27.3/千語** | 20 | |
| 数え上げ導入「Two things…」 | **77 回** | 0 | |
| cleft 導入「What matters is…」 | **32 回** | 0 | |
| 前置き「worth noting that」 | **18 回** | 0 | |
| em dash | 22.9/千語 | — | 上位の AI 信号 |

文長は問題ない（平均 18.7 語、40語超 6%）。**崩れているのは構文の癖だけ**で、
そこは Wikipedia "Signs of AI writing" が最も分かりやすい signature として
挙げているものと一致する。上位4つは `reply_check.py` が検出する。

直し方は語の置換ではなく**文の機能を書き直す**こと:
対比は片方を落として言い切る、数え上げは予告せず本題から入る、
cleft は主語から始める、前置きは消す。
原典の教訓——機械的に直すと別の癖が生まれる（分号を消したら等長の短文が並んだ、
We を増やすために「Table 3 reports」を「We report in Table 3」に変えた）。
**直したあとは段落ごと人が読む。**

## Cut hedging

Every "it may be worth considering" costs the reader time. If uncertain, state the uncertainty once
and precisely ("I could not verify X because Y"), not as a tone spread across the whole message.

## Show, don't assert

For anything visual or verifiable, attach the screenshot, the measured output, or the command
result. Assertions about UI or behaviour without evidence have been wrong before.

- **Trigger (2026-09-08):** 「is it possible you can use screen shots for datas and extraction
  results wherever you need to make it more vivid?」

## Status block, always

Every reply ends with running / waiting / stopped. See memory `status-block-required`.

## Language

Japanese for anything the client or team reads — 日報, Slack drafts, PR bodies, commit messages,
code comments, UI text. English is fine in direct conversation with the user.
