---
name: feedback_convergence_protocol
description: "In adversarial primal-dual runs, \"converged\" = tail-window statistics stationary (not flat curves); test drift-z before quoting endpoints; resume drifters"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c9eba5dd-9973-4243-8661-3d16069c0e76
---

In <project-A> chase/nav runs (adversarial zero-sum + primal-dual), curves NEVER flatten — the dynamics orbit (limit cycle). "Converged enough to compare" therefore means **the cycle's statistics are stationary**, not the iterate.

**Why:** User asked 2026-07-02 "很多runs都没有收敛啊 如何去比对 是否要继续训练" about the chase sweep. Quantified on the finished mu40 batch: c1 (binding) cells had λ still crawling at ep10000 (drift-z 1.1–1.6) — the dual outer loop (every-10-ep, α₀/√k decay) is SLOW at binding cells; endpoint numbers there would misquote.

**How to apply — the 3-rule protocol:**
1. **Stationarity test before quoting endpoints:** from the saved histories (cost*_hist/lam*_hist in results.json, or ckpt histories), split the tail (last half) into two windows; drift-z = |mean(w2)−mean(w1)| / pooled-std. z<0.5 stationary, 0.5–1 mild, >1 DRIFTING → resume (+~6000 ep) before using endpoint stats. train_chase.py `--resume <run>/models.pt --out <same dir>` restores nets/λ/lam_step; redirect to `train_resume.log` to preserve the original log.
2. **Compare via tail-window averages + multi-checkpoint eval, never single final snapshots** — on a limit cycle the endpoint depends on cycle phase; average the last-K-window (and/or eval several ckpt_ep*.pt) instead.
3. **Edge rules:** (a) μ=0 arms are EXPECTED to fail the test — non-stationarity IS their reported finding, don't chase convergence there; (b) if the cycle period approaches the window length, z misfires — sanity-check against history.png before acting; (c) STOP-LOSS: resume in +6000-ep blocks, at most TWO extensions; if z>1 persists, report "dual not stationary within budget" honestly instead of chasing forever.
4. **Equal-budget comparisons remain valid for STABILITY claims** (drift/oscillation IS the measured phenomenon, esp. μ=0 arms); extension is only needed for endpoint/performance tables. Report both, with the window documented.

**"Stationary" ≠ "training complete" (user probed 2026-07-02):** stationarity only says the process reached ITS asymptotic regime under this algorithm+schedule — it does NOT certify (a) the attractor is the GOOD one (a λ-pinned dead-policy basin is perfectly stationary — always check sat/goal/catch levels and both-agents-active separately), nor (b) absoluteness — the dual step decays as α₀/√k, so "stationary" is partly schedule-relative (a slow crawl under shrunken steps can pass the z-test). CONTROL EXPERIMENT launched 2026-07-02: mu40_c10_d10 (stationary verdict) resumed +6000 ep on ryugu — if its cycle stats move <~0.5σ, the metric is empirically validated; if they move, the test is schedule-fooled and thresholds need tightening. **RESULT (analyzed 2026-07-06): VALIDATED — all cycle stats (c1/c2/λ1/λ2/catch, last-2500ep windows pre vs post resume) moved z≤0.20 pre-σ (c̄1 13.8±25.6 → 9.9±17.2, λ̄1 1.72 → 1.83); the stationary verdict was not schedule-fooled. Caveat: results.json histories were OVERWRITTEN by the resume segment (600 pts = post only) — pre-resume stats must come from train.log parsing; keep train_resume.log separate as the protocol says.**

**Provenance (user asked 2026-07-02):** drift-z is MY ad-hoc assembly, not an established named metric. Nearest legitimate relative: the **Geweke (1992) MCMC convergence diagnostic** (two-window mean comparison with spectral/autocorrelation-corrected variance → calibrated z). My version deliberately uses the RAW tail std as denominator (≈ limit-cycle amplitude, so z = "drift in units of cycle amplitude") — physically right for the resume decision but NOT a calibrated statistic (thresholds 0.5/1.0 are judgment, autocorrelation uncorrected). FOR THE PAPER: report stationarity via proper Geweke diagnostics (statsmodels/pymc) — citable; keep drift-z as the internal resume trigger only.

Applied 2026-07-02: resumed mu40_{c1_d1, c1_d10, c1_d40, c40_d40} +6000 ep on ryugu. Pending: same test on mu10 batch when it lands (~19:20 UTC) and on the 30 E4 anchor runs when they finish (~Jul 4) — expect the c1-cell drifters there too. See [[project_rcmg_e4_chase_anchor]], [[feedback_equilibrium]].

**2026-09-02 追加（自审发现的稿子缺陷）**：<venue> 主线 app:convergence 曾按「意图中的流程」写成 s.e. 尺度门 +「所有 run 平稳才算完」+「绑定战场无一续训」；跑 `~/<project-A>/rcmat/stationarity_screen_audit.py` 后发现 RC-MAT 210 条引用 run 在 s.e. 尺度全不过、s.d. 尺度 173 条乘子被标（绝对位移 ≤0.13）、RC-MAT 根本没有 resume 通道（train_rcmat.py 只存策略+λ）。现行真相：本协议的 z（合并 s.d. 尺度）是**筛子**，只在有 resume 的池子（E4 chase / E5h tag / RC-HASAC）上触发续训；RC-MAT 固定 6000 集、靠尾窗读数判完。⛔ 写任何协议段落前先跑该审计脚本，数字从 `.out` 抄，不许按意图写。tag 侧同一统计量：发表 s3 与对照 s0–s3 也被标 → E-TAGEXT 续训（E5h/launch_tagext.sh，最多两段 3000 集）。
