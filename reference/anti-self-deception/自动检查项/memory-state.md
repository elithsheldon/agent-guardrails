---
name: memory-state
predicate: python3 /home/<user>/n-chang/.claude/scripts/check_memory_state.py
manual: false
status: VIOLATED
last-pass: 2026-08-31
---
memory 易腐状态检查 (2026-08-11 加)。事故: 一个教材战役的 memory 文件断言「已批准但
一次都没开跑」, 战役其实四天前就跑完了, 真状态只在 vault LEDGER 里; 会话读了就信,
向用户报了「正好轮到开跑」。当天更正了正文, 同一句假话却还留在该文件 frontmatter 的
`description:` 和 MEMORY.md 的索引行里 —— **状态事实存了三份, 更正只到了一份。**

管的那条线: **索引行与 description 是耐久文档, 只该说一个文件是关于什么的, 不该说
一个项目现在站在哪里。** 项目站位是易腐事实, 归各自的活单源 (vault LEDGER /
EXPERIMENT_PLAN / crontab -l / TODO.md)。同理 cron 行、tmux 窗口地址、会被官方改掉的
日期, 都别在散文里复述。

三类可机械证伪的矛盾 = ERROR, 直接决定退出码, 永不进 baseline:
E1 幽灵 cron (文档说某脚本在定时跑, `crontab -l` 里没有; 脚本名须与 cron 表达式相邻
≤40 字符才算受它管辖, 否则同行并列的无关脚本全成假阳性) · E2 索引行 ↔ description
状态互斥 (一处只说收官, 另一处说还在等用户拍板 = 更正只到了一份, 本次事故的指纹) ·
E3 截止日没说是谁的 (写了「截止+摘要/全文+日期」却不说是官方硬截止还是自定提前锚;
截止词/阶段词须在日期前后 40 字符内, 且「知识截止」这类非投稿义先抹掉)。

W 类 (状态词/cron/窗口地址/日期字面量) 走 baseline 增量制, 先例=check_bare_refs_delta:
存量冻结在 `goals/baselines/memory-state.txt` (2026-08-11 首次冻结 115 条), 只有【新增】
命中才 FAIL。处置新增命中 = 把状态从索引行/description 里删掉, 改成指向活单源的指针;
确属不朽事实 (立项日、已收官的 DONE、写清归属的两套截止日) 才手动追加进 baseline。
退出码 2 = 检查器自身跑不起来, verify_goals 记 CHECK-ERROR 与产物违规分开。
全库 142 索引行 + 428 description 跑 1.3s (远低于 verify_goals 的 60s 上限)。
2026-08-11 接停止门前实测: 三类 ERROR 全 OK、exit 0; `--selftest` 35 项全绿 (含
E1 相邻性两向+并列 cron 各归最近者、E3 归属两向 + 长行远距离共现/「知识截止」不误判)。
RED 实测: 把事故当天原文 (description「立项待批」+ 索引行「已批」+ 无归属的
「实际=9/11 abstract」+ overnight_agent.sh 的 cron 行) 灌进沙盒 → exit 1, E1/E3 各
点名一条、W1 抓出「已批」与「待批」两处 = 三份状态里的两份被独立抓到。
source: feedback_memory_capture_rules + feedback_memory_ref_audit (姊妹 goal=memory-refs,
那条管引用失效, 本条管状态失效)。
retire-when: 永不 (memory 体系换代时随之换代)。
