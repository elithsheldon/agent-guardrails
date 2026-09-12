#!/usr/bin/env python3
"""定时任务里跑 headless claude 的那些，有没有在静默失败。

## 为什么有这个（2026-08-28）

`~/wild/_meta/daily_scout.sh` 每天粗筛 arXiv 决定要不要叫醒 wild 那条线。
它这样写：

    claude -p --model haiku >"$VERDICT"          # ⛔ 不看退出码
    head -1 "$VERDICT" | grep -q WAKE && WAKE=1 || WAKE=0

⛔ 于是「筛选失败」与「筛过了，今天没东西」**完全同形**，不留任何痕迹。
⚠️ 而它当时正在发生：08-27 与 08-28 的产物都是 **0 字节**，日志里写着
`claude: command not found`（cron 的 PATH 只有 /usr/bin:/bin，而 claude 装在
~/.local/bin），两天都被判成「今天没东西」，没有任何地方报错。
连坏两天，是撞上一次人工排查才被看见的。

## 这道检查测什么

两件，都键在**脚本作者控制不了的量**上（磁盘上的产物与日志），不读任何自述字段：

1. **产物是不是空的。** 每个受管任务声明一个产物路径模式（按日期展开），
   ⭐ 判据是「昨天/今天这一份存在但为 0 字节」—— 那正是静默失败的形状。
   ⚠️ 文件**不存在**不算失败：那天可能压根没到运行时刻，或任务被停用了。
2. **日志里有没有 `command not found` / `No such file`。** 这一条抓的是 PATH 问题，
   它会在产物变空之前就出现，且指名道姓说缺什么。

## ⛔ 它故意不测什么

- **不测「那天该不该叫醒」** —— 那要重跑一遍粗筛，成本与判断都不属于一道检查。
  它只回答「这次运行有没有产出东西」。
- **不替任何脚本修 PATH。** 报出来，交给拥有那个脚本的窗口改；
  `~/wild` 与知识库的脚本各有其主。

## 加新任务怎么加

往 JOBS 里加一条，四个字段：名字、产物路径模式（`{d}` 会被换成 YYYYMMDD）、
日志路径模式、以及一句「它是干什么的」。⚠️ 产物模式指不到真实文件时，
本检查会**明说自己没测到**，而不是默默跳过 —— 一个测不到东西的检查最爱伪装成绿灯。

## 单独跑

    python3 ~/.claude/scripts/check_cron_agent_jobs.py
    python3 ~/.claude/scripts/check_cron_agent_jobs.py --selftest
"""
import datetime
import glob
import os
import re
import sys

HOME = os.path.expanduser("~")

# 受管的定时任务。⚠️ 只列**产物形状固定、能机械判空**的那些；
# 产物是自由文本、判不出「空 vs 有内容」的任务不要硬塞进来。
JOBS = [
    {
        "name": "wild 每日 arXiv 粗筛",
        "artifact": f"{HOME}/wild/_meta/scout_log/verdict_{{d}}.txt",
        "log": f"{HOME}/wild/_meta/scout_log/scout_{{d}}.log",
        "what": "决定要不要叫醒 wild 那条线；空产物会被判成「今天没东西」",
    },
    {
        "name": "知识库每晚研究日志",
        "artifact": f"{HOME}/ObsidianVault/daily/{{iso}}.md",
        "log": f"{HOME}/ObsidianVault/_meta/logs/daily.log",
        "what": "每晚写当天的研究日志并提交",
    },
]

BAD_LOG_PATTERNS = [
    (r"command not found", "有命令找不到 —— 多半是 cron 的 PATH 里没有它"),
    (r"No such file or directory", "有路径不存在"),
    (r"Reached max turns", "回合数用尽 —— ⚠️ headless claude 这时仍返回 0，"
                           "所以外层 `if claude …; then` 会把它当成功"),
]


def days(n=2):
    """今天与昨天。⭐ 只看这两天：再往前的失败已经无法补救，报出来只是噪声。"""
    t = datetime.date.today()
    return [t - datetime.timedelta(days=i) for i in range(n)]


def check_job(job, day_list=None):
    """返回 (problems, notes)。⛔ 测不到东西时进 notes 并明说，不算通过。"""
    problems, notes = [], []
    found_any = False
    for d in (day_list or days()):
        art = job["artifact"].format(d=d.strftime("%Y%m%d"), iso=d.isoformat())
        if not os.path.exists(art):
            continue
        found_any = True
        try:
            size = os.path.getsize(art)
        except OSError:
            continue
        if size == 0:
            problems.append(
                f"{job['name']}: {d.isoformat()} 的产物是 0 字节 —— "
                f"{job['what']}｜{art.replace(HOME, '~')}")
    if not found_any:
        notes.append(f"{job['name']}: 最近两天都没有产物文件，"
                     f"⚠️ 本检查对它什么都没测到（可能没到运行时刻，或任务已停）")

    # 日志里的硬错误。
    # ⛔ 两个坑，都是装上第一次跑就现形的（2026-08-28 当场修）：
    #  ① **同一个日志文件被扫两遍**（今天一次、昨天一次），于是同一条错误报两次。
    #     日志路径里不含 {d} 时，两天展开出的是同一个路径 —— 先去重再扫。
    #  ② **累积型日志会翻出陈年旧账**：知识库那份 daily.log 是一直追加的，
    #     只读尾部仍读到 8-20 那条早已修好的记录，于是一条已经解决的问题天天报红。
    #     ⭐ 判据改成「这条错误出现在最近两天的日期戳之后吗」：日志行里带日期就按日期筛，
    #     筛不出日期的（比如每天新建的那种日志）才退回「文件修改时间在最近两天内」。
    #  ⚠️ 一条会报重复、又会报陈年旧账的检查，两周内就会被当噪声忽略 —— 那时它连真问题
    #     也拦不住了。这与「天天无故变红的检查等于没有」是同一件事。
    recent = {d.isoformat() for d in (day_list or days())}
    recent |= {d.strftime("%Y-%m-%d %H") [:10] for d in (day_list or days())}
    seen_logs = set()
    seen_kinds = {}
    for d in (day_list or days()):
        log = job["log"].format(d=d.strftime("%Y%m%d"), iso=d.isoformat())
        if log in seen_logs or not os.path.exists(log):
            continue
        seen_logs.add(log)
        # 文件本身很久没动过 = 它记的都是旧事，整份跳过
        try:
            mtime = datetime.date.fromtimestamp(os.path.getmtime(log))
        except OSError:
            continue
        if mtime < min(day_list or days()):
            continue
        try:
            with open(log, encoding="utf-8", errors="replace") as fh:
                fh.seek(0, os.SEEK_END)
                back = min(fh.tell(), 8000)
                fh.seek(fh.tell() - back)
                tail = fh.read()
        except OSError:
            continue
        for pat, why in BAD_LOG_PATTERNS:
            hit = None
            for line in tail.splitlines():
                if not re.search(pat, line):
                    continue
                dates = re.findall(r"\d{4}-\d{2}-\d{2}", line)
                if dates and not (set(dates) & recent):
                    continue        # 行里写着日期，而那是旧事
                hit = line.strip()
                break
            if hit:
                # ⭐ 按「哪一类错误」去重，而不是按「哪个日志文件」（2026-08-28 二次修）。
                #    每日新建的日志下，连续两天同一个毛病是两个文件各一条 —— 那确实是
                #    两次失败，不是重复报；但读的人要的是「这个毛病还在」而不是数它犯了几次。
                #    ⚠️ 所以合并成一条并把天数带上：信息不丢，噪声减半。
                key = (job["name"], pat)
                if key in seen_kinds:
                    seen_kinds[key][1] += 1
                else:
                    seen_kinds[key] = [
                        f"{job['name']}: 日志里出现「{re.search(pat, hit).group(0)}」"
                        f"—— {why}\n       {hit[:150]}", 1]
                break

    for (_n, _p), (msg, cnt) in seen_kinds.items():
        problems.append(msg + (f"\n       ⚠️ 最近两天里出现了 {cnt} 天" if cnt > 1 else ""))
    return problems, notes


def main(argv):
    if "--selftest" in argv:
        return selftest()
    all_problems, all_notes = [], []
    print("== 定时任务里的 headless agent 调用 ==")
    for job in JOBS:
        probs, notes = check_job(job)
        all_problems += probs
        all_notes += notes
        mark = "⛔" if probs else ("·" if notes else "✅")
        print(f"  {mark} {job['name']}")
    for n in all_notes:
        print(f"  ⚠️ {n}")
    if not all_problems:
        print("\n== CRON AGENT JOBS: CLEAN ==")
        return 0
    print(f"\n== CRON AGENT JOBS: {len(all_problems)} 处问题 ==")
    for p in all_problems:
        print(f"  ⛔ {p}")
    print("\n   ⭐ 这一族的形状是**失败被表达成了成功** —— headless claude 跑不完也返回 0，")
    print("      所以 `if claude …; then <往下走>` 读到的是「成功」。")
    print("   修法两层：① 脚本自己验产物（非空、形状对）；② 验不过时**响亮地失败**，")
    print("      ⛔ 别退回一个看起来安全的默认值（判不出来时宁可叫醒人，别判成「没事」）。")
    return 1


def selftest():
    """反向验证：空产物要报红，正常产物不报，产物不存在要明说没测到。"""
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    ok = True
    d = datetime.date.today()
    ds = d.strftime("%Y%m%d")

    def job(art_size=None, log_text=None):
        art = os.path.join(tmp, f"v_{ds}.txt")
        log = os.path.join(tmp, f"l_{ds}.log")
        for f in (art, log):
            if os.path.exists(f):
                os.remove(f)
        if art_size is not None:
            with open(art, "w") as fh:
                fh.write("x" * art_size)
        if log_text is not None:
            with open(log, "w") as fh:
                fh.write(log_text)
        return {"name": "t", "artifact": os.path.join(tmp, "v_{d}.txt"),
                "log": os.path.join(tmp, "l_{d}.log"), "what": "w"}

    def case(label, j, want_problems, want_notes):
        nonlocal ok
        probs, notes = check_job(j, [d])
        got = (len(probs) > 0, len(notes) > 0)
        want = (want_problems, want_notes)
        mark = "PASS" if got == want else f"FAIL(问题={got[0]} 说明={got[1]}, 应为 {want})"
        if got != want:
            ok = False
            print(f"      {probs} {notes}")
        print(f"  [{mark}] {label}")

    print("== 定时任务检查 · 自测 ==")
    case("产物 0 字节 —— 应当报红", job(art_size=0), True, False)
    case("产物有内容 —— 不该报红", job(art_size=6), False, False)
    case("产物文件不存在 —— 应当明说没测到，而不是打绿灯",
         job(art_size=None), False, True)
    case("日志里有 command not found —— 应当报红",
         job(art_size=6, log_text="x\nfoo.sh: line 59: claude: command not found\n"),
         True, False)
    case("日志里有 Reached max turns —— 应当报红",
         job(art_size=6, log_text="Error: Reached max turns (50)\nrun finished (exit 0)\n"),
         True, False)
    case("日志干净 —— 不该报红", job(art_size=6, log_text="all good\n"), False, False)

    # ⛔ 上面六条都只喂一天、一个日志文件，**测不到我 2026-08-28 当场修的那两个缺陷**。
    #    一条自测跑绿却覆盖不到刚改的代码，是最容易骗过自己的形状 —— 补这两条。
    yday = d - datetime.timedelta(days=1)

    def shared_log_job(text):
        """日志路径不含 {d}：两天展开出同一个文件，用来验去重。"""
        art = os.path.join(tmp, f"v_{ds}.txt")
        with open(art, "w") as fh:
            fh.write("ok")
        with open(os.path.join(tmp, f"v_{yday.strftime('%Y%m%d')}.txt"), "w") as fh:
            fh.write("ok")
        shared = os.path.join(tmp, "shared.log")
        with open(shared, "w") as fh:
            fh.write(text)
        return {"name": "t", "artifact": os.path.join(tmp, "v_{d}.txt"),
                "log": shared, "what": "w"}

    j = shared_log_job(f"[{d.isoformat()}] foo: claude: command not found\n")
    probs, _n = check_job(j, [d, yday])
    if len(probs) != 1:
        print(f"  [FAIL(报了 {len(probs)} 条, 应为 1)] 同一个日志文件不该被扫两遍"); ok = False
    else:
        print("  [PASS] 同一个日志文件只扫一遍，同一条错误不重复报")

    j2 = shared_log_job("[2026-01-01] foo: claude: command not found\n")
    probs2, _n2 = check_job(j2, [d, yday])
    if probs2:
        print(f"  [FAIL] 日志里那条错误写着 2026-01-01（早已修好），不该再报：{probs2}"); ok = False
    else:
        print("  [PASS] 累积日志里的陈年旧账不再报红")

    shutil.rmtree(tmp, ignore_errors=True)
    print("\n== SELFTEST: 全部通过 ==" if ok else "\n== SELFTEST: 有失败 ==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
