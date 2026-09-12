---
name: config-regression-tests
description: 操控层（hooks/skills/goals/settings）自己也要被测——两条常驻检查、行为回归用例怎么写、以及三个把测试写坏的实例
metadata:
  node_type: memory
  type: feedback
  originSessionId: f18a5265-8750-436e-860f-b283dc919ae7
---

**空白的形状**（2026-08-26 发现，来自 Anthropic 那篇 AI-native SDLC 长文的一句话）：
四十多个检查脚本和二十多条常驻目标**全都在检查产物**，没有一条检查**操控层本身**。
`guard_the_guards.py` 拦得住未授权改 skill，但一次**已授权**的修改把行为改差了，
没有任何东西会说话。

装了两条，分工不同，别混：

- **`check_config_integrity.py`** → 目标 `config-integrity`。测「配置有没有**坏**」：
  hook 指向的脚本在不在、目标写没写判定命令、自带 `--selftest` 的脚本自测过不过、
  skill 的 frontmatter 全不全、两个 settings 是不是合法 JSON。零成本，约 1 秒，每晚跑。
- **`run_config_evals.sh` + `check_config_evals_fresh.py`** → 目标 `config-evals-fresh`。
  测「配置**没坏**，但行为变差了」。用例在 `~/.claude/evals/cases/*.json`，
  每条 = 一个 prompt + 一组正则断言，`claude -p` 跑一遍机械判定。
  ⛔ **有意不用「让另一个模型判分」**：那会把不确定性引进闸门本身。

## ⛔ 三个把测试写坏的实例（写新用例前先读，这三种我都真踩了）

1. **断言分不清「使用」和「引用」**。测「不许用黑话」的用例，模型在**举例说明哪些词不该用**
   时提到了那些词，被判违规。→ prompt 要给足场景让它直接示范，别让它去谈论措辞本身。
2. **断言过度指定，钉在具体用词上**。要求出现「检查」二字，而回答写的是「自检模式」
   「判定命令」，语义完全对却被判红。→ ⭐ **断言要钉在「规矩失效时会消失的那个性质」上**，
   不要钉在某个词上。同一条规矩别写两条同义断言，那不是加强，是加倍的误判面。
3. **测试环境被当天状态污染**。headless 会话继承了开场注入常驻目标违规的 hook，
   注入内容随当天有哪些目标没达标而变，漏进回答里就让判定随环境漂移。
   → 修法：`run_config_evals.sh` 设 `CLAUDE_CONFIG_EVAL=1`，`goals_violations_hook.sh`
   见到它就闭嘴。**一个受当天环境影响的测试给不出稳定的红绿。**

## ⭐ 新鲜度检查为什么按内容指纹而不是文件时间

最自然的写法是「配置文件最新修改时间不得晚于最近一次全绿」。那样会**每晚误报一次**：
`verify_goals.sh` 每晚把 `status:` 与 `last-pass:` 回写进每个目标文件。
而一条天天无故变红的检查，两周内就会被当噪声忽略，那时它再也拦不住真问题。
所以算的是内容哈希，且读目标文件时剥掉那两个自动回写的字段。

## ⛔ cron 里必须用绝对路径（同日实踩，症状出现在别的检查里）

`live_windows.py` 里用裸命令名 `herdr`，cron 的 PATH 只有 `/usr/bin:/bin`，
找不到装在 `~/.local/bin` 的 herdr → 探测静默退化成「测不出来」→
**交接便条那道检查**把目录里 41 个文件（含 DISPATCH_/CLOSED_ 这些本来就不是便条的）
全判成便条逐个报错。⚠️ **根因在 A 脚本，症状在 B 检查**，这类跨脚本静默失效最难查。
凡是会被 cron 调用的脚本，外部命令一律绝对路径查找。

相关：[[anti-self-deception-protocols]]（机械检查必须反向验证会报红）、
[[promises-need-mechanisms]]、[[herdr-setup]]。
