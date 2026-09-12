---
name: claims-<venue>
predicate: /home/<user>/n-chang/miniforge3/envs/rl/bin/python3 /home/<user>/n-chang/.claude/scripts/check_claims.py /home/<user>/n-chang/Overleaf/RCMG_ICLR2027/claims.yml
manual: false
status: PASS
last-pass: 2026-09-11
---
ICLR 稿 claims 台账 anti-leakage 契约 (2026-07-15 采自 ai-research-skills, 单源
reference_awesome_claude_code.md + 台账文件头注释): 75 条 claim 逐字对稿, 无证据
只能标 gap/rejected, supported 必须挂 >=1 个存在的证据路径 (图源/实验目录/代码)。
改稿时同步维护 claims.yml: 新增断言加条目, 删除的翻 rejected 不删行 (审计尾迹),
数字改动更新 text 为新 verbatim。prose 纪律: 非 supported 的 claim 禁配
shows/demonstrates 类直陈动词。
retire-when: <venue> 稿终审后归档。
