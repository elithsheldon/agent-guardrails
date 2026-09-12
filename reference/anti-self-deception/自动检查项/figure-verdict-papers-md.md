---
name: figure-verdict-papers-md
predicate: bash /home/<user>/n-chang/.claude/scripts/check_figure_verdict.sh
manual: false
status: PASS
last-pass: 2026-09-11
---
插图义务门 (2026-07-11 插图断供审计后加: 23 页零图事故): 讲解日期 >= 2026-07-08 的 papers/<slug>.md 必须有「- **插图**:」判定行 (配图记录 或 免图+理由)。
建页时判据是义务门不是许可门; 图随 create-pages 同批发 (事后 update_content 插图=二等路径, 且插后必须 fetch 验证 image 块成立)。
source: project_notion_paper_sync A.5 + papers/INDEX.md CHECKPOINT 2026-07-11d + /paper-read SKILL 硬门槛 8。
retire-when: 永不。

⚠️ 2026-08-15 修：卡片格式把日期字段从「讲解日期」改名为「读的日期」，而本门只认旧名，于是当天新写的 8 张卡被**静默跳过**——门照样 exit 0，从输出看不出它失明了。现在两种字段名都认（覆盖 360 → 368 张），并且「一个日期字段都没有」不再静默 continue：无日期且无插图判定行会显式报告，因为「合规的卡」和「本门管不到的卡」必须能分辨。全大写文件名（ZOTERO_MISSING.md 等）是台账不是卡，已排除。改后跑过八例沙箱自测：旧字段缺行、新字段缺行、无日期无判定行三例被抓，两例合规、截止日之前一例、台账一例正确放行。
