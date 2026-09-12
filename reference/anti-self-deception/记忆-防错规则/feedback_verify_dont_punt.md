---
name: feedback_verify_dont_punt
description: "Verify source-checkable claims myself with web tools, don't hand them off"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e41f954e-5c99-4a11-81ab-ed0380689bd9
---

When auditing the notebooks (or any work) surfaces items that need an external source to confirm — a paper's exact equation, a venue/arXiv id, a headline number, whether a named method is really the paper's own — **look them up myself with WebSearch/WebFetch before reporting**. Do not list them as "verify this yourself" tasks for the user.

**Why:** 2026-06-29, after I deferred four such items, the user pushed back: "这几个你不能自己找到吗". I have web access; offloading verifiable lookups is lazy and wastes their time. (One deferred item — the LEO arXiv id — I had even mis-flagged as a "placeholder"; a 30-second lookup proved it valid. See [[project_paper_notes_forward_refs]].)

**How to apply:** parallel research agents (general-purpose / Explore, which have WebFetch+WebSearch), one per independent lookup; fetch ar5iv/arXiv for exact equations and numbers; only hand an item back if it is genuinely unverifiable from public sources (and say what I tried). Applies to all of [[project_paper_notes_repo]] and the <project-A> paper repos.
