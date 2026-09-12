#!/usr/bin/env python3
"""交接便条检查 —— 长期窗口必须留下一份「我是谁、做到哪、下一步」的便条，且不能过期。

## 为什么有这个检查（2026-08-15 用户要求「要保证这个有效」）

多个 tmux 窗口长期并行干活，会话会被压缩、会被关掉、额度会用完。压缩本身不丢东西——
**丢的是没写进文件的东西**。所以每个长期窗口留一份便条，让压缩后的自己或接手的新窗口
能在一分钟内回到状态。

⚠️ 一份靠自觉维护的文档必然会过期，而**过期的交接便条比没有更坏**——接手的人会信它。
所以这个检查存在：它比对便条的时间戳与该窗口 transcript 的最后活动时间，**便条比会话
旧太多就报红**。

## 便条放哪、长什么样

`~/.claude/handoff/<窗口名>.md`，YAML 头 + 四个必填字段：

    ---
    window: concept-bf
    session: <会话名, 如 n-chang-6b>
    updated: 2026-08-15T06:44+09:00      # JST，写进产物的日期一律走 JST
    ---
    ## 我在干什么
    一两句白话，不用内部代号。
    ## 任务书 / 必读
    - ~/kb_tools/CONCEPT_BACKFILL_BRIEF.md
    ## 做到哪了
    ⚠️ 指向已存在的状态源，不要复制它的内容（复制品会和真源打架）。
    ## 被打断的话，下一步做什么
    一条具体动作，接手的人照着做就能继续。

## 退出码

0 = 全部便条新鲜；1 = 有便条过期、缺字段，或有长期窗口根本没写便条。
本脚本只报事实，不替谁写便条。
"""
import argparse
import os
import re
import subprocess
import sys
import time

HANDOFF = os.path.expanduser("~/.claude/handoff")
PROJECTS = os.path.expanduser("~/.claude/projects")

REQUIRED_HEADINGS = ["我在干什么", "任务书", "做到哪了", "下一步"]
REQUIRED_FIELDS = ["window", "session", "updated"]

# 便条比会话最后活动时间旧超过这么久 = 过期
STALE_HOURS = 3.0
# 便条自称的更新时刻与文件修改时间之间容许多少偏差（分钟）。
# 往前（字段比文件旧）＝改了内容忘了改字段，给的余量大一点，因为写完字段之后
# 还要写正文、跑检查，文件时间本来就会晚一些；往后（字段比文件新）＝时间是编的，
# 余量只留给时钟抖动。
DRIFT_TOLERANCE_MIN = 90.0
FUTURE_TOLERANCE_MIN = 5.0

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from live_windows import live_windows as _probe_live
except ImportError:                                  # 探测器被挪走也不该让检查静默变绿
    _probe_live = None

# 最近一次探测的来源与告警，供报告开头打印。⚠️ 存来源不是装饰：
# 「从哪儿测来的」决定了这份结果可信到什么程度（herdr 测的是 agent，tmux 测的是窗口壳）。
_LIVE_SOURCE = "unknown"
_LIVE_WARNINGS = []


def _live_names():
    global _LIVE_SOURCE, _LIVE_WARNINGS
    if _probe_live is None:
        _LIVE_SOURCE, _LIVE_WARNINGS = "none", [
            "⛔ live_windows.py 不在 ~/.claude/scripts/，这道检查退化成「只看便条格式」，"
            "测不出任何一份便条是否过期。"]
        return None
    names, _LIVE_SOURCE, _LIVE_WARNINGS = _probe_live()
    return names


def tmux_windows():
    """在跑的窗口名。测不出来就返回 None。

    ⚠️ 名字里的 tmux 是历史包袱：2026-08-26 用户换到 herdr 之后，这个探测已经改成
    走 `live_windows.py`（先问 herdr，问不到再退回 tmux）。函数名保留是因为
    selftest 与外部调用按名字传它。

    ⛔ 换工作区管理器那天，tmux 会话没关，留下一批**同名的空壳窗口**（窗口在、
    Claude 不在），这道检查于是一边对着死壳子喊「便条过期」，一边完全看不见
    herdr 里真正在跑的八个窗口。判据必须测 agent 本身，不能测窗口这个容器。
    """
    return _live_names()


def parse_note(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        return None, None, "没有 YAML 头"
    head, body = m.group(1), m.group(2)
    fields = {}
    for line in head.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    missing = [f for f in REQUIRED_FIELDS if not fields.get(f)]
    if missing:
        return fields, body, f"缺字段: {', '.join(missing)}"
    absent = [h for h in REQUIRED_HEADINGS if h not in body]
    if absent:
        # ⚠️ 报缺小节时**把标题原文一并打出来**（2026-08-15 加）：当天有个窗口
        # 连踩两次同一个坑，两次都是**自造了小节标题**（把「做到哪了」写成
        # 「今天完成了什么」、把「下一步」写成「下次接手的人从哪一句接着往下走」）。
        # 内容都在、意思也对，但这个检查是按**固定字符串**找的，自造标题让它失明。
        # 只说「缺哪一节」不够——人会照自己的理解再写一个近义标题，于是再红一次。
        # 直接给可照抄的原文，把「凭理解重写」变成「复制粘贴」。
        return fields, body, ("缺小节: " + ", ".join(absent)
                              + " ｜ ⛔ 本检查找的是**标题里含不含这几个词**（不是整行照抄）："
                              + "、".join(REQUIRED_HEADINGS)
                              + "。别改写成近义说法（「今天完成了什么」不含「做到哪了」，"
                              + "「从哪一句接着往下走」不含「下一步」）。"
                              + "惯例写法：## 我在干什么 / ## 任务书 / 必读 / ## 做到哪了 "
                              + "/ ## 被打断的话，下一步做什么")
    return fields, body, None


def _now_field():
    """当前时刻，写成这份便条用的那种格式。

    ⭐ 存在的理由是「能给成品就别给规矩」：这个字段被写错过十次（2026-08-15 三次、
    2026-08-22 四次、2026-08-29 三次，跨六个窗口），每一次都是凭印象写而不是查出来的。

    ⚠️ 手写会以两种不同的方式出错，**修法不同，先分清是哪一种**：

      · 超前**正好 540 分钟** → 时区。本机时区就是世界时，而「取本机时间再贴一个
        +09:00」正好差九小时。修法是让 `time.strftime` 自己出偏移量，别手贴。
      · 超前**一个不规律的量** → 根本没读系统时钟，是估了一个时间填进去。
        2026-08-29 实测三份便条分别超前 21、375、8 分钟，⛔ **没有一个是 540**，
        彼此也不成比例。⭐ 判别法就是这条：任何系统性成因（时区、时钟偏差、
        代码里的常数）都产生**固定**偏差，只有人估的才每次差得不一样。

    ⛔ 那次我先按时区结论发了通知，是同伴窗口拿超前量把它否掉的。⚠️ 把一个成立过的
    成因写进注释，会让下一个人照着它改时区、改不动就以为是玄学——**所以判别法要和
    成因写在一起**。（另已排除时钟偏差：家目录在网络硬盘上，服务器时钟落后也会造成
    「字段对而文件时间偏早」，但实测本机写文件与记时只差 0.005 秒。）
    """
    return time.strftime("%Y-%m-%dT%H:%M%z", time.localtime())


def parse_ts(s):
    """接受 2026-08-15T06:44+09:00 或 2026-08-15 06:44 等常见写法，返回 epoch 秒。"""
    s = s.strip().strip('"\'')
    s = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", s)
    for fmt in ("%Y-%m-%dT%H:%M%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            t = time.strptime(s, fmt)
            if "%z" in fmt:
                import calendar
                # strptime 带 %z 时 struct_time 无 tz 信息，退回用 datetime
                from datetime import datetime
                return datetime.strptime(s, fmt).timestamp()
            return time.mktime(t)
        except ValueError:
            continue
    return None


def main(handoff=None, probe=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="用临时目录跑一遍新鲜/过期/缺字段三种情形")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    return run(handoff or HANDOFF, probe or tmux_windows)


def run(HANDOFF, probe):
    if not os.path.isdir(HANDOFF):
        print(f"⛔ 交接便条目录不存在: {HANDOFF}")
        return 1

    # ⚠️ 这个目录里不只有交接便条。别的窗口会把「交付清单」之类的文件也放进来
    # （2026-08-15 实测：k-books 放了一份 `k-books-delivery-1.md`，内容是「以下改动请
    #  总控提交」的路径清单，本来就不该有 YAML 头，却被本检查判成「便条格式不合」）。
    # **判据改成：只管文件名与某个在跑的窗口同名的那些**——那才是交接便条的约定位置；
    # 其余文件是别人放在这里的东西，本检查管不着。
    # 这与规则 24 是同一件事：别拿一个便于计算的代理量（「目录里的 .md 文件」）
    # 去代表一个它代表不了的状态（「这是一份交接便条」）。
    probed = probe()
    # ⛔ None（探测失败，不知道谁在跑）与 []（探测成功，答案是一个都没在跑）是两件事。
    #    原先写作 `set(probe() or [])`，两者塌成同一个空集合，走同一条分支：
    #    「谁都不知道」时按**全都活着**处理。那条分支对 None 是对的（宁可多报几条红，
    #    也不能因为测不出来就打绿灯），⚠️ 但对 [] 是错的——一个窗口都没在跑时，
    #    没有任何一份便条**能**过期（过期的定义是「窗口还在跑而便条停在过去」），
    #    却会把目录里每一份历史便条都报成过期。
    blind = probed is None
    live_names = set(probed or [])
    # ⛔ 探测失败时不能把目录里所有 .md 都当便条（2026-08-26 实踩）：
    #    那天 cron 里 herdr 找不到（PATH 只有 /usr/bin:/bin，而 herdr 装在 ~/.local/bin），
    #    探测退化成失明，于是 41 个文件全被当成便条，DISPATCH_*、CLOSED_*、
    #    各种交付清单被逐个报「没有 YAML 头」「缺小节」——一屏噪声，真问题淹没在里面。
    #    这些前缀按约定就不是交接便条，任何时候都不该被当成便条判。
    NOT_NOTES = ("DISPATCH_", "CLOSED_", "BATCH", "CONCEPT_PAGE_BRIEF")
    def is_note_name(stem):
        return not any(stem.startswith(p) for p in NOT_NOTES)
    notes = [f for f in sorted(os.listdir(HANDOFF))
             if f.endswith(".md")
             and (f[:-3] in live_names if not blind else is_note_name(f[:-3]))]
    live = sorted(live_names) if not blind else None
    now = time.time()
    problems = []

    src = (f"，在跑的窗口来自 {_LIVE_SOURCE}：{len(live_names)} 个" if not blind
           else "，⛔ 探测不到在跑的窗口，下面一律按「窗口还活着」从严判")
    print(f"== 交接便条 == 目录 {HANDOFF}，{len(notes)} 份{src}")
    for w in _LIVE_WARNINGS:
        print(f"  ⚠️ {w}")

    for fn in notes:
        path = os.path.join(HANDOFF, fn)
        name = fn[:-3]
        fields, body, err = parse_note(path)
        if err:
            problems.append(f"{name}: {err}")
            print(f"  ⛔ {name:16} {err}")
            continue

        # ⛔⛔ 便条**自称**的窗口名不能用来判活死（2026-08-22 修，那是一个能被自己关掉的警报）。
        #    上面那段已经按**文件名**过滤过：`notes` 里每一份的文件名都与某个活着的 tmux 窗口同名，
        #    所以进到这里的便条**按构造就是活的**。而原先这里又拿 `window:` 字段去重判一次，
        #    ⛔ 于是把字段写成「j-<project-B>（现 tmux main:7）」这种带括注的形式，就与窗口名匹配不上、
        #    被判成「窗口已关」——⚠️ **而判过期那一步只对活着的窗口生效**，
        #    也就是说：**给这个字段加一个括注，就能永久关掉自己的过期警报**。
        #    实测当时 j-<project-B> 正处在这个状态（tmux 第 7 号窗口活着，检查却打「窗口已关」）。
        #    ⭐ 这与本文件上面那条同源：别拿一个便于取得的代理量去代表一个它代表不了的状态。
        # 上面已按文件名过滤过：探测成功时，能走到这里的便条都对应一个在跑的窗口。
        # ⭐ 探测失败时故意仍按「活着」判——测不出来就从严，宁可多几条红也不打绿灯。
        alive = True
        # 字段与文件名不一致本身是缺陷：别的工具也会按这个字段找窗口。报出来，不照它办事。
        declared = fields.get("window")
        if declared is not None and declared != name:
            problems.append(f"{name}: window 字段写的是 {declared!r}，与文件名不一致")
            print(f"  ⛔ {name:16} window 字段 {declared!r} ≠ 文件名 —— "
                  f"⚠️ 这个字段不再用于判活死，但不一致会误导按它找窗口的人")

        ts = parse_ts(fields["updated"])
        if ts is None:
            problems.append(f"{name}: updated 时间戳解析不了 ({fields['updated']!r})")
            print(f"  ⛔ {name:16} updated 解析不了: {fields['updated']!r}")
            continue

        # ⚠️ **过期判定读的是便条自己写的那个时间，不是文件的修改时间**，
        # 所以这个字段写错就直接把过期警报关掉了——写成未来时间尤其危险：
        # 年龄成了负数，永远小于阈值，那份便条从此**永久显示新鲜**。
        # 2026-08-15 一个窗口一天之内把它写成未来时间三次（超前 3.1 小时、
        # 45 分钟、48 分钟），每次都是没先查当前时刻就凭印象写。
        # ⛔⛔ 2026-08-22 又四次，分布在三个不同窗口上（超前 8、10、13、14 分钟）——
        #    **规矩加检查都没能挡住它，所以这里改成直接给出可粘贴的那一行**。
        #    ⭐ 犯它的那个窗口自己诊断得最准：**「时间戳是这份文件里唯一一个我不用查
        #    就能写出来的字段——所以它是唯一一个我没查的」**；而且它刚刚才因为同一件事
        #    纠正过别人，**规矩完全没有阻止它**，因为写的时候它根本没意识到那是个需要核的值。
        #    ⚠️ 所以对这一类，能给成品就别给规矩。
        # 所以拿文件的修改时间作旁证：两者对不上，说明这个字段是编的。
        # ⭐⭐ 这一步是整段能成立的关键，写下来免得将来有人「简化」掉它：
        #    **一个自述性的字段不能自证。** ⚠️ 只看字段的话，未来时间戳是**自洽**的——
        #    「它比现在新」这件事，只有引入一个**写它的人控制不了的量**（文件的修改时间）才看得出来。
        #    ⛔ 同理，`scan_mention_without_link.py` 的守卫键在「范围解析出了几个文件」而不是
        #    「命中几条」：两处都是拿当事人改不动的量去卡当事人。
        # ⚠️ 另外注意上面那行可粘贴的时间戳**只给这两支**（字段是编的 / 改了内容没改字段）——
        #    那两种情形下便条内容本身是新的，只有字段错了。⛔ 真正「内容过期」那一支不给，
        #    给了就等于替人造出这道检查本来要防的那种谎：时间戳新了，内容还是旧的。
        drift_min = (os.path.getmtime(path) - ts) / 60.0
        if drift_min < -FUTURE_TOLERANCE_MIN:
            problems.append(f"{name}: updated 写的是未来时间（比文件本身新 "
                            f"{-drift_min:.0f} 分钟），过期警报会被它永久关掉")
            print(f"  ⛔ {name:16} updated 是未来时间，超前 {-drift_min:.0f} 分钟"
                  f" ← 这会让它永远显示新鲜")
            # ⛔ 这里以前直接断言成因是时区，2026-08-29 被实测否掉：三处超前
            #    21、375、8 分钟，没有一个是 540。所以现在只报判别法，不下结论。
            if abs(-drift_min - 540) < 5:
                print("       超前正好九小时 → 是时区：本机时区就是世界时，"
                      "手贴 +09:00 会差这么多。")
            else:
                print("       ⚠️ 超前量不是 540 分钟，所以**不是时区**——"
                      "任何系统性成因都产生固定偏差，不规律的偏差意味着"
                      "这个时间是估出来的，没有去读系统时钟。")
            print(f"       ⛔ 别手写：python3 ~/.claude/scripts/touch_handoff.py {name}"
                  f"（它写出来会是 {_now_field()}）")
            print("       ⚠️ 但只刷字段会让一份可能已过期的便条显得新鲜——"
                  "先翻正文确认它说的还是现在的状态。")
            continue
        if drift_min > DRIFT_TOLERANCE_MIN:
            # ⛔ 措辞不许预设是谁改的（2026-08-27 改）。原话是「改了内容没改字段」，
            #    那句话预设了改动出自便条主人。实测出现过另一种：**别的窗口直接往这份
            #    便条里追加了一节**，主人根本不知道发生过，于是它照原话去找"自己忘了刷字段"
            #    的记忆，找不到，反而怀疑检查报错了。
            # ⭐ 被人改过而你不知道，比自己忘了刷字段严重得多 —— 所以这里两种可能并列摆出，
            #    先让人去看文件末尾，而不是先让人去刷字段。
            #    同族＝check_paper_window_scope 同日的大修：**别断言一件你证明不了的事**。
            problems.append(f"{name}: 文件在 updated 之后被改过 {drift_min:.0f} 分钟"
                            f"（自己没刷字段，或别人写进来了——这里分不出）")
            print(f"  ⚠️ {name:16} 文件在 updated 之后被改过 {drift_min:.0f} 分钟")
            print(f"       ⭐ 两种可能，先看哪一种：① 你自己改了正文忘了刷字段；"
                  f"② **别的窗口直接写进了这份文件**（实测发生过）。")
            print(f"       ⛔ 先翻一遍文件末尾确认是不是第②种再刷字段 —— "
                  f"刷字段只会让一份你没读过的内容显得新鲜。")
            print(f"       改成这一行：updated: {_now_field()}")
            print(f"       ⭐ 或者别手写：python3 ~/.claude/scripts/touch_handoff.py {name}")
            continue

        age_h = (now - ts) / 3600.0
        # 会话文件最后活动时间：便条声称的窗口若还在跑，就该比便条新
        mark = "·" if alive else "（窗口已关）"

        # ⛔⛔ 一个已经收工、正在等用户决定的窗口，它的便条**越旧越对**：
        # 内容就是终态，没什么可更新的。而先前这道检查把它一路报成「过期」，
        # ⚠️ 2026-08-24 实测有一份被报了 37.9 小时，我去读它，正文写的是
        # 「全部完成、无在飞任务、等用户对去向的决定」——**便条是对的，检查错了**。
        # ⭐ 判据：**「便条旧」与「便条不再对」是两件事**，而这道检查只测得到前一件。
        # 所以给便条一个办法声明后者不成立：正文里写一行 `PARKED:` 开头的句子，
        # 说明在等什么。⛔ 这不是免检开关——它要求写下**在等谁的什么**，
        # 那句话本身就是可以被读到、被判断是否还成立的东西。
        parked = None
        for ln in (body or "").splitlines():
            t = ln.strip().lstrip("-*# ").strip()
            if t.upper().startswith("PARKED:"):
                parked = t[len("PARKED:"):].strip()
                break
        if parked:
            # ⛔⛔ 挂起理由里写了「等到某个日期」而那个日期已经过去 —— 挂起就该失效（2026-08-27 加）。
            #    实例：concept 那份便条写「PARKED: 等 2026-08-30 15:00 UTC 周额度重置；
            #    在那之前派任何下级都会立刻失败」，而该窗口 08-27 早已照常派下级干完三批活。
            #    ⚠️ 这行的危害是双重的：它挂在「## 下一步」标题底下，新接手的人读起来像现行指令，
            #    可能照它白停三天；同时它让这份便条**永久豁免过期警报** —— 一句写死的等待理由
            #    把一道会随时间报警的检查变成了永不报警的检查。
            #    ⭐ 判据只认「等/至/到/until + 日期」这种明确的等待到某时刻，不认顺手写在括号里的
            #    记录日期（「在等用户挑下一批（2026-08-26 记）」不该被判过期）。
            m_until = re.search(r"(?:等到?|至|到|until)\s*(\d{4}-\d{2}-\d{2})", parked)
            if m_until:
                until = parse_ts(m_until.group(1))
                if until is not None and until < now:
                    over_d = (now - until) / 86400.0
                    problems.append(
                        f"{name}: 挂起理由说等到 {m_until.group(1)}，那个时刻已经过去 "
                        f"{over_d:.1f} 天，挂起豁免作废")
                    print(f"  ⛔ {name:16} 挂起理由已过期：说等到 {m_until.group(1)}，"
                          f"已过去 {over_d:.1f} 天")
                    print(f"       ⚠️ 这一行同时在两处误导：接手的人会当成现行指令，"
                          f"而它还让这份便条一直豁免过期警报。")
                    continue
            print(f"  ⏸ {name:16} {age_h:5.1f}h 前更新 · 已收工挂起：{parked[:60]}")
            continue

        if alive and age_h > STALE_HOURS:
            problems.append(f"{name}: 便条 {age_h:.1f} 小时没更新，而窗口还在跑")
            print(f"  ⚠️ {name:16} {age_h:5.1f}h 未更新 {mark} ← 窗口还活着，便条已过期")
        else:
            print(f"  ✅ {name:16} {age_h:5.1f}h 前更新 {mark}")

    # 活着但没便条的长期窗口
    if live:
        have = set()
        for fn in notes:
            f, _, e = parse_note(os.path.join(HANDOFF, fn))
            if f:
                have.add(f.get("window", fn[:-3]))
        # 只管明确长期干活的窗口：名字里带这些的
        LONG = ("concept", "paper", "book", "read", "audit", "prop", "seed", "chain")
        missing = [w for w in live
                   if any(k in w.lower() for k in LONG) and w not in have]
        for w in sorted(set(missing)):
            problems.append(f"{w}: 窗口在跑但没有交接便条")
            print(f"  ⛔ {w:16} 窗口在跑, 没有交接便条")

    if problems:
        print(f"\n== HANDOFF: {len(problems)} 处问题 ==")
        print("   ⚠️ 过期的交接便条比没有更坏——接手的人会信它。")
        print(f"   便条格式见本脚本 docstring；放在 {HANDOFF}/<窗口名>.md")
        return 1

    print("\n== HANDOFF: CLEAN ==")
    return 0


def selftest():
    """装上时验证它真的会报红，而不是只会打印绿色。"""
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    ok = True
    now = time.time()

    def write(name, updated, full=True, mtime="match", declared=None, parked=None):
        """mtime="match" ＝ 把文件修改时间对齐到 updated 字段（真实便条就是这样：
        没人碰它，两个时间就一起停在那里）。传数字则强行制造两者不一致。"""
        body = ("## 我在干什么\n干活\n## 任务书 / 必读\n- x\n## 做到哪了\nx\n"
                "## 被打断的话，下一步做什么\nx\n") if full else "## 我在干什么\n干活\n"
        if parked:
            body += f"\nPARKED: {parked}\n"
        p = os.path.join(tmp, f"{name}.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(f"---\nwindow: {declared or name}\nsession: s\nupdated: {updated}\n---\n{body}")
        t = parse_ts(updated) if mtime == "match" else mtime
        if t:
            os.utime(p, (t, t))

    fresh = time.strftime("%Y-%m-%dT%H:%M", time.localtime(now - 600))
    stale = time.strftime("%Y-%m-%dT%H:%M", time.localtime(now - 8 * 3600))
    future = time.strftime("%Y-%m-%dT%H:%M", time.localtime(now + 45 * 60))

    cases = [
        ("新鲜便条应当通过", lambda: (write("fresh-note", fresh), True)[1], 0),
        ("过期便条应当报红", lambda: (write("stale-note", stale), True)[1], 1),
        # ⛔ 2026-08-24 加：一份已收工、正在等用户决定的便条**越旧越对**。
        # ⚠️ 这一例的时间与上一例完全相同（8 小时前），差别只有那一行 PARKED——
        # ⭐ 所以两例并排就证明了「是那一行让它通过的」，不是别的什么让它通过的。
        ("收工挂起的便条不该报红",
         lambda: (write("parked-note", stale, parked="等用户对去向的决定"), True)[1], 0),
        # ⛔ 而没有写在等什么的，不算挂起：这条防的是把 PARKED 当免检开关用
        ("PARKED 后面空着的仍按过期算",
         lambda: (write("bare-parked", stale, parked=""), True)[1], 1),
        ("缺小节应当报红", lambda: (write("thin-note", fresh, full=False), True)[1], 1),
        # 这两条是 2026-08-15 加的：字段是编的，比便条过期更隐蔽
        ("updated 写成未来时间应当报红",
         lambda: (write("future-note", future, mtime=now), True)[1], 1),
        # ⚠️ 这一条的字段时间**故意选在过期线以内**（2.5 小时 < 3 小时）：
        # 用 8 小时前那个会同时踩中过期判定，于是无论偏差判定在不在都会报红，
        # 测不出想测的东西。
        # ⛔⛔ 2026-08-22 加：这一条测的是「一个能被自己关掉的警报」。
        #    原先判活死用的是便条自称的 `window:` 字段，于是把它写成带括注的形式就匹配不上
        #    tmux 窗口名、被判成「窗口已关」，⚠️ 而过期判定只对活着的窗口生效——
        #    **加个括注就能永久静音自己的过期警报**。实测当时确有一份便条正处在这个状态。
        #    现在活死按**文件名**判（上面的过滤已经保证了这一点），字段不一致单独报出来。
        #    ⭐ 这一条对改动前的代码是 FAIL：那时它会打绿勾加「（窗口已关）」。
        ("window 字段带括注不许静音过期警报",
         lambda: (write("muted-note", stale, declared="muted-note（现 tmux main:9）"), True)[1], 1,
         lambda: ["muted-note"]),
        ("改了内容却没改 updated 应当报红",
         lambda: (write("drift-note",
                        time.strftime("%Y-%m-%dT%H:%M", time.localtime(now - 2.5 * 3600)),
                        mtime=now), True)[1], 1),
        # ⛔⛔ 2026-08-26 加（换 herdr 那天）：**「探测失败」与「探测成功，答案是零」不是一回事。**
        #    上面「过期便条应当报红」那一条走的是默认 probe（返回 None＝测不出来），
        #    从严按「窗口还活着」判，所以报红——那是对的。
        #    ⚠️ 这一条给的是 `lambda: []`：探测成功了，答案是一个窗口都没在跑。
        #    此时同一份 8 小时前的便条**不该**报红：过期的定义是「窗口还在跑而便条停在过去」，
        #    窗口都不在跑，便条停在那里正是它应有的样子。
        #    ⭐ 两条并排（同一份 stale 便条，只有 probe 不同，期望相反）才证明得了
        #    这个分支真的在按来源区分，而不是碰巧都对。
        ("一个窗口都没在跑时，旧便条不该报红",
         lambda: (write("closed-note", stale), True)[1], 0, lambda: []),
        # ⛔⛔ 2026-08-27 加：挂起理由里写了「等到某日」而那天已经过去 —— 豁免必须作废。
        #    ⚠️ 这一条防的是一种**能把自己变成永不报警的检查**的写法：PARKED 一挂，
        #    过期警报就永久静音，而理由是不是还成立没有任何东西在看。
        #    实例=concept 便条写「等 2026-08-30 周额度重置，在那之前派下级必失败」，
        #    而该窗口 08-27 早已照常派下级干完三批活；那行还挂在「## 下一步」底下，
        #    新接手的人读起来像现行指令。
        ("挂起理由说等到的日子已经过去 —— 豁免作废，应当报红",
         lambda: (write("expired-parked", stale,
                        parked="等 2020-01-01 15:00 UTC 周额度重置"), True)[1], 1,
         lambda: ["expired-parked"]),
        # ⭐ 与上一条并排：日期只是顺手记在括号里的，不是「等到那天」——不该被判过期。
        #    只测报红那一向等于没验：那样把所有含日期的挂起理由都误杀了也发现不了。
        ("挂起理由里顺带写了个过去的日期 —— 不该报红",
         lambda: (write("dated-parked", stale,
                        parked="在等用户挑下一批要读什么（2020-01-01 记）"), True)[1], 0,
         lambda: ["dated-parked"]),
    ]
    for case in cases:
        label, setup, want = case[0], case[1], case[2]
        # ⚠️ 有些用例必须在「tmux 可见」的情形下跑：默认的 probe 返回 None，
        #    那时活死判定短路成「全都活着」，⛔ 于是测不出任何与活死有关的缺陷。
        #    2026-08-22 我第一版就栽在这里——写了一条用例，改动前后返回值一样，**它什么都没测**。
        probe = case[3] if len(case) > 3 else (lambda: None)
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        setup()
        got = run_quiet(tmp, probe)
        status = "PASS" if got == want else f"FAIL(得到 {got}, 应为 {want})"
        if got != want:
            ok = False
        print(f"  [{status}] {label}")

    shutil.rmtree(tmp, ignore_errors=True)
    print("\n== SELFTEST:", "全部通过 ==" if ok else "有失败 ==")
    return 0 if ok else 1


def run_quiet(d, probe):
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = run(d, probe)
    return r


if __name__ == "__main__":
    sys.exit(main())
