---
name: bash-safety-guard
description: PreToolUse(Bash) 破坏性命令拦截 hook——bash_safety_guard.py 的规则清单、deny/ask 分级、设计取舍（为何不装 cc-safety-net）；执行保证第七级
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 678f8822-6656-4c1a-b648-40385b2b78f0
  modified: 2026-08-05T02:29:30.205Z
---

**脚本**：`~/.claude/scripts/bash_safety_guard.py`（PreToolUse matcher=Bash；输出 stdout JSON permissionDecision）。**状态：2026-07-15 用户拍板后已挂进 ~/.claude/settings.json 并实弹验证生效**（无害 Zotero DELETE 探测被正确 deny，放行路径正常，审计日志 `~/.claude/safety_guard.log` 落账）。执行保证第七级。

**Why**：大量自治会话/headless cron 跑在共享服务器上；Zotero DELETE 永久删、NFS home 一损俱损（⚠️ 原来还有一条「~/<project-A> 无 git 史」，2026-08-26 建库后不再成立；但版本库只护住了收进去的那 145 MB，51+61 GB 的实验产物依旧没有任何兜底）。调研结论（2026-07-15，[[awesome-claude-code-survey]]）：不装 cc-safety-net 原工具——它默认拦 git restore/stash drop 等日常操作，且 rm"cwd 内放行"恰好漏掉 ~/<project-A>。

**How to apply**（规则单源=脚本本体，此处记分级逻辑）：
- **deny（硬拦，零正常用例）**：rm -rf 指向 /、$HOME、~/<project-A>|~/Overleaf|~/.claude 顶层、Overleaf 单仓、<project-A> E* 实验夹/两个核心 .py；任意 rm 指向 memory/goals/scripts/rules/settings 树；Zotero API DELETE；crontab -r；Overleaf 仓内 git push --force（--force-with-lease 放行）；顶层 dd of=/dev|mkfs|shred；find 保护树 -delete。
- **ask（交互确认=放行一次；headless 无人应答=自动拒，正好自治从严）**：Overleaf 仓内 reset --hard / clean -f（-n 放行）/ checkout -- / restore（--staged 放行）；rm -rf 变量目标（非 tmp/scratchpad）；xargs rm -rf；解释器代码内 rmtree 且提及保护路径。
- **设计原则**：宁缺勿滥（更深层 rm 放行，prune_runs.sh 不受影响）；fail-open（guard 自身异常=放行+日志 `~/.claude/safety_guard.log`，别让守门人变路障——与停止门的 fail-closed 相反，因为这是安全网不是正确性门）；按 `;&&||` 切段逐段判、"递归∧强制"同时成立才判 rm 目标（两条抄 cc-safety-net）。
- 已知绕过面（继承原工具，接受）：eval "…"、先写脚本再执行、变量命令头。定位=防事故安全网，不是防恶意边界。
- **2026-07-22 硬化（采自 ECC 补扫，GHSA-4v57-ph3x-gf55 同类）**：①引号包命令名绕过（`"r"m`/`'d'd`）已堵——前置 regex 检查全走去引号副本，shlex 解析失败的 fallback 也去引号分词（实测双样例拦住）；②ask 档文案改三问式（列将删对象/一行回滚/逐字引用用户指令——索要调查产物而非口头确认，采自 ECC gateguard-fact-force）；③`--no-verify`/`core.hooksPath` 拦截**判不采**：各仓无 git hooks，拦不存在的事故违背宁缺勿滥。
- **姊妹件 guard_the_guards.py（同日挂，PreToolUse Edit|Write|MultiEdit）**：编辑命中 ~/.claude/{scripts,goals,rules}/、settings.json、vault check_links.py → ask「修产物不改判卷人」——防「为让检查通过而弱化护栏」，采自 ECC config-protection；共用 safety_guard.log。
- **2026-08-05 晚 mktemp 窄豁免（Compost 提案三，用户签字；七路回归全过）**：`rm -rf $T` 若 `T` 在**同一命令串**由 `$(mktemp` 赋值 → 放行＋append-only 记账（decision=allow-mktemp）。豁免刻意窄：只认字面同串赋值的**裸变量**——带子路径（`$d/.claude`）、跨命令、借名（赋了 T 删别的变量）全部维持 ask 从严。治的是 headless 下合法临时目录清理被自动拒。
- **2026-08-05 两改（LongHorizon 收割件 4，台账 [[paper-skill-survey]]；deny/ask/allow/fail-open 四路回归全过）**：①记账行补 `ts`（UTC）+`cwd`——日志从「拦了什么」升级为可对账时间线（配套协议=[[anti-self-deception]] 规则 14「声称删了要 diff 证实」）；②**修存量真 bug**：`git -C <Overleaf仓> reset --hard` 曾静默溜过——子命令探测把 `-C` 的路径参数误当子命令（回归坏样本抓到）；修后 `-C` 形式与 cwd 形式同判 ask，force-push `-C` 形式同判 deny。
