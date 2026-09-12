---
name: memory-refs
predicate: bash /home/<user>/n-chang/.claude/scripts/check_memory_refs.sh
manual: false
status: PASS
last-pass: 2026-09-11
---
memory 失效引用检查 (2026-07-15 加, 规则采自 Ctxlint/agnix 调研, 单源
feedback_memory_ref_audit.md): R1 局部 md 链接断链 / R2 goals predicate 脚本失踪 /
R3 正文 "bash ~/x.sh" 显式脚本调用失效 —— 三类 ERROR 计入退出码。
R4 (白名单根 ~ 路径 WARN) 与 R5 (悬空 wikilink INFO) 只报告, 归 /kb-audit 周巡检分诊;
wikilink 有意悬空 ("值得以后写") 是设计特性, 永不判死。
retire-when: memory 体系换代。
