---
name: feedback-random-order-hash-seed
description: 随机流程若在 set/dict 上迭代后再抽样，结果随 Python 哈希种子变；候选列表先 sorted，且随机流程的结论按多种子报区间
metadata:
  type: feedback
---

随机流程（随机打破并列、随机剥离、随机子集）在 `set` 或 `dict` 上迭代后再 `rng.choice`，哪怕 numpy 种子固定，结果也随 Python 进程的哈希种子变（字符串哈希每个进程不同）。2026-09-09 候选 R 的替代池脚本就是这样：论文里那段「只有一个池是线段」是某一次哈希种子的抽样，换种子 0–4 个线段都有；零上下文包复查跑了两遍才发现。

**Why:** 论文把单次抽样写成结论，读者复现得到不同答案，等于报了假结果。

**How to apply:** 任何用 rng 从集合里挑元素的地方，候选列表先 `sorted(...)`；随机流程的结论按多个种子报区间（本例改成十个流各二十次，报「13/222 个池是线段」和逐流计数）；包审查时同一脚本用两个不同 `PYTHONHASHSEED` 各跑一次比对输出。相关：[[feedback-record-experiments]]、[[feedback-zero-context-artifact-review]]。
