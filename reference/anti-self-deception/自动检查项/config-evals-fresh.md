---
name: config-evals-fresh
predicate: python3 /home/<user>/n-chang/.claude/scripts/check_config_evals_fresh.py
manual: false
status: VIOLATED
last-pass: 2026-08-30
---
行为回归测试的新鲜度 (2026-08-26 加)。

**它和 config-integrity 测的不是一件事**: 那条测「配置有没有坏」(文件在不在、
自测过不过); 这条盯的是「配置**没坏**, 但一次合法修改把行为改差了」。
例子: 注入语言规则的那个 hook 还在、还能跑, 只是内容被改动后不再生效 ——
config-integrity 全绿, 而回答从此变成英文, 没有任何东西会报错。

**判据**: 把配置面 (skills 的 SKILL.md / scripts 的 .py .sh / goals 的 .md /
settings.json / settings.local.json) 的内容拼起来算一个指纹, 与
`~/.claude/evals/eval-ledger.tsv` 里最近一行「全绿」记录的指纹比对。不一致 = 报红。

⛔ **为什么按内容指纹而不是按文件修改时间**: verify_goals.sh 每晚把 `status:` 与
`last-pass:` 回写进每个目标文件, 按时间判会**每晚误报一次**; 而一条天天无故变红的
检查, 两周内就会被当噪声忽略, 那时它再也拦不住真正的问题。算指纹时那两个字段被剥掉。

**报红后怎么办**: `bash ~/.claude/scripts/run_config_evals.sh` (三条用例约两分钟,
每条开一个 headless 会话, 用 sonnet 档)。全绿后它会把新指纹写进台账, 这条自动转绿。
⛔ **不要为了转绿而删用例** —— 用例变少 = 覆盖变小, 而这条检查照样会绿, 那是自欺。

**用例在哪**: `~/.claude/evals/cases/*.json`。每条含 prompt 与一组正则断言, 判定是
纯机械的。⛔ 有意不用「让另一个模型判分」: 那会把不确定性引进闸门本身。
每条用例的 `why` 字段写明它守的是哪条规矩, 加新用例时照写。

**装上时的反向验证**: ① 判定逻辑自测三例 (满足全部断言→通过 / 缺必需内容→红 /
出现禁止内容→红) 全过; ② 真加了一条断言必然不成立的临时用例 `_redtest` 跑了一次,
确认报 FAIL、退出码 1、并如实记进台账, 跑完删除; ③ 指纹自测四例
(只改 status/last-pass→指纹不变 / 改 skill 正文→变 / 新增脚本→变 / 台账解析取到
最后一次全绿) 全过。

retire-when: 配置层不再是文件形态。

**⚠️ 这条绿意味着什么、不意味着什么（2026-08-27 自审后补）**：配置面指纹只覆盖
skills / scripts / goals / settings，**不覆盖 memory**。所以它绿只意味着「那个配置面没变过」,
⛔ **不意味着「影响行为的东西都没变过」** —— memory 里全是塑造行为的规矩，改一条完全可能
改变行为。memory 被排除的真实理由是它每天都在长、算进去会让这条天天变红，而一条天天无故
变红的检查两周内就会被当噪声忽略；⛔ 不是因为"改 memory 没风险"（早先的说法，已改口）。
**改了 memory 里的规矩之后想确认行为没变差，得自己手动跑一次 run_config_evals.sh。**
判据来自反自欺协议第 32 条 2026-08-27 补的第二问：不可伪造的量未必是你要问的那个量 ——
这里的量不可伪造，但它答的问题窄在 memory 上。
