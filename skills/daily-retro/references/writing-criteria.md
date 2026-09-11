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
