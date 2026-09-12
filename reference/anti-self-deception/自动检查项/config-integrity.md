---
name: config-integrity
predicate: python3 /home/<user>/n-chang/.claude/scripts/check_config_integrity.py
manual: false
status: VIOLATED
last-pass: 2026-09-04
---
配置层完整性 (2026-08-26 加)。

**要解决的问题**: 已有的四十多个检查脚本和二十多条常驻目标, **全都在检查产物** ——
论文里的裸编号、知识库卡片长度、引用、交接便条。⛔ **没有一条在检查「操控层」本身**,
也就是 hooks / skills / goals / settings.json 这些决定 agent 怎么干活的东西。

空白的确切形状: `guard_the_guards.py` 拦得住**未授权**修改 scripts / goals / rules / settings
(⚠️ 2026-08-30 核对: skills 目录**不在**它的保护名单里, settings.json 里五个自建 skill 的 Edit
是用户明确放行的, 所以 SKILL.md 的改动只靠这条目标事后发现), 但一次**已授权**的修改
把某个 hook 的路径写错、或把某个脚本的自测跑坏, 没有任何东西会告诉你。
它不报错, 只是安静地不再生效 —— 这套体系最怕的就是这种失败。
同日的实例: herdr 状态栏那个仓库角标, 11 次调用 11 次超时、一次都没成功过,
而它照常显示着一个旧数字, 没有任何人发现。

**测四项** (全部零成本、约 1 秒、不调用模型):
① settings.json 里每条 hook 命令指向的脚本存在且可执行;
② 每条常驻目标写了判定命令 (没写 = 它永远不会被自动跑, 是个不报错的缺口);
③ 每个自带 `--selftest` 的脚本, 自测真的通过 —— **这项最值钱**, 因为规矩要求
   机械检查装上时必须反向验证「它真的会报红」, 自测就是那个反向验证的载体,
   自测坏了等于那道检查从此没有反向验证;
④ 每个 skill 有 SKILL.md 且 frontmatter 的 name/description 不为空;
   settings.json 与 settings.local.json 本身是合法 JSON。

**故意不测**: memory 引用链、以及「目标判定命令所引脚本是否存在」——
`check_memory_refs.sh` 的 R1/R2/R3 已经在做, 不重复造。脚本的自测里专门留了一条用例
把这个分工写成可执行断言 (期望「不报红」), 谁将来顺手把它加回来就会立刻发现重复。

**装上时的反向验证**: 七种情形逐一造出来跑过 —— 干净配置通过; hook 指向不存在的脚本、
settings.json 不是合法 JSON、脚本自测跑不过、skill 缺 description、目标没有判定命令
五种全部报红; 外加「目标引用不存在的脚本」一条断言它**不**报红 (归 R2 管)。
随后对真实配置跑一次: 12 处 hook 引用 / 26 条目标 / 9 个自测 / 16 个 skill, 全绿, 0.9 秒。

**报红后怎么办**: 修产物本身 —— 路径写错就改回来, 自测跑不过就去看那个脚本出了什么事。
⛔ 不要为了让它转绿而删掉某个脚本的 `--selftest` 分支, 那等于把「这道检查失去了反向验证」
这件事藏起来, 正是这条目标要防的。

retire-when: 配置层换代 (hooks/skills/goals 三者之一不再是文件形态)。
