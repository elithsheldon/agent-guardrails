---
name: feedback-zero-context-artifact-review
description: 对外产物（supplement zip/代码发布/arXiv 附件）上传前的零上下文独立合规审查法——用户指示记住、以后审别的也用
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6b6fd0c6-9bac-4103-ad60-14e04af01f50
  modified: 2026-08-21T20:49:31.792Z
---

# 零上下文产物合规审查法（2026-08-21 首用于候选 K supplement，用户令记住复用）

**方法**：派一个不带本会话任何背景的 general-purpose 独立 agent，只给它三样：产物文件路径、会议的合规规则（单 zip/尺寸上限/公开可见/匿名要求）、四维审查任务书。**不透露作者方任何内部结论**（比如"我们已扫过是干净的"），防止把它带偏成走过场。

四维任务书（照抄换路径即可）：
1. **匿名性**（最重）：文本内容+文件名/目录名+zip 条目元数据（注释/extra fields/UID）+二进制文件**解压后**的可打印字符串；每处命中要求给出上下文并判定真泄露还是字节巧合。
2. **自包含可用性**：README 逐句对照包内实际；依赖是否列全带版本；挑最小的入口脚本试运行（py_compile+短跑，禁长计算）；找"脚本引用了包里没有的文件"。
3. **卫生**：__pycache__/.DS_Store/.git/swap 文件/死链/零字节/嵌套 zip/尺寸超限。
4. **得体性**：凭据/API key、TODO/FIXME 带私货、无授权的第三方代码、读起来奇怪的内部代号。

要求输出：verdict 先行（SUBMIT-READY / FIX BEFORE SUBMIT）+ 每条发现分级（BLOCKER/WARN/NOTE）+ 文件路径行号级证据。

**Why**：自家审自家会被"已知干净"的记忆带偏；打包脚本的机械审计只查身份词表，查不出"README 声明与包内实际不符""分析脚本要读的文件没打包"这类使用性问题——而外部审稿人拿到包第一件事就是试跑。首用当场抓出 4 条属实的 WARN（缺分析输入文件、README 数据清单失实、依赖漏列 scipy/matplotlib 且无版本、取数目录名不匹配）。

**How to apply**：每篇稿的 supplement 上传前跑一次；代码正式发布、arXiv 附件同样适用。回报后守总控纪律（[[feedback-coordinator-verifies-subordinates]]）：**抽样核对它的关键主张再动手修**；修完重打包+重跑机械审计+独立关键词复扫+把它点名跑不通的脚本真的跑通一遍。装不下的大文件在 README 明写"未含+精确再生命令"，让声明与包内实际严格一致。

## 2026-09-04 判例：08-31 判 SHIP 的两个包，重审都是 FIX FIRST——审查任务书必须点名四类检查
**What happened**：O/Q/D 三包因图脚本变动重建后再派零上下文审查。D 的包里 28 个结果 JSON 带真实主机名（`"host": "kawahagi"/"katsuo"`，训练脚本早期未做进程伪装时写的）、142 个隐藏的调度哨兵文件（`.review_mail_sentinel`、`.brfired_*` 等，名字暴露审稿轮次和邮件通知）、README 命令缺必填参数；O 的包里一个脚本缺 `import os` 直接崩、run-1 数据没随包、README 工作目录前后矛盾、13 处脱敏后留下的半句话；Q 的包 README 与脚本行为不符 8 处。08-31 的四维审查全判了 SHIP，因为那次审查只读了 README 和抽样脚本，没有 grep JSON 值、没有列隐藏文件、没有跑 README 里的每条命令。
**How to apply**：派零上下文审查时任务书明写四件事：①对全部 JSON/JSONL 的字符串值 grep 主机名/路径/用户名（键名如 host、cwd、argv、out）；②`unzip -l | grep "/\."` 列出所有隐藏文件并逐个判用途；③README 列出的每条命令从声明的工作目录实际跑一遍（含 --selftest）；④脱敏后的 docstring 逐句读是否成句。⭐ 训练脚本写 host 字段的项目，进程伪装之前跑的早期结果文件一律要在打包时改写该字段。⑤包里只许 .py/.json/.jsonl/.md/.txt/.npz 这类白名单后缀，其余一律拒绝——O 的旧包随了 37 个 `__pycache__/*.pyc`（构建脚本的 py_compile 步骤写的），.pyc 里嵌着绝对构建路径和用户名，纯文本审查看不见；语法检查用 `ast.parse`，不用 py_compile。

## 2026-09-05 判例：D 稿 09-04 那版包里仍有 28 个结果文件带真实主机名（kawahagi、katsuo）和 144 个隐藏的调度哨兵文件，扫描器报 CLEAN
原因：`~/anon_release/configs/adversarial_qrl.json` 的改写表和 `wordlist.txt` 都没收这两台机器的名字，扫描器只认词表；09-04 的复查也没按「grep 全部 JSON 字符串值」做。这次做包升级时分支自己 grep 了 `"host"` 字段的全部取值才发现。
**Why:** 词表是白名单式的，漏一个名字就整包放行；「CLEAN」只说明词表里的词没出现。
**How to apply:** 每次打包后固定跑 `grep -rhoI '"host": *"[^"]*"' <包目录> | sort -u`，取值只允许一个通用词；`wordlist.txt` 必须含 FLEET 里全部主机名（对着 `~/.claude/projects/-home-mil-n-chang/memory/project_multihost_dispatch.md` 的机器清单核一遍）；隐藏文件用 `**/.*` 一律排除，不逐个判。已写进 `~/anon_release/PIPELINE.md`。

## 09-05 判例：结果文件按修改时间选副本的脚本，打包后会翻转（D 稿第三次包审）
- 现象：八个判定脚本用 `os.path.getmtime` 挑「先完成的副本」；打包器改写主机名时重写了 2,467 个文件，修改时间全被重置成打包时刻，zip 里的条目也就只剩一个时间。解压后并列，判定按解压顺序翻转，两个已发布的判定输出无法复现。之前记的「用 unzip 别用 cp」只是碰巧：09:34 那版 zip 同样丢了时间，只是解压顺序恰好一致。
- 修法（已在 make_release.py 和 a48_common.py 里）：① 任何按时间判定的脚本改成读包内记录的时间清单（这里是 a48_index.json），文件系统只作无记录时的回退；② 打包器改写文件后用 `os.utime` 恢复源文件的修改时间，zip 条目带真实日期；③ 复核任务书里加一条检查：解压后 `touch` 全部结果文件再跑判定脚本，输出必须逐字节相同。
- 顺带的规矩：打包器改写阶段之后再跑一次「重新生成的报告 vs 源树报告」比对，差异行要么解释、要么修。

## 2026-09-09 用户裁定：一个包只审一次，重建后不再派独立审查
用户原话：「重建之后不用上下文审查啊」。
**规则**：零上下文四维审查在一篇稿的包**第一次组装完成时跑一次**（或用户点名再跑）。之后因为加脚本、加数据、改 README、表号变动而做的重建，不再派独立 agent 审，改由打包脚本的机械审计加总控自己的固定四项检查覆盖：① `unzip -l | grep "/\."` 无隐藏文件；② 对全部 JSON 字符串值 grep 主机名/路径/用户名，取值只许通用词；③ `ast.parse` 过全部 .py；④ 在 fuka 上跑一遍 smoke.sh 和新加的分析脚本。这四项自己跑、结果写进包重建记录（各仓 PACKAGE_REBUILD_*.md），不派人。
**Why**：独立审查每次要几十万 token，而重建只改增量；首次审查已经把 README 声明与包内实际、隐藏文件、主机名这几类问题查过，增量部分用固定检查就够。
**How to apply**：paper-freeze 第 6 步的「包成后零上下文四维审」只在首版包做；重建走上面四项。判例：候选 Q 09-06 首版包审过（FIX FIRST，六处 README 错处已修），09-07 之后的重建不再审。
