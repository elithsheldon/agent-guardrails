---
name: links-vault
predicate: python3 /home/<user>/n-chang/ObsidianVault/_meta/scripts/check_links.py
manual: false
status: PASS
last-pass: 2026-09-11
---
Obsidian vault 结构不变量, 13 项一次跑完: 悬空 wikilink / 孤立页 / CJK 混入 /
taxonomy 游离文件 / Obsidian-MathJax 不支持的宏 (\mathds \textsc \mathscr \bm, 在
Obsidian 里渲成红色 undefined-macro 而 check_mathjax 全盲) / 数学区里的 \* /
退役散度拼写 (房规=黑板体载体 + 直立下标, 单源 Notation.md) / 书号 \tag{x.y} /
文件名 wikilink 破坏字符 / 大小写不敏感 stem 撞名 / section·block 锚点存在性 /
散文中段硬折行 / tikz 标签样式 bug (裸色吞 fill、标签加白底)。
谓词不带参数 = --vault 默认取仓根, 全库 2084 页跑 4.5s (远低于 verify_goals 的 60s)。
2026-08-10 接停止门前实测: 全库 exit 0 CLEAN; 沙箱注入一条悬空 wikilink 后 exit 1;
--selftest (散度门 fires / does-not-fire 两向) CLEAN。
source: project_obsidian_vault + feedback_vault_mathjax_render + feedback_tikz_label_style。
retire-when: 永不 (vault 核心纪律)。
