#!/usr/bin/env python3
"""「现在有哪些窗口在跑 Claude」—— 所有检查共用的唯一探测口。

## 为什么有这个文件（2026-08-26）

用户当天从 tmux 换到了 herdr（herdr.dev，专给 AI agent 用的终端工作区管理器）。
换完之后 tmux 会话没关，里面留下一批**同名的空壳窗口**：窗口还在，窗格进程是
裸 bash，Claude 早就不在里面了。

⛔ 于是所有「靠 `tmux list-windows` 判断谁还活着」的检查同时坏掉，而且是**两头都错**：

  - 对着死壳子 `j-<project-B>` 喊「窗口还活着，便条已过期」——窗口是活的，干活的人不在；
  - 真正在跑的八个 Claude 全在 herdr 里（tab 名 AQRL / RCMAT / OfflineRCMG / DOTD /
    J / paper / concept），这些检查**一个都看不见**。

⭐ 这正是 check_handoff.py 自己反复写下的那条教训：别拿一个便于取得的代理量
（「tmux 里有几个窗口」）去代表一个它代表不了的状态（「有几个 Claude 在干活」）。
tmux 窗口存在，从来就不等于里面有人在干活；从前两者恰好一致，是因为窗口都是
`tmux new-window 'claude …'` 起的。换了工作区管理器，这个巧合就没了。

## 判据

按可靠性排序，取第一个能回答的：

  1. **herdr**：`herdr agent list` 直接给出「哪些窗格里跑着 agent、属于哪个 tab」。
     ⭐ 这比 tmux 那条准，因为它测的就是 agent 本身，不是窗口这个容器——
     文件浏览器插件开的 `viewer` tab、纯 shell 的 tab 都不会被算进来。
  2. **tmux**：退回老办法，窗口名即窗口。herdr 没装、没跑、或版本对不上时用。
  3. 都问不到就返回 None，让调用方打印「测不出来」而不是打印绿灯。

## 窗口名是什么

herdr 下＝**tab 的标签**（sidebar 上看到的那个名字）。交接便条的文件名要与它对齐：
`~/.claude/handoff/<tab 标签>.md`。tab 标签只在同一个 workspace 内保证不重名，
所以重名时本模块会在 `warnings` 里报出来——重名意味着两个窗口共用一份便条，
那份便条一定有一个是错的。

## 单独跑

    python3 ~/.claude/scripts/live_windows.py          # 人看的
    python3 ~/.claude/scripts/live_windows.py --json   # 机器读的
    python3 ~/.claude/scripts/live_windows.py --selftest
"""
import json
import os
import subprocess
import sys

# agent list 里这些 agent 才算「一个在干活的窗口」。herdr 认得十几种 agent，
# 但这台机器上只有 claude；写成集合是为了将来加 codex 时不必改判据。
AGENT_KINDS = {"claude", "codex"}


def _run(cmd, timeout=10):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def _herdr_bin():
    """herdr 可执行文件的绝对路径。

    ⛔ 别用裸命令名 `herdr`（2026-08-26 实踩）：cron 的 PATH 只有 /usr/bin:/bin，
    找不到装在 ~/.local/bin 里的 herdr，于是探测静默退化成「测不出来」，
    交接便条那道检查随即把整个目录里 41 个文件（含 DISPATCH_* / CLOSED_* 这些
    本来就不是便条的）全判成便条并逐个报错。⚠️ 症状出现在**另一个**检查里，
    而根因在这里 —— 这类跨脚本的静默失效最难查，所以路径必须写死。
    """
    for c in (os.environ.get("HERDR_BIN_PATH"),
              os.path.expanduser("~/.local/bin/herdr"),
              "/usr/local/bin/herdr", "/usr/bin/herdr"):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return "herdr"          # 最后退回裸名，交给 PATH 碰运气


def _herdr_json(args):
    """跑一条 herdr CLI 子命令，取回它的 result 对象。取不到就 None。"""
    raw = _run([_herdr_bin()] + args)
    if not raw:
        return None
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            return json.loads(line).get("result")
        except (ValueError, AttributeError):
            continue
    return None


def herdr_windows():
    """herdr 里跑着 agent 的 tab 标签。herdr 不可用就 None。

    ⚠️ 返回的是**跑着 agent 的 tab**，不是所有 tab。插件开的 tab（文件浏览器那种）
    和空 shell tab 不该被要求写交接便条。
    """
    agents = _herdr_json(["agent", "list"])
    if not agents or "agents" not in agents:
        return None
    tabs = _herdr_json(["tab", "list"])
    if not tabs or "tabs" not in tabs:
        return None

    label_of = {t.get("tab_id"): (t.get("label") or "").strip()
                for t in tabs["tabs"]}
    names = []
    for a in agents["agents"]:
        if a.get("agent") not in AGENT_KINDS:
            continue
        label = label_of.get(a.get("tab_id"), "")
        if label:
            names.append(label)
    # herdr 在跑但一个 agent 都没有，是合法状态（用户刚开起来）。
    # 返回空列表而不是 None：探测成功了，答案就是「没有」。
    return names


def tmux_windows():
    """tmux 窗口名。tmux 不可用就 None。

    ⚠️ 这条**测不出窗口里有没有人在干活**——空壳窗口照样会被算进来。
    只在 herdr 问不到时用。
    """
    tmux = next((c for c in ("/usr/bin/tmux", "/usr/local/bin/tmux",
                             os.path.expanduser("~/.local/bin/tmux"))
                 if os.path.isfile(c) and os.access(c, os.X_OK)), "tmux")
    out = _run([tmux, "list-windows", "-a", "-F", "#{window_name}"])
    if out is None:
        return None
    return [l.strip() for l in out.splitlines() if l.strip()]


def live_windows():
    """(names, source, warnings)。names 为 None 表示**没测出来**，不是「没有窗口」。

    ⛔ 调用方必须把 None 和 [] 分开处理：前者是这道检查失明了，后者是真的一个都没有。
    """
    warnings = []
    names = herdr_windows()
    source = "herdr"
    if names is None:
        names = tmux_windows()
        source = "tmux"
        if names is not None:
            warnings.append(
                "herdr 问不到，退回 tmux 窗口名 —— ⚠️ tmux 那条测的是「窗口在不在」，"
                "不是「里面有没有 Claude 在跑」，空壳窗口会被误判成活窗口。")
    if names is None:
        return None, "none", ["herdr 与 tmux 都问不到，无法判断哪些窗口在跑"]

    seen, dupes = set(), set()
    for n in names:
        if n in seen:
            dupes.add(n)
        seen.add(n)
    if dupes:
        warnings.append(
            f"{source} 里有重名窗口：{', '.join(sorted(dupes))} —— "
            "重名的窗口会共用同一份交接便条，其中至少一份是错的。请改名。")
    return sorted(seen), source, warnings


def selftest():
    """只验能验的那部分：解析与去重。真实探测依赖机器状态，不在这里断言。"""
    ok = True

    got = live_windows()
    if not (isinstance(got, tuple) and len(got) == 3):
        print("FAIL: live_windows 应返回三元组"); ok = False

    names, source, _w = got
    if names is not None and not all(isinstance(n, str) for n in names):
        print("FAIL: 窗口名应全是字符串"); ok = False
    if source not in ("herdr", "tmux", "none"):
        print(f"FAIL: source 取值意外 {source!r}"); ok = False

    # herdr 与 tmux 都问不到时，必须返回 None 而不是空列表
    real_h, real_t = globals()["herdr_windows"], globals()["tmux_windows"]
    globals()["herdr_windows"] = lambda: None
    globals()["tmux_windows"] = lambda: None
    n2, s2, w2 = live_windows()
    globals()["herdr_windows"], globals()["tmux_windows"] = real_h, real_t
    if n2 is not None or s2 != "none" or not w2:
        print("FAIL: 两边都问不到时应返回 (None, 'none', [告警])"); ok = False

    # 重名要被报出来
    globals()["herdr_windows"] = lambda: ["a", "a", "b"]
    n3, _s3, w3 = live_windows()
    globals()["herdr_windows"] = real_h
    if n3 != ["a", "b"] or not any("重名" in x for x in w3):
        print("FAIL: 重名窗口没被去重或没被告警"); ok = False

    print("selftest: 3 case pass" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    names, source, warnings = live_windows()
    if "--json" in sys.argv:
        print(json.dumps({"names": names, "source": source, "warnings": warnings},
                         ensure_ascii=False))
        return 0 if names is not None else 1
    if names is None:
        print("⛔ 测不出哪些窗口在跑（herdr 与 tmux 都问不到）")
        for w in warnings:
            print(f"   {w}")
        return 1
    print(f"== 在跑的窗口 ==（来源：{source}，{len(names)} 个）")
    for n in names:
        print(f"  · {n}")
    for w in warnings:
        print(f"  ⚠️ {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
