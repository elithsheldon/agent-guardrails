---
name: cron-agent-jobs
predicate: python3 /home/<user>/n-chang/.claude/scripts/check_cron_agent_jobs.py
manual: false
status: PASS
last-pass: 2026-09-11
---
定时任务里的 headless claude 调用有没有在静默失败 (2026-08-28 加)。

**要解决的问题**: `~/wild/_meta/daily_scout.sh` 每天粗筛 arXiv 决定要不要叫醒 wild 那条线,
写法是 `claude -p --model haiku >"$VERDICT"` (**不看退出码**) 再
`head -1 "$VERDICT" | grep -q WAKE && WAKE=1 || WAKE=0`。
⛔ 调用一失败产物就是空的, 于是判成 `WAKE=0` —— **「筛选失败」与「筛过了没东西」完全同形**,
不留任何痕迹。⚠️ **它不是理论缺陷: 装这道检查时它正连坏两天** (08-27/08-28 产物都是 0 字节,
日志里 `claude: command not found`), 而且是撞上一次人工排查才被看见的。

**根因**: cron 的 PATH 只有 `/usr/bin:/bin`, 而 claude 装在 `~/.local/bin`。
⭐ 与 2026-08-26 在 live_windows.py 上踩的是同一个坑 (那次是 herdr 找不到)。
全机复查过: cron 下 `git`/`tmux`/`python3` 都在 /usr/bin 里找得到, **只有 claude 与 herdr 找不到**;
知识库那三个定时脚本自己 export 了 PATH 所以没事, `~/wild` 那两个都没有,
而 wild_watchdog.sh 里的 claude 只出现在给人看的提示文字里、不是真调用。

**测什么** (两件, 都键在脚本作者控制不了的量上): ① 最近两天的产物存在但为 0 字节;
② 日志里出现 `command not found` / `No such file` / `Reached max turns`。
⚠️ 产物**不存在**不算失败 (可能没到运行时刻或任务已停), 但会明说「本检查什么都没测到」——
一个测不到东西的检查最爱伪装成绿灯。

**故意不测**: 「那天该不该叫醒」(要重跑粗筛, 不属于一道检查的成本与判断);
也不替任何脚本改 PATH —— 报出来交给拥有那个脚本的窗口改。

**装上时的反向验证**: 八条用例, 空产物报红/正常产物不报/产物缺失明说没测到/三种日志错误各报红/
日志干净不报。⭐ 另加两条是**针对装上第一次跑就暴露的两个自身缺陷**补的:
同一个日志文件被扫两遍导致重复报; 累积型日志 (知识库那份 daily.log) 翻出 8-20 的陈年旧账。
⚠️ 前六条都只喂一天一个日志文件, **覆盖不到这两处** —— 一条跑绿却覆盖不到刚改的代码的自测,
是最容易骗过自己的形状。第三次修改把去重键从「哪个日志文件」换成「哪一类错误」并带上天数。

**报红后怎么办**: 修那个脚本本身 —— 两层缺一不可, ① 脚本自己验产物 (非空、形状对);
② 验不过时**响亮地失败**, ⛔ 别退回一个看起来安全的默认值 (判不出来时宁可叫醒人)。
⛔ 别为了转绿而把出问题的任务从 JOBS 里删掉。

**当前状态**: wild 那条已登记给对应窗口 (`~/.claude/handoff/DISPATCH_wild_daily_scout_fix.md`,
含根因、实锤证据与三件修法), 本窗口未动 ~/wild 任何文件。所以这条目标现在是红的,
**它会一直红到那个脚本被修好为止** —— 这正是它存在的意义。

retire-when: 不再有定时任务跑 headless claude。
