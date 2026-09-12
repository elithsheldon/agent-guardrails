---
name: pdf-text-layer-traps
description: PDF 文字层会静默改写内容的两类陷阱——连字/变音符折叠（只造成漏命中）与「≠」被压成「=」（把数学命题反过来而句子仍通顺）。凡从文字层读到的不等号、否定、符号，落笔前必须回渲染页确认
metadata: 
  node_type: memory
  type: reference
  originSessionId: b618ba61-dc6a-4438-a4f5-1b67cc33602f
  modified: 2026-09-03T14:27:09.692Z
---

从 PDF 抽出来的文字**不是页面上印的东西**。已实测两类改写，危险程度差一个量级，处理方式也不同。

## 一、连字与变音符被折叠 —— 只造成**漏命中**

裸搜 `efficien` 在某份抽取文本上返回 0，规范化之后返回 4：排版里的 `fi` 是**一个连字字符**，抽出来根本不是那两个字节。同理 `Buchi` 搜不到任何 `Büchi`。射程包括 efficient / different / sufficient / coefficient / first / final / flow 这类常用词，而它们正是判「这篇谈没谈效率、谈没谈流量」时会用的词。

**修法（别自己写替换表，现成的已踩过一次坑）**：

```python
import sys; sys.path.insert(0, '/home/<user>/n-chang/kb_tools')
from shelf_probe import unligature      # 连字 + 变音符，一次折完
text = unligature(open(pdf_txt, errors='ignore').read())
```

⚠️ 书架文本（`~/kb_tools/shelf_text/`）走 `shelf_probe.py` 时已经折过，不必再折；要折的是**自己刚从 PDF 抽出来的那一份**。
⚠️ 反向代价：`unligature` **会把重音符也折掉**，所以**人名不能从规范化后的文本里取**——从未规范化的抽取里取，或回渲染页看。判例：某篇作者是 Emmanuel J. Candès，规范化后成了 Candes，直接进文献库条目就把人名写错了。

## 二、⛔⛔ 「≠」被压成「=」 —— 把命题**反过来**，而句子仍然通顺

2026-09-03 实测（某统计期刊的官方 PDF，pypdf 抽取）：论文原文写的是「当 **f_K ≠ 0** 时可以用插值估计……」，抽出来是 `f_K = 0`。

**为什么这条比第一类危险得多**：
- 第一类的症状是「搜不到」，会引起怀疑；这一类**读起来完全正常**。
- 而且它**与紧接的上一句直接矛盾**（上一句说 f_K = 0 时覆盖已近乎精确），于是最自然的结论是「论文这里写错了」——**差一步就把一个不存在的笔误当作缺陷写进知识库**。
- 一旦写成「论文这里有笔误」，那是对作者的事实指控，而且没有任何自动检查会发现它是假的。

**规则**：⭐ **凡从文字层读到的不等号、否定、符号（≠ ≤ ≥ ± ∓ 上下标 撇号），落笔前必须回渲染页亲眼确认**。

```bash
pdftoppm -f <页> -l <页> -r 300 -png <pdf> /tmp/pref      # 再用 Read 打开 PNG
# 只要某一段：-y <上边距> -H <高度> 裁出来，省读入
```

## 判据（两类共通）

⭐ **文字层是定位工具，不是权威。** 用它找位置、做检索、算词频；凡要**落笔断言论文说了什么**，尤其是断言论文错了，一律回图像。

这与 MinerU 那条的边界是同一条原则的两个应用面——[[mineru-ocr-probe]] 记的是「MinerU 的错误模式是错得很像对的，所以不能替代图像权威做单源」，本文件记的是**连出版方自己的 PDF 文字层也有这个毛病**，不必是 OCR 或扫描件。另见 [[feedback_never_truncate_before_negative_conclusion]]（要下否定结论的检索不许截断）与 [[anti-self-deception]]（阳性对照纪律）。
