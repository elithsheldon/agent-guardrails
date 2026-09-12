#!/usr/bin/env python3
"""Deadline gate for the goals cron (goal: deadlines).

Single source of truth: ~/ObsidianVault/_meta/TODO.md
This script only READS the vault; all edits to TODO.md happen in sessions.

Parsed line shapes (anywhere in the file):

  - [ ] 2026-08-10 (lead 7) UAI poster PDF due (AoE)     open dated item
  - [x] 2026-08-10 (lead 7) ...                          done -> ignored
  - monthly-end (lead 3) RIKEN monthly timesheet #riken-timesheet
        recurring item; satisfied for the current month iff a checked line
        "- [x] <this month's last day> ... #riken-timesheet" exists.
        Outside the lead window it is silently OK.

FAIL (exit 1) iff any open dated item is due within its lead window (or past
due), or a recurring item's current instance is inside its window and has no
checked instance line. The report names each offender and the exact fix line.

Dates are evaluated in JST (UTC+9, no DST), so reminders trip early, which is
the safe direction. Items whose text carries an "(AoE)" marker get their
PAST DUE label computed against the UTC-12 calendar instead: the reminder
still fires on the JST schedule, but the label never claims "past due" while
the AoE day is still running (a false "no refunds, too late" label invites
giving up on a window that is in fact still open).

--selftest runs synthetic cases and must stay green after any edit.

QUIET HORIZON MODE (--horizon N [--at YYYY-MM-DD], added 2026-08-11 for the
biweekly paper-batch proposer): prints one line and exits 1 iff an open
MANUSCRIPT SUBMISSION deadline falls within N days. This is a blackout gate,
not a reminder, so it is deliberately much narrower than the checks above:
only "<venue> abstract/full paper/camera-ready deadline" shapes count.
Candidate gates, rehearsals, pre/post-submission chores, CFP re-checks and the
monthly timesheet must NOT trip it -- a gate every fortnight would blackout the
proposer forever. The classifier reads only the head of the description (up to
the first em dash), because the tail carries verification prose that mentions
"CFP" and "deadline" for items that are not submissions.
"""

import re
import sys
import calendar
from datetime import datetime, timedelta, timezone
from pathlib import Path

TODO_PATH = Path.home() / "ObsidianVault" / "_meta" / "TODO.md"

DATED_RE = re.compile(
    r"^\s*-\s*\[(?P<done>[ xX])\]\s*(?P<date>\d{4}-\d{2}-\d{2})"
    r"\s*\(lead\s*(?P<lead>\d+)\)\s*(?P<text>.+?)\s*$"
)
RECUR_RE = re.compile(
    r"^\s*-\s*monthly-end\s*\(lead\s*(?P<lead>\d+)\)\s*(?P<text>.+?)"
    r"\s*(?P<tag>#[\w-]+)\s*$"
)


def today_jst() -> "datetime.date":
    return (datetime.now(timezone.utc) + timedelta(hours=9)).date()


def today_aoe() -> "datetime.date":
    return (datetime.now(timezone.utc) - timedelta(hours=12)).date()


AOE_RE = re.compile(r"\(AoE\)", re.IGNORECASE)


def month_end(d) -> "datetime.date":
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


PRIO_RE = re.compile(r"\s*#p([123])\b")


def split_prio(text: str):
    """Return (priority 1..3, text with the #pN tag stripped). Default 2."""
    m = PRIO_RE.search(text)
    if not m:
        return 2, text
    return int(m.group(1)), PRIO_RE.sub("", text).strip()


def check(text: str, today, today_utc12=None) -> list:
    """Return list of violation strings (empty = PASS), P1 first then by date.

    today_utc12: current date on the UTC-12 (AoE) calendar; only used to label
    "(AoE)" items. Defaults to `today`, which reproduces the old behavior.
    """
    if today_utc12 is None:
        today_utc12 = today
    violations = []  # (priority, date, message)
    checked_lines = []  # (date, rest-of-line) of all [x] lines, for recurring ack lookup
    for line in text.splitlines():
        m = DATED_RE.match(line)
        if m:
            date = datetime.strptime(m.group("date"), "%Y-%m-%d").date()
            if m.group("done").strip():
                checked_lines.append((date, m.group("text")))
                continue
            days_left = (date - today).days
            if days_left <= int(m.group("lead")):
                # Reminder cadence is JST; the PAST DUE label for AoE items
                # follows the AoE calendar so it never lies about a live window.
                label_days = (
                    (date - today_utc12).days
                    if AOE_RE.search(m.group("text")) else days_left
                )
                tag = "PAST DUE" if label_days < 0 else f"due in {label_days}d"
                prio, clean = split_prio(m.group("text"))
                violations.append(
                    (prio, date, f"[P{prio}, {tag}] {m.group('date')} {clean}")
                )
            continue
        # also collect checked lines that carry a date but no (lead N)
        m2 = re.match(r"^\s*-\s*\[[xX]\]\s*(\d{4}-\d{2}-\d{2})\s*(.*)$", line)
        if m2:
            checked_lines.append(
                (datetime.strptime(m2.group(1), "%Y-%m-%d").date(), m2.group(2))
            )

    for line in text.splitlines():
        m = RECUR_RE.match(line)
        if not m:
            continue
        due = month_end(today)
        days_left = (due - today).days
        if days_left > int(m.group("lead")):
            continue
        tag = m.group("tag")
        acked = any(d == due and tag in rest for d, rest in checked_lines)
        if not acked:
            prio, clean = split_prio(m.group("text"))
            violations.append(
                (prio, due,
                 f"[P{prio}, recurring, due in {days_left}d] {due} {clean} {tag} "
                 f"-- ack by adding: - [x] {due} {m.group('text')} {tag}")
            )
    violations.sort(key=lambda v: (v[0], v[1]))
    return [msg for _, _, msg in violations]


# --- quiet horizon mode (blackout gate) --------------------------------------

SUBMISSION_RE = re.compile(
    r"(abstract|full[-\s]paper|paper|camera[-\s]ready|supplementary|submission)"
    r"\s+deadline",
    re.IGNORECASE,
)
NOT_SUBMISSION_RE = re.compile(
    r"pre-submission|post-submission|rehearsal|\bgate\b|\bconfirm\b|re-check|"
    r"check whether|\bCFP\b|\bprep\b|timesheet|\bexpected\b|\bpromote\b",
    re.IGNORECASE,
)


def is_submission(text: str) -> bool:
    """True iff this dated item is a manuscript submission deadline.

    Only the head (before the first em dash) is classified; the tail is
    provenance prose that routinely names other people's deadlines.
    """
    head = text.split("—")[0]
    return bool(SUBMISSION_RE.search(head)) and not NOT_SUBMISSION_RE.search(head)


def submissions_within(text: str, today, days: int) -> list:
    """Open manuscript submissions due in [0, days]. Empty list = not blacked out.

    Past-due submissions do not blackout: the window has closed, so waiting
    on it would stall the caller forever.
    """
    hits = []
    for line in text.splitlines():
        m = DATED_RE.match(line)
        if not m or m.group("done").strip():
            continue
        if not is_submission(m.group("text")):
            continue
        date = datetime.strptime(m.group("date"), "%Y-%m-%d").date()
        left = (date - today).days
        if 0 <= left <= days:
            _, clean = split_prio(m.group("text"))
            hits.append((date, left, clean.split("—")[0].strip()))
    hits.sort()
    return hits


def selftest() -> int:
    from datetime import date

    today = date(2026, 7, 29)
    cases = [
        # (name, content, expect_fail)
        ("far future passes", "- [ ] 2026-09-16 (lead 7) ICLR full paper", False),
        ("inside lead fails", "- [ ] 2026-08-02 (lead 7) UAI thing", True),
        ("checked inside lead passes", "- [x] 2026-08-02 (lead 7) UAI thing", False),
        ("past due fails", "- [ ] 2026-07-01 (lead 3) old item", True),
        (
            "recurring in window unacked fails",
            "- monthly-end (lead 3) RIKEN monthly timesheet #riken-timesheet",
            True,
        ),
        (
            "recurring acked passes",
            "- monthly-end (lead 3) RIKEN monthly timesheet #riken-timesheet\n"
            "- [x] 2026-07-31 RIKEN monthly timesheet #riken-timesheet",
            False,
        ),
        (
            "recurring ack for WRONG month still fails",
            "- monthly-end (lead 3) RIKEN monthly timesheet #riken-timesheet\n"
            "- [x] 2026-06-30 RIKEN monthly timesheet #riken-timesheet",
            True,
        ),
        (
            "recurring outside window passes",
            "- monthly-end (lead 3) RIKEN monthly timesheet #riken-timesheet",
            False,
        ),
        ("non-todo prose ignored", "some prose with a date 2026-07-30 in it", False),
        ("priority tag still parses", "- [ ] 2026-07-30 (lead 3) urgent thing #p1", True),
    ]
    failures = 0
    for name, content, expect_fail in cases:
        t = date(2026, 7, 20) if name == "recurring outside window passes" else today
        got_fail = bool(check(content, t))
        ok = got_fail == expect_fail
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        failures += 0 if ok else 1

    # ordering: P1 outranks an earlier-dated P3; #pN tag is stripped from output
    v = check(
        "- [ ] 2026-07-01 (lead 3) low thing #p3\n"
        "- [ ] 2026-07-28 (lead 3) big thing #p1",
        today,
    )
    ok = (len(v) == 2 and "big thing" in v[0] and v[0].startswith("[P1")
          and "#p" not in v[0] + v[1])
    print(f"{'PASS' if ok else 'FAIL'}  P1 sorts first and tags stripped")
    failures += 0 if ok else 1

    # AoE labeling: JST is already past the date but the AoE day still runs ->
    # the reminder fires, yet the label must NOT say PAST DUE.
    aoe_today, aoe_utc12 = date(2026, 7, 29), date(2026, 7, 28)
    v = check("- [ ] 2026-07-28 (lead 7) register (AoE) #p1", aoe_today, aoe_utc12)
    ok = len(v) == 1 and "PAST DUE" not in v[0] and "due in 0d" in v[0]
    print(f"{'PASS' if ok else 'FAIL'}  AoE window still open is not PAST DUE")
    failures += 0 if ok else 1

    # Truly past on the AoE calendar -> PAST DUE as before.
    v = check("- [ ] 2026-07-27 (lead 7) register (AoE) #p1", aoe_today, aoe_utc12)
    ok = len(v) == 1 and "PAST DUE" in v[0]
    print(f"{'PASS' if ok else 'FAIL'}  AoE truly past is PAST DUE")
    failures += 0 if ok else 1

    # Non-AoE items ignore the AoE calendar argument entirely.
    v = check("- [ ] 2026-07-28 (lead 7) register plain", aoe_today, aoe_utc12)
    ok = len(v) == 1 and "PAST DUE" in v[0]
    print(f"{'PASS' if ok else 'FAIL'}  non-AoE keeps JST past-due label")
    failures += 0 if ok else 1

    # horizon mode: only manuscript submissions blackout, and only ahead of time
    hcases = [
        ("submission inside horizon blacks out",
         "- [ ] 2026-09-18 (lead 14) <venue> abstract deadline (AoE) — re-verified "
         "on the official CFP+AuthorGuidelines #p1", date(2026, 8, 28), True),
        ("submission outside horizon is clear",
         "- [ ] 2026-09-18 (lead 14) <venue> abstract deadline (AoE) #p1",
         date(2026, 8, 17), False),
        ("past-due submission does not blackout",
         "- [ ] 2026-09-25 (lead 7) <venue> full paper deadline (AoE) #p1",
         date(2026, 9, 28), False),
        ("checked submission does not blackout",
         "- [x] 2026-09-18 (lead 14) <venue> abstract deadline (AoE) #p1",
         date(2026, 9, 10), False),
        ("candidate gate does not blackout",
         "- [ ] 2026-08-22 (lead 2) Candidate J P2 exit: cross-env decline at "
         "5-seed confidence #p1", date(2026, 8, 17), False),
        ("submission rehearsal does not blackout",
         "- [ ] 2026-09-05 (lead 3) ICLR full-pipeline submission REHEARSAL — "
         "burn the first time two weeks before the 09-25 deadline #p1",
         date(2026, 8, 28), False),
        ("pre-submission chore does not blackout",
         "- [ ] 2026-09-15 (lead 4) AQRL pre-submission neighbor re-scan + bib "
         "refresh: cite into Related Work before the abstract deadline #p2",
         date(2026, 8, 28), False),
        ("CFP re-check does not blackout",
         "- [ ] 2026-09-15 (lead 5) Re-check AISTATS 2027 + AAMAS 2027 CFPs — "
         "deadlines expected Oct 2026 #p3", date(2026, 8, 28), False),
        ("timesheet submission does not blackout",
         "- [ ] 2026-08-31 (lead 3) RIKEN monthly timesheet submission deadline "
         "#p1", date(2026, 8, 17), False),
        ("poster session does not blackout",
         "- [ ] 2026-08-19 (lead 2) UAI virtual poster session — Gather.Town #p1",
         date(2026, 8, 10), False),
    ]
    for name, content, t, expect_black in hcases:
        got = bool(submissions_within(content, t, 21))
        ok = got == expect_black
        print(f"{'PASS' if ok else 'FAIL'}  horizon: {name}")
        failures += 0 if ok else 1

    total = len(cases) + 4 + len(hcases)
    print(f"selftest: {total - failures}/{total} passed")
    return 1 if failures else 0


def horizon_main(argv) -> int:
    """--horizon N [--at YYYY-MM-DD]: one line, exit 1 iff blacked out."""
    days = int(argv[argv.index("--horizon") + 1])
    when = (datetime.strptime(argv[argv.index("--at") + 1], "%Y-%m-%d").date()
            if "--at" in argv else today_jst())
    if not TODO_PATH.exists():
        print(f"FAIL: {TODO_PATH} missing")
        return 1
    hits = submissions_within(TODO_PATH.read_text(encoding="utf-8"), when, days)
    if hits:
        d, left, what = hits[0]
        print(f"BLACKOUT {when}: submission within {days}d — {d} ({left}d) {what}")
        return 1
    print(f"clear {when}: no submission within {days}d")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    if "--horizon" in sys.argv:
        return horizon_main(sys.argv)
    if not TODO_PATH.exists():
        print(f"FAIL: {TODO_PATH} missing")
        return 1
    violations = check(TODO_PATH.read_text(encoding="utf-8"), today_jst(), today_aoe())
    if violations:
        print(f"DEADLINES ({len(violations)} open, JST {today_jst()}):")
        for v in violations:
            print(f"  {v}")
        print(f"Single source: {TODO_PATH} (check items off there)")
        return 1
    print(f"deadlines: all clear (JST {today_jst()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
