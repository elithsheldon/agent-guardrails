---
name: daily-retro
description: Write the daily report (日報) and run the end-of-day improvement loop — convert the day's mistakes into mechanical gates, and review the day's writing against accumulated criteria. Use when writing or updating the 日報, when the user asks for the daily report, or at the end of a working day.
---

# 日報 + 自己改善ループ

Writing the 日報 is the trigger for the day's improvement pass. The report alone is not the
deliverable — **the report plus the gates and criteria it produces** is.

Standing instruction from the user (2026-09-11): improve the mechanism for writing/presentation
and for learning from mistakes, every day, at 日報 time.

## 1. Write the 日報

- Location: `$DAILY_REPORT_DIR/` — filename is `<3-letter weekday><mon><day>.md`, lowercase
  (e.g. `frisep11.md`, `thusep10.md`). Match the most recent file's structure exactly.
- Sections, in order: 日付 / 報告先 / 【取り組んだこと】(Engineering, MTG) / 【進捗】/
  【時間配分】/【明日以降】
- Japanese. Each Engineering bullet states what changed and why it mattered, with the PR/issue
  URL indented under it.
- **Record mistakes plainly in 【取り組んだこと】 and 【進捗】.** A log that hides the day's
  errors is worthless for this loop and reads as evasive to the reader.
- Never invent meetings. Leave `MTG` as a placeholder for the user to fill.

## 2. Retrospective — turn each mistake into a gate

**First, separate one-off from repeat. Measure it; do not judge by impression.**

```
python3 ~/.claude/skills/daily-retro/scripts/mistake-frequency.py
```

This counts, across all past sessions, how often the user had to correct each pattern.

- **≥5 occurrences = repeat.** A note will not fix it — it has already been written down and
  the mistake happened anyway. It needs a preflight, a hook, or a permission.
- **1–4 = one-off.** A criterion or memory entry is proportionate.

Treating every mistake as equally weighted is the main failure mode of this kind of system:
the file grows, nothing is enforced, and the frequent errors keep happening.

Then place it on this ladder and push it **as far down as it will go**:

| level | requires attention? | example |
| --- | --- | --- |
| memory / note | entirely | a memory file |
| CLAUDE.md rule | mostly | SEND-DISABLED |
| runbook doc | mostly | a precheck section nobody reads under pressure |
| script encoding the safe path | only to invoke it | `deploy_app.sh` |
| preflight assertion inside it | no | abort before the destructive step |
| test in CI | no | `check_design_refs.py` |
| permission / IAM | cannot happen | deny the API, force terraform |

Principle, from the a client repo: **人の注意力ではなく、機械で担保する。**

A note is the weakest possible response and should be the last resort. If the lesson can be a
preflight check or a test, write the check — do not write a reminder to be careful.

Ask explicitly:
- What would have caught this **within seconds** rather than when the user noticed?
- Did I verify *the change* but not *the operation itself*? (Deploys, migrations, and
  bulk edits can break things unrelated to what you changed.)
- Is the gate in the repo, where it binds everyone — or only in my memory, where it binds no one?

## 3. Writing / presentation review

Re-read the day's user-facing output — replies, Slack drafts, PR bodies, the 日報 — against
`references/writing-criteria.md`. Add a criterion whenever the user reacts to *how* something was
said rather than what it said ("give clear indication", "reader's perspective", "too long").

## 4. Weekly — prune, and check the checks

Once a week (or when the memory list feels long):

```
python3 ~/.claude/skills/daily-retro/scripts/mistake-frequency.py --stale
```

Read the bottom third and decide: retire, or move into the relevant repo. Note the metric is
relative and confounded by recency — newly written memories rank low simply for being new.
Never auto-delete on it.

Also confirm the gates still fire:

```
python3 ~/.claude/skills/daily-retro/scripts/verify-gates.py
```

It feeds each hook input that *should* trip it and input that shouldn't, and exits non-zero if
any gate has gone quiet. **A check that has never failed and cannot be made to fail is not
protecting anything** — three staleness detectors passed all 18 memories before I noticed the
metric was meaningless. When adding a gate, break it on purpose once and confirm the alarm.

## 5. Update

- New durable fact about the user or a standing instruction → a memory file, plus a line in
  `MEMORY.md`.
- New recurring procedure → a skill, or a section in this one.
- New writing lesson → `references/writing-criteria.md`.
- New engineering gate → a script/test **in the relevant repo**, not here.

Then state in the reply what was added, in one or two lines. Do not narrate the whole loop.
