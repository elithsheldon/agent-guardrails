---
name: record-experiments
description: "Always record experiment parameters, directional decisions, and results in memory immediately — git now tracks the code, but not the decisions"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c4a21a20-0fb1-4adc-8a66-4513997956b6
---

Always record the following in memory after running or interpreting experiments in `~/<project-A>`:
1. **Parameter configuration** used (nature_budget, balan, f1/f2 or manual con, lam_max, n_ep)
2. **Directional decisions** — e.g. "nature is adversarial (no negative sign)", "Bellman targets are separated", "calibrated constraints enabled"
3. **What was tried and failed** — include why it failed (bad basin, constraint violated, catch=0, etc.)
4. **Final outcome per run** — c1, c2, λ1, λ2, catch_last, whether constraints were satisfied

**Why:** ⭐ 2026-08-26 起 `~/<project-A>` 与 `~/offline_rcmg` **都有 git 了**（用户当天下令建的），但**这条规矩不因此作废，理由变了而已**：git 记的是代码怎么变的，记不了「为什么这么定」「这次跑出来说明了什么」「下一步方向」——那些从来不在 diff 里。本条原来的理由是「完全没有任何记录」，现在的理由是「有代码史，仍然没有决策史」。
  历史背景（原文保留）：`~/<project-A>` had no git history. Without memory, design decisions and bug fixes get lost between sessions. This happened concretely: the nature sign was fixed in April (before `rcmg_results_wall/`), but the fix was not recorded → a later session re-introduced the bug → the bug had to be found and fixed again in June 2026.

**How to apply:** At the end of any session where (a) algorithm code changed, (b) new experiments were run, or (c) a parameter turned out good/bad — write or update a project memory before closing. Do not wait until next session to record results.
