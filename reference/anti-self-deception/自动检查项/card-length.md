---
name: card-length
predicate: bash /home/<user>/n-chang/.claude/scripts/check_card_length_delta.sh /home/<user>/n-chang/.claude/goals/baselines/card-length.txt
manual: false
status: PASS
last-pass: 2026-09-11
---
论文卡零【新增】超硬线(1.5×家族 P75)。卡是给用户快速读论文用的笔记, 不是誊写;
判据与实测长度带单源=feedback_paper_card_is_for_fast_reading。计数口径: 剥 frontmatter、
剥围栏块、剥 `## Derivations` 附录(2026-08-11 用户裁定推导不计入)后按空白分词。
存量 3 张(DBC / Scalable Methods / Offline Primal-Dual)是装门当天既有的超长卡, 冻在
baselines/card-length.txt; 新增一律瘦身, 确有理由超带(说明这篇凭什么载荷更重+已砍了什么)才准追加 baseline。
retire-when: 永不 (核心纪律)。
