# agent-guardrails

[English](README.md) · [日本語](README.ja.md) · **中文**

Claude Code 的**防错钩子集**。让重复犯的错**由机器拦住**，而不是再写一条
「下次注意」的笔记。

> 人的注意力靠不住，要用机械来担保。

## 为什么做这个

实测了 30 个会话、887 条用户发言：用户纠正我的地方共 **44 处**，收敛成 6 类。
而**这 6 类全都只靠「写在笔记里的文字」在防**。笔记早就写好了，错照样在犯。

| 实测次数 | 模式 | 现在的防线 |
| --- | --- | --- |
| 12 | 文字与呈现的质量 | `reply_check.py` 检出 |
| 9 | 过早宣称做完了 | `reply_check.py` 检出 |
| 9 | 交付没人要的东西 | `outward_action_guard.py` **拒绝** |
| 7 | 没试就说「做不到」 | `reply_check.py` 检出 |
| 4 | 漏读指令 | 留在基准文件（未到阈值） |
| 3 | 弄错目标仓库/环境 | 留在基准文件（未到阈值） |

采纳的线是：**出现 ≥5 次 = 在反复犯 = 笔记治不好**——那条笔记已经失效过一次了。
4 次以下的仍留作文字。全都做成拦截，警告会饱和到没人看。

## 有什么

### 钩子（注册在 `~/.claude/settings.json`，全目录生效）

| 文件 | 事件 | 做什么 |
| --- | --- | --- |
| `reply_check.py` | Stop | 检出缺少状态块、没有证据的「已完成」、没试就说的「做不到」、机器写作的句式痕迹（`X, not Y` 对仗、数数式开头、cleft 开头、清嗓子式前置），以及聊天机器人口头禅。**只告警**——在 Stop 上硬拦有死循环风险 |
| `outward_action_guard.py` | PreToolUse(Bash) | **拒绝**难以撤销的对外动作（PR / push / 建仓 / 发布 / gist）。同时拒绝 `<检查> \| tail; echo $?`——那读到的是 `tail` 的退出码，不是检查的 |
| `guard_the_guards.py` | PreToolUse(Edit/Write) | 编辑检查器、钩子、配置或 memory 时要求确认。防止**被审的一方去改判卷人**而不是改产物 |
| `daily-retro-reminder.sh` | PostToolUse | 写完日报时催促做复盘 |

### 技能

`skills/daily-retro/` — 以「写日报」为触发点的改进循环。把每个错误尽量往下推：

> memory → 文档 → 脚本 → 前置检查 → 测试 → 权限

### 脚本

| 文件 | 用途 |
| --- | --- |
| `mistake-frequency.py` | 从全部历史会话里**数**各类纠正出现了多少次，让「这个我已经改好了」变成实测而非印象 |
| `verify-gates.py` | **给拦截器本身做自检**。喂该触发的输入和不该触发的输入各一遍 |

### 参考资料

`reference/anti-self-deception/` — 另一支团队成熟的防错机制（24 条规则、15 个脚本、
29 项常驻检查），经许可、匿名化后收录。详见该目录的 `ATTRIBUTION.md`。

## 最有用的两个

**`guard_the_guards.py`** — 其他所有防线看的都是「产物」，没有一层拦住
**被审的人去改判卷人**。我刚建好三个钩子和一套自检，而它们全都可以被我随手改掉。

**`verify-gates.py`** — 陈旧检测我写了三个版本，三次都是 18 条全过。
不去读那些数字的话，我会连着三次报告「一切健康」。
**从没失败过的检查，可能什么都没在守。**

## 安装

取下来后 `bash install.sh`。会复制到 `~/.claude/hooks/` 和 `~/.claude/skills/`，
并把钩子注册进 `~/.claude/settings.json`——只追加，保留已有配置。

`CLAUDE.example.md` 要先读一遍，按自己的环境改（memory 的绝对路径、日报存放位置），
再放到 `~/.claude/CLAUDE.md`。

装完一定要跑自检：

    python3 ~/.claude/skills/daily-retro/scripts/verify-gates.py

全新环境 21/21，已配置环境 26/26。

## 注意

- 钩子放在 `~/.claude/` 下，所以**在任何目录都生效**。memory 不是——它按 Claude
  启动的目录分区，所以跨项目的原则要写进每次都会读的 `~/.claude/CLAUDE.md`。
- `outward_action_guard.py` 会拦 push。确实要推的加 `CLAUDE_OUTWARD_OK=1`。
  嫌吵就从 `GUARDED` 里删条目。
- `reply_check.py` 是正则，会误报。误报时**把模式收窄，不要删掉这项检查**。
- 钩子的运行时提示目前是日文。那部分是给 agent 读的，不影响行为，欢迎翻译。

## 许可

MIT
