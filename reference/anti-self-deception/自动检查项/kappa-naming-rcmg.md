---
name: kappa-naming-<project-A>
predicate: bash /home/<user>/n-chang/.claude/scripts/check_kappa_naming.sh
manual: false
last-pass: 2026-09-11
---
(2026-08-05 复审判定=复活: 训练侧已收官, 按下方 RE-ENABLE-WHEN 预登记配方执行——
check_kappa_naming.sh 已加 baselines 排除行, RED 纪律三向验证过: 假 999 无 off 样本
FAIL / 删后清树 PASS / macpo coll999.0 基线不再假阳性。)
κ 命名规则常绿: 2026-07-13 18:00 之后启动的任何 <project-A> run, 目录名带 999 哨兵标签的必须带 off 后缀
(--kappa 0), 无例外——no_both/no_lagrangian 也不豁免 (2026-07-14 用户对 native probe 的裁定)。
判 run 启动时间用 config.json mtime, 老 run 一律豁免。
source: project_code_structure (κ 开关) + 2026-07-14 native probe κ 重发事件。
retire-when: <project-A> 项目收官, 或 train_exp.py 在 run_dir 层直接 assert 该规则后。

PAUSED 2026-07-19 (用户裁定「暂挂起该目标」): 谓词 glob 了 <project-A>/*/runs/* 把外部安全-MARL
基线 (macpo/mappolag, config 无 kappa 键, 999.0 = 基线自己的 cost-limit, 且在飞) 也捞进来,
60 个假阳性。这些算法根本没有 κ 机制, off≡--kappa 0 对它们不适用。用户选择暂挂 (manual:true
使 verify_goals 跳过) 而非当场收窄谓词, 等 RC-MAT 基线战役收官再统一处理。
RE-ENABLE-WHEN: baselines 战役收官后, 把 manual 改回 false 并在 check_kappa_naming.sh 加一行
`[[ "$d" == */baselines/runs/* ]] && continue` 排除无 κ 机制的外部基线, 再验证转绿。
