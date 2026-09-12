# agent-guardrails

**English** · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Bahasa Melayu](README.ms.md) · [ไทย](README.th.md)

Guardrail hooks for Claude Code. Stops repeated mistakes **mechanically**, instead of
writing yet another note asking the agent to be careful.

> Guarantee it with machinery, not with human attention.

## Why

I measured 30 sessions — 887 user messages. The user had to correct me **44 times**,
and the corrections collapsed into 6 patterns. Every single one was defended only by
**prose in a notes file**. The note was already written. The mistake happened anyway.

| Measured | Pattern | Defence now |
| --- | --- | --- |
| 12 | Writing quality | `reply_check.py` detects |
| 9 | Claiming done too early | `reply_check.py` detects |
| 9 | Shipping work nobody asked for | `outward_action_guard.py` **refuses** |
| 7 | Saying "can't" without trying | `reply_check.py` detects |
| 4 | Missing an instruction | criteria file (below threshold) |
| 3 | Wrong target repo/env | criteria file (below threshold) |

The adoption rule: **≥5 occurrences means it is recurring, which means a note will not
fix it** — the note already failed. Below 5 stays prose. Gate everything and the warnings
saturate until nobody reads them.

## What's here

### Hooks (registered in `~/.claude/settings.json`, active everywhere)

| File | Event | What it does |
| --- | --- | --- |
| `reply_check.py` | Stop | Flags a missing status block, unevidenced completion claims, untested "can't", model-tells (`X, not Y` contrast, counted-inventory openers, cleft openers, throat-clearing), and chatbot leakage. **Warn only** — blocking on Stop risks a loop |
| `outward_action_guard.py` | PreToolUse(Bash) | **Refuses** hard-to-undo outward actions (PR/push/repo/release/gist). Also refuses `<check> \| tail; echo $?` — that reads *tail's* exit code, not the check's |
| `guard_the_guards.py` | PreToolUse(Edit/Write) | Asks before editing a checker, hook, settings file, or memory. Stops the agent rewriting the judge instead of fixing the product |
| `daily-retro-reminder.sh` | PostToolUse | Prompts the retrospective when a daily report is written |

### Skill

`skills/daily-retro/` — an improvement loop triggered by writing the daily report.
Pushes each mistake as far **down** this ladder as it will go:

> memory → doc → script → preflight → test → permission

### Scripts

| File | Purpose |
| --- | --- |
| `mistake-frequency.py` | **Counts** correction patterns across all past sessions, so "I fixed that already" is measured rather than felt |
| `verify-gates.py` | **Self-test for the gates.** Feeds each hook input that must trip it and input that must not |

### Reference

`reference/anti-self-deception/` — 24 rules, 15 scripts and 29 standing checks from
another team's mature system, included with permission and anonymised.
See its `ATTRIBUTION.md`.

## The two that mattered most

**`guard_the_guards.py`.** Every other defence watched *products*. Nothing stopped the
audited party from rewriting the judge. I had just built three hooks and a self-test —
and could freely edit all of them to silence a failure.

**`verify-gates.py`.** I wrote a staleness detector three times and it passed all 18
memories every time. Without reading the numbers I would have reported "healthy" three
times over. **A check that has never failed may be protecting nothing.**

## Install

Clone, then `bash install.sh`. It copies into `~/.claude/hooks/` and `~/.claude/skills/`
and registers the hooks in `~/.claude/settings.json` — appending only, existing settings
preserved.

Read `CLAUDE.example.md`, adapt it to your machine (memory path, daily-report location),
then place it at `~/.claude/CLAUDE.md`.

Then always run the self-test:

    python3 ~/.claude/skills/daily-retro/scripts/verify-gates.py

Tested at 21/21 on a fresh machine and 26/26 on a configured one.

## Notes

- Hooks live in `~/.claude/`, so they apply **in every directory**. Memory does not —
  it is keyed by the directory Claude starts in, so cross-project principles belong in
  `~/.claude/CLAUDE.md`, which is loaded every session.
- `outward_action_guard.py` blocks pushes. Intentional ones set `CLAUDE_OUTWARD_OK=1`.
  Too noisy? Remove entries from `GUARDED`.
- `reply_check.py` is regex-based and will produce false positives. When it does,
  **narrow the pattern — don't delete the check.**
- Hook messages are currently Japanese. Runtime output is read by the agent, so this
  does not affect behaviour, but a translation is welcome.

## Licence

MIT
