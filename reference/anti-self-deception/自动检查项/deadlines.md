---
name: deadlines
predicate: python3 /home/<user>/n-chang/.claude/scripts/check_deadlines.py
manual: false
status: VIOLATED
last-pass: 2026-09-01
---

Personal deadline / errand reminders. Single source = ObsidianVault/_meta/TODO.md
(dated checkboxes with a lead window + recurring monthly-end items, e.g. the
RIKEN monthly timesheet). The predicate fails while an open item is inside its
lead window, which routes it into the daily VIOLATIONS mail and the next
session's opening context. Fix = do the thing, then check the item off (or add
the recurring ack line) in TODO.md. Capture rule: whenever the user states a
new task or date in conversation, it gets written into TODO.md the same turn
([[feedback_todo_capture]] in memory).
