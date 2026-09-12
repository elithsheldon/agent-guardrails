---
name: fix-known-defects-dont-defer
description: A defect I have already confirmed in a paper (wrong figure legend, wrong caption, wrong number) gets fixed in the same round; "needs a figure re-render" or "the paper is frozen" is not a reason to leave it and report it as pending
metadata:
  type: feedback
---

2026-09-10, candidate K: a reader test found Figure 3's legend missing entries for two plotted series (the confirmed-chaotic squares and the unconstrained level). I fixed nine text inconsistencies from the same report and wrote "not changed: Figure 3 legend, needs a figure re-render" in the record and the report. The user asked why a wrong figure was left in place ("图错了居然不改吗"). The fix took twenty minutes: edit the plotting script, regenerate, copy the PDF, adjust two captions, rebuild the supplement package, re-freeze.

**Why:** a confirmed defect in a submission is a defect regardless of which file it lives in. The effort of a figure re-render is small next to the cost of a reviewer seeing an unkeyed series, and a frozen paper is re-frozen after a fix the same way it is after a text fix. Deferring it also hides it: "left for later" items in reader-test records were not being picked up by anyone.

**How to apply:** when a reader, reviewer, or my own check confirms a defect (figure legend or axis, caption, number, label), fix it in the same round before reporting; the report says what was fixed. If a fix truly cannot be done now (data missing, needs a run), say so with the concrete blocker, not "needs a re-render" or "the paper is frozen". The same leftover existed in R: the freeze record listed "Figure 1 legend maxent -> maximum-entropy point (re-render)" as camera-ready backlog; it took fifteen minutes plus a package rebuild. Figure sources for K are ~/wild/n2_phase_diagram/figs/make_figs.py (copies into Overleaf figures/ and into the supplement are manual, and the supplement zip must be rebuilt and re-checked after a script change). Related: [[feedback_paper_artifact_hygiene]], [[feedback_package_review_once]].
