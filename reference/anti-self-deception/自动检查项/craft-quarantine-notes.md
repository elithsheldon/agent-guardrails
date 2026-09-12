---
name: craft-quarantine-notes
predicate: bash -c "! grep -rliE 'writing[[:space:]_-]?craft' /home/<user>/n-chang/Overleaf/Paper_Notes /home/<user>/n-chang/Overleaf/RL_Note --include='*.tex'"
manual: false
status: PASS
last-pass: 2026-09-11
---
writing-craft/手法点评是元知识, 只进 memory/feedback_skill_paper_writing.md 原则 6「手法层收割」, 绝不出现在两本笔记的 .tex 里 (2026-07-12 Opus 把 \paragraph{Writing craft} 写进 Paper_Notes 4 篇小节, 用户纠正后撤, commit 842ebd0)。
第一道防线 = PreToolUse hook craft_tex_guard.py (写入时拦); 本谓词是每日兜底 (防 bash/sed 绕过 hook 写入)。
source: feedback_skill_paper_notes 债务战役 bullet + feedback_skill_paper_writing 原则 6。
retire-when: 两仓归档。
