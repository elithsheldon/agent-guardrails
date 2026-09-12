---
name: paper-products
predicate: /home/<user>/n-chang/miniforge3/bin/python3 /home/<user>/n-chang/.claude/scripts/check_paper_products.py --baseline /home/<user>/n-chang/.claude/goals/baselines/paper-products.txt
manual: false
status: PASS
last-pass: 2026-09-11
---
读一篇论文的四产物零【新增】缺口。本门是 check_paper_queue.py 的反方向：那边从队列走向产物
(☑ 行必须有卡有 digest), 本门从产物走回队列 —— 每张 vault 卡必须有 digest、有 ☑ 行、有 Zotero
条目, 每个 digest 必须有卡有 ☑ 行。它守的是「☑ 真的是最后一步」这条断言, 而这条断言正是
「读到一半中断可以直接扔掉」的全部依据: 顺序成立则中断只留完整论文 + 未动的行, 没有半成品。
存量 85 条(卡无 digest 40 / 卡无 ☑ 行 3 / digest 无 ☑ 行 6 / 无 Zotero 条目 36)是装门当天既有的
历史债, 冻在 baselines/paper-products.txt: 40 里 39 条来自 2026-07-17 两个 ultracode 批次(basic
21 + 阶段2 18)当时就定的「只建卡不写 digest」, 另一条是 Beta-VAE 薄卡。新增一律补齐缺的那件产物,
确属有意只建卡(如 basic 伴读卡)才准把签名行追加进 baseline 并写明理由。
Zotero 侧走全库缓存 (scripts/.paper_products_zotero.json, 627 条), 只在缺缓存或 --refresh-zotero
时拉一次, 缓存年龄逐次打印、超 45 天报 ZOTERO-CACHE-STALE; 断网且无缓存则跳过该节不判 FAIL。
source: reference_zotero_api (凭证与调用) + feedback_skill_notion_kb (四产物顺序)。
retire-when: 永不 (核心纪律)。
