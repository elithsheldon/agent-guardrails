---
name: shelf-pairing
predicate: python3 /home/<user>/n-chang/.claude/scripts/check_shelf_pairing.py
manual: false
status: PASS
last-pass: 2026-09-11
---
书架两侧配对检查 (2026-08-15 加, 事故驱动): 抽取文本 `~/kb_tools/shelf_text/` 与原始 PDF
`~/Overleaf/Teaching/Textbooks/` 必须一一对应, 任一侧多出条目即报红。

**为什么需要它**: 那天用户上传一本 Sipser, 我核对了「与架上文本同为第三版 2012 Cengage」
就判成重复删掉 —— 而那是它**唯一一份 PDF**, 架上只有文本。本机无回收站, 不可恢复。
在此之前**两侧可以悄悄不一致而没有任何东西会发现**: 当时 131 份文本对 100 个 PDF,
31 本书只有文本。同伴会话也误以为两侧一致, 我照它的前提行动才出的事。

**为什么 PDF 那半不能少**: 抽取文本是定位用的, 它小写化、折叠空白、并且**丢公式**。
凡是要写进知识库页面的公式、定理陈述、符号定义, 都必须回 PDF 页面 (pdftoppm 转图像)
逐条抄。缺 PDF 的书遇到公式只能标注「未回原页核实」。

**报红后怎么办**: 本检查只报事实不做处置 —— 缺口该补书还是该删多余文件是用户的决定。
但**在补齐之前, 删任何一侧的文件都必须先确认另一侧还在**。
「有 PDF 但没抽文本」的补法: `~/miniforge3/envs/rl/bin/python3 ~/kb_tools/shelf_extract.py <pdf> <stem>`。

装上时已做反向验证: 临时移走一本的 PDF, 检查准确点名该书并以退出码 1 报红; 放回后转绿。
规则单源 = memory `feedback_shelf_first_concept_pages.md` 的「书架是两半」条。
