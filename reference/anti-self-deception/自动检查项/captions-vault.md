---
name: captions-vault
predicate: python3 /home/<user>/n-chang/ObsidianVault/_meta/scripts/check_captions.py --strict
manual: false
status: PASS
last-pass: 2026-09-11
---
Obsidian vault 每个 tikz 图块下面挂且只挂一条格式正确的 caption (CONVENTIONS
Diagrams 节): 位置固定在收尾 ``` 的下一行、上下各一空行, 房规写法是 "> " 开头的
单行 markdown 引用块。位置即身份 —— 占着那一行的 >[!callout] 不算 caption;
caption 是 markdown+Obsidian MathJax 不是 tikz, \small \\ \emph \textbf
\mathbb{1} 一律不许进; 按句子排版 (首字母大写、句号收尾、约 15-40 词)。
--strict = 缺失或畸形一律判失败 (另有 --report 模式只统计不判, 回填期间用)。
能测的只有形式: 真正要命的「caption 说出标签说不出的东西」得靠人读图读上下文,
这门全绿只代表格式对, 不代表值得读。
2026-08-11 接停止门前实测: 全库 1416 个 tikz 块全部有 caption, exit 0 CLEAN;
沙箱里在 caption 位置放一行散文后 exit 1; --selftest (八类缺陷逐一) CLEAN;
全库跑 0.7s。
source: project_obsidian_vault + feedback_tikz_label_style (CONVENTIONS Diagrams 节)。
retire-when: 永不 (vault 核心纪律)。
