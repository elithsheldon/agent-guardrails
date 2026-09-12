---
name: no-expand-ratification
predicate: bash -c "! grep -rn 'no-expand' --include='*.tex' /home/<user>/n-chang/Overleaf/Paper_Notes /home/<user>/n-chang/Overleaf/RL_Note | grep -v 'no-expand(ok'"
manual: false
status: PASS
last-pass: 2026-09-11
---
no-expand 豁免的人工批准闸 (2026-07-12 用户拍板立规)。背景: 债务战役中模型一天自授 19 个
% no-expand (写内容与发豁免同一 agent = 自我认证), 结构上重演 07-12 被撤 11/12 的批发模式;
本批 19 个用户已批准, 与存量 4 个一并打 (ok 2026-07-12) 戳。
规则: 模型新发的 % no-expand 一律裸写 (provisional); 只有用户审过后改成
% no-expand(ok YYYY-MM-DD): 才算转正。本谓词抓一切未转正标记 → FAIL → 开场 hook 提醒用户批。
豁免的抑制作用 (check_latex 疑似过短/WEEKMEAN) 对 provisional 仍生效, 闸门只管"必须过人"。
source: feedback_skill_paper_notes 债务战役 bullet + check_latex.sh 未批准豁免提示节。
retire-when: 两仓归档。
