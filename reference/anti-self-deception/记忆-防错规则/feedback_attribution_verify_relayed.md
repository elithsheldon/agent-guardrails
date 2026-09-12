---
name: attribution-verify-relayed
description: 读论文窗口转述来的「谁提出/谁证明」归属结论一律回原文抽查原话再落稿；同一句上连错两次的判例（LLL 1993 复合一致性）
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 95a602c5-7dda-482e-b710-bcfa6e1a4036
  modified: 2026-09-03T05:49:51.621Z
---

# 归属类转述必须回原文抽查

2026-09-03 候选 R 相关工作里「复合一致性」一句，读论文窗口（r-reads）连给两次错误指引：第一次把复制说成复合的特例（它自己的知识库页面第 76 行写着两者在锦标赛类不相交），第二次把定义归给 Laffond–Lainé–Laslier 1996（原文 Definition 4 与 Proposition 6 都在 Laffond–Laslier–Le Breton 1993）。两次的共同原因都是拿题名和转述当证据、没回原文。我照单改了两次，第二次还把 1993 整个从句子里拿掉，引入了新的归属错误。

**Why:** 归属错误是审稿人一眼能抓的硬伤，且改错比不改更糟；转述链每多一环，「没标出处」就越容易被读成「就是源头」。

**How to apply:**
- 任何「X 提出/证明/首次」类结论，落稿前自己打开原文（或 OCR 文本）找到定义编号/命题编号/原话，稿内引用带编号（如 `\citet[Definition~4]{...}`）。
- 不写「proposed by / first」除非有证据；原文未挂引用不等于源头（可能引未刊工作论文）。
- 没人读过原文的文献只作 see-also，不描述其适用范围。
- 无文字层的 PDF 用 OCR 文本查，`grep` 零命中不能当作「没有」（见 [[never-truncate-before-negative-conclusion]]）。
- 同一句被更正后再改时，先读现行句子全文，只改被指出的那一处，别顺手删掉未被质疑的引用。
- 转述里的指代词（「那个变体」「该性质」「这条结论」「this variant」）落稿前一律换成具体对象名；换不出来就退回去问，不落稿。判例：Berker 2025 第 9 页脚注的「this variant」是随机混合规则，不是满足复合一致性的 RP_i——我核了原话在页上却没追先行词，照样写错。核原话≠核先行词。
