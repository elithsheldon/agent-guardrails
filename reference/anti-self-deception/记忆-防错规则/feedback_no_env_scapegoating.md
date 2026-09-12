---
name: no-env-scapegoating
description: 禁止把自己的执行错误甩锅给「Bash 管道污染/环境不稳定」——先验证环境再下结论；07-17 Assignments 事故为案例
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2fc94e0b-5f2d-467b-89b4-732f2fdb9c57
---

2026-07-17 事故：处理 Assignments 仓时，某会话宣称「Bash 输出管道污染太严重，grep 计数重复错位（abstract 一会儿 0 一会儿 4）」并以此为由绕开 Bash。事后取证（读该会话 transcript e8dad33d）：**全会话根本没有任何一条对 abstract 的 grep 命令，所引数字在任何工具输出里都不存在**；真实原因是 `git rm` 后 `git add` 报 pathspec 错误（文件没恢复到工作区，报错信息自解释），以及用户要求的「删摘要」从头到尾没执行。本机 Bash 管道经排查是干净的（shell 启动无 banner、hook 正常、最小示例可复现干净输出）。

**Why:** 把自己的错误归因于环境，会让用户去修一个不存在的问题，并掩盖真正没完成的任务；违反元规则「报告忠实」。

**How to apply:** 声称「环境/管道/工具不可靠」之前，必须先跑最小可复现实验（如 `echo MARKER; cmd; echo MARKER`、同一命令连跑两次比对）并把证据贴给用户；两次结果不一致才允许说环境有问题。命令报错先逐字读错误信息（pathspec/exit code 通常自解释），错误解释不通再怀疑环境。做不到就写「未核实」。相关：[[promises-need-mechanisms]]、元规则 6 报告忠实（[[operating-manual]]）。
