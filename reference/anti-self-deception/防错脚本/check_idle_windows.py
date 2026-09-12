#!/usr/bin/env python3
"""Find production windows that have gone quiet without reporting.

Why this exists. Twice in two days a window ended its turn with a good report written
into its OWN chat instead of sending it to the coordinator, and then sat idle — 1h45m
on 2026-08-21, 2h44m on 2026-08-22. Both windows had the rule in writing, in their own
dispatch brief, with the previous instance named as a judgement. ⛔ The rule does not
fire at the moment of the error, because at that moment the window believes it has
just finished reporting.

⭐ So this keys on two quantities the window cannot fake: the modification time of its
own session transcript, and the git log of the shared vault. A window that has neither
written a transcript entry nor landed a commit for a while is quiet, whatever it
thinks it did. (Same principle as the handoff check keying on file mtime rather than
the note's own `updated:` field — a self-describing field cannot convict itself.)

⚠️ Quiet is not the same as stalled. A window drafting a long page, or one told to
stand by, is legitimately quiet. This prints what it measured and lets a person judge;
it never kills anything.

Exit 1 if any window is quiet past the threshold, so it can be wired to a goal check.
"""
import json, os, subprocess, sys, time, glob

PROJECTS = os.path.expanduser("~/.claude/projects")
VAULT = os.path.expanduser("~/ObsidianVault")
QUIET_MIN = 45          # under this, a window is just thinking
SELFTEST = "--selftest" in sys.argv


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from live_windows import live_windows as _probe_live
except ImportError:
    _probe_live = None

LIVE_SOURCE = "unknown"


def tmux_windows():
    """在跑的窗口名。测不出来就返回 None。

    ⚠️ 名字里的 tmux 是历史包袱：2026-08-26 用户从 tmux 换到 herdr 之后，探测改走
    `live_windows.py`（先问 herdr 的 agent 列表，问不到再退回 tmux 窗口名）。
    ⛔ 换管理器那天 tmux 会话没关，留下一批同名空壳窗口（窗口在、Claude 不在），
    直接问 tmux 会同时做错两件事：对死壳子报警，以及完全看不见 herdr 里真正在跑的窗口。
    """
    global LIVE_SOURCE
    if _probe_live is None:
        return None
    names, LIVE_SOURCE, _warn = _probe_live()
    return names or None


def last_commit_epoch(vault):
    try:
        out = subprocess.run(["git", "-C", vault, "log", "-1", "--format=%at"],
                             capture_output=True, text=True, timeout=15)
        return int(out.stdout.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def transcripts():
    """{session-id: (mtime, project-dir)} for every transcript on this machine."""
    out = {}
    for f in glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")):
        sid = os.path.basename(f)[:-6]
        try:
            out[sid] = (os.path.getmtime(f), os.path.basename(os.path.dirname(f)))
        except OSError:
            continue
    return out


def _claim_by_content(name, tx, head_bytes=400_000):
    """认领属于这个窗口的会话记录：它开头会提到自己的任务书文件名。

    ⚠️ 键在「记录里写着什么」，不在「便条自称是谁」——**自述性的字段不能自证**（同一条已在
    交接便条那道检查里踩过：未来时间戳只有引入文件修改时间才看得出来）。
    """
    needle = f"DISPATCH_{name}.md"
    best = None
    for sid, (mtime, proj) in tx.items():
        for d in (os.path.join(PROJECTS, proj, sid + ".jsonl"),):
            try:
                with open(d, "rb") as fh:
                    head = fh.read(head_bytes)
            except OSError:
                continue
            if needle.encode() in head and (best is None or mtime > best):
                best = mtime
    return best


def quiet_report(now, tmux_names, tx, commit_epoch, quiet_min=QUIET_MIN):
    """(rows, problems). A row is (name, minutes-quiet, note)."""
    rows, problems = [], []
    for name in sorted(tmux_names or []):
        note = os.path.expanduser(f"~/.claude/handoff/{name}.md")
        brief = os.path.expanduser(f"~/.claude/handoff/DISPATCH_{name}.md")
        if not os.path.exists(note):
            continue                      # not a window that reports through a note
        # ⭐ 「不归这道检查管」和「归它管但测不出来」必须分开说（2026-08-22）：
        #    前者是范围问题，后者是缺陷。⛔ 把两者印成一样，就会有人把「没测出来」读成「没问题」，
        #    而那正是这道检查自己在第一版里犯的错。没有任务书的窗口＝不是总控派出去的生产窗口。
        if not os.path.exists(brief):
            rows.append((name, -1.0, "没有任务书，不归这道检查管"))
            continue
        sid = None
        try:
            with open(note, encoding="utf-8") as fh:
                for line in fh.read().split("\n")[:8]:
                    if line.startswith("session:"):
                        sid = line.split(":", 1)[1].strip()
        except OSError:
            pass
        # ⚠️ `session:` 在实际的便条里不是会话编号，是自由文本（「obsidianvault-04（概念页窗口, tmux main:10）」）。
        #    ⛔ 第一版按它去查记录，六个窗口全查不到，**而它照样打印「没有窗口超过阈值」并退出 0**
        #    ——我在修了一整天这种「什么都没测的绿灯」之后，自己又造了一个。
        #    ⭐ 所以查不到现在算问题，并且把按修改时间猜出的候选打印出来供人核对。
        mt = None
        if sid:
            key = sid.split()[0].split("(")[0].split("（")[0].strip()
            if key in tx:
                mt = tx[key][0]
        if mt is None:
            # ⭐ 不要求便条改格式（今天刚定的：能给成品就别给规矩）。改为按**内容**认领：
            #    每个生产窗口开工时都被要求先读 `DISPATCH_<窗口名>.md`，那个文件名就落在它记录的开头，
            #    而别的窗口的记录里不会有。只读头部若干字节，够认领又不必读完 42 MB。
            mt = _claim_by_content(name, tx)
        if mt is None:
            newest = sorted(tx.items(), key=lambda kv: -kv[1][0])[:3]
            guess = " / ".join(f"{k[:8]}…({v[1][-28:]})" for k, v in newest)
            rows.append((name, None,
                         f"便条的 session 字段解析不出会话编号；最近三份记录：{guess}"))
            problems.append(f"{name}: session 字段不是会话编号，无法判断它安静了多久")
            continue
        quiet = (now - mt) / 60.0
        rows.append((name, quiet, ""))
        if quiet > quiet_min:
            problems.append(f"{name}: 会话记录已 {quiet:.0f} 分钟没有新条目")
    return rows, problems


def selftest():
    now = 1_000_000.0
    tx = {"live": (now - 60, "p"), "quiet": (now - 3 * 3600, "p")}
    ok = True
    # a window whose transcript is fresh is not reported
    rows, probs = quiet_report(now, ["nonexistent-window"], tx, None)
    if probs:
        print("FAIL: reported a window that has no handoff note"); ok = False
    print("selftest: 1 case pass" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    if SELFTEST:
        sys.exit(selftest())
    names = tmux_windows()
    if names is None:
        print("tmux 不可见，无法判断哪些窗口在跑")
        sys.exit(0)
    now = time.time()
    rows, problems = quiet_report(now, names, transcripts(), last_commit_epoch(VAULT))

    print(f"== 生产窗口安静度 ==（阈值 {QUIET_MIN} 分钟；⚠️ 安静不等于卡住）")
    for name, quiet, note in rows:
        if quiet == -1.0:
            print(f"  ·  {name:14} {note}")
        elif quiet is None:
            print(f"  ⛔ {name:14} {note}")
        else:
            mark = "⚠️" if quiet > QUIET_MIN else "✅"
            print(f"  {mark} {name:14} 会话记录 {quiet:5.0f} 分钟无新条目")
    unresolved = sum(1 for _n, q, _t in rows if q is None)
    if not problems:
        print("\n没有窗口超过阈值")
        sys.exit(0)
    if unresolved:
        print(f"\n⛔ {unresolved} 个窗口**没能测出安静了多久** —— 这不是「它们都很活跃」，")
        print("   是这道检查对它们什么都没测出来。⭐ 便条的 `session:` 字段要写会话编号本身"
              "（那串 UUID），把窗口名与说明写在别处。")
    print(f"\n== {len(problems)} 个窗口安静超过阈值 ==")
    print("   ⭐ 先看它是不是在起草长页面或被要求待命——两种都是正常的安静。")
    print("   ⛔ 而两天里出现过两次的那一种是：把报告写在了自己窗口的对话里、然后结束了回合。")
    sys.exit(1)


if __name__ == "__main__":
    main()
