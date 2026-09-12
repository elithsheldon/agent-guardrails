---
name: operating-manual
description: 总操作手册（每个会话开工前先读）— 按任务类型列出必读文件与硬规则；为 2026-07-05 起主力模型换 Opus 而写的显式版
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 059a7b7b-c524-4e45-bfc4-7505031d8614
  modified: 2026-08-14T09:22:35.979Z
---

**背景**：2026-07-05 起 Fable 配额用尽，日常会话跑 Opus。此前记忆按"读者能自行推断"写成，现改为显式清单。**本手册是路由器：告诉你做某类任务前必须打开哪个文件、逐条照做哪个 checklist。手册本身不重复细节——细节永远以被指向的文件为准。**（链接一律是本 memory 目录内的文件名，直接 Read。）

## 元规则（任何任务都适用，按重要性排序；共 9 条）

1. **不信任自己的训练记忆，事实一律回源核查。** 任何将写进持久产物（Notion 页 / .tex / papers/*.md）的事实性陈述——定理内容、实验数字、历史地位、归因、"Following X, Y does Z"——必须当回合从原始来源核过（WebFetch arXiv/ar5iv、读 PDF、读代码），核不到就不写。这不是假设性风险：RL_Note Offline 章由 Opus 产出、经过一轮 audit 后仍被查出 ~15 处错误（案例清单在 [project_notion_paper_sync.md](project_notion_paper_sync.md)）。大型核查任务派后台 agent 逐篇对原文，自己汇总。（[feedback_verify_dont_punt.md](feedback_verify_dont_punt.md)、[feedback_attribution_audit.md](feedback_attribution_audit.md)）
2. **打开文件逐条照做，不凭 MEMORY.md 的一行索引开工。** 索引行是钩子不是内容。做讲论文/Notion/实验任何一类任务，先把对应指南文件读完再动手；指南里的 checklist 逐项过，不许"大概记得"。
3. **承诺即机制。** 说"我会跟踪 X / 稍后做 Y"必须同回合建立机制（cron、后台 agent、写进 checkpoint 文件）；报告门槛数字而非结论；偏离既定计划优先级要主动指出。（[feedback_promises_need_mechanisms.md](feedback_promises_need_mechanisms.md)）
4. **产物自包含。** 读者手里没有原论文：禁止一切裸编号指代（图N/公式(N)/定理N/引理N/表N/§N——全清单与发布前扫描流程见 [feedback_no_bare_numbered_refs.md](feedback_no_bare_numbered_refs.md)，这是用户三次纠正的高发错误）；教科书级概念首现处必须"有概念页 + 内联链接"两件齐。
5. **立刻记账。** 实验参数/结果/方向性决定当场写进 memory（git 记代码不记决策，[feedback_record_experiments.md](feedback_record_experiments.md)）；讲完论文四产物同回合完成；会话可能中断，做到一半先写 checkpoint（照 papers/INDEX.md 的 SESSION CHECKPOINT 格式：给页 ID/任务 ID/下一步动词，让下个会话零推断续做）。**记账时的跨文件义务（2026-08-14 加）**：更新某项目状态后，同回合 grep memory 目录里该项目名/代号的其他出现处，把旧状态快照改成指向单源的指针——别的文件里的状态一律写指针不写快照（判例与细则=[feedback_memory_capture_rules.md](feedback_memory_capture_rules.md) 跨文件状态快照禁令节；事故=候选 D <project-B> 状态两处记载漂移两天后答错用户）。
6. **报告忠实。** 测试失败就说失败并贴输出；跳过的步骤明说；不确定的写"未核实"，不写含糊的完成句。
7. **外科手术式改动 + 简单优先。**（2026-07-15 采纳自 Karpathy 四守则的两条空档，出处 github.com/multica-ai/andrej-karpathy-skills；另两条 goal-driven / surface-assumptions 本手册已有更强版本，勿重复引入）改既有产物（代码 / .tex / Notion 页 / memory）时：**每行改动必须能追溯到本次请求**；不顺手"改进"邻近代码、注释、格式，照抄现有风格；顺手发现的无关问题=报告，不代修不代删；只清理自己的改动产生的孤儿（import/变量/函数），既有 dead code 不动。这是 2026-07-12 Opus 双事故（.tex 里塞 \paragraph{Writing craft} + 另开平行 memory）所属的失败类的通用律。新写代码或搭基建时自问**"资深工程师会不会说这过度设计了"**——不做单次使用的抽象、没人要的可配置性、不可能场景的错误处理；200 行能砍成 50 就重写；勿为用而用（配套判断：琐碎小任务不必套全套流程，防线是给非琐碎工作准备的）。

8. **对话正文写给人读。**（2026-08-05 用户反馈「黑话太多看不懂」）memory/台账的压缩速记语域不许漏进 chat 正文：完整句子、内部代号换白话或首现括注解释、汇报说事情和结果不堆代号。执行机制=route_reminder.py 的可读性钉（逐回合注入），细节见 [feedback_chinese_readability.md](feedback_chinese_readability.md)。

9. **新建资源前先盘点已有的。**（2026-08-13 用户抓：候选 K 要 GPU 版 JAX，我照交接材料一句「需装 cuda 版」直接新装环境，没有先扫已有的 conda 环境——实际上候选 D 的 <env>/<env> 就是能用的 cuda 版 JAX。那次新装碰巧仍是对的选择（旧环境版本 0.4.x，与已记录判定用的 0.6.2 不一致），但那是事后才查出来的辩护，不是决策依据。）新装环境/新写工具脚本/新建 venv、cron、检查脚本之前，先花一分钟列出已有的同类资源并逐个排除；「排除理由」要能当场说出口（版本不符/归属别的项目/缺关键功能）。同类先例：rebuttal 实验先盘点已有结果再谈新跑；memory 先查既有文件再新建。**Python 环境的盘点已机械化：跑 `~/.local/bin/envs`**（列全部 conda 环境+各仓 venv 的 python/jax/torch/numpy 版本，同库多版本会单列一节；2026-08-13 装，条目见 [reference_local_bin_tools.md](reference_local_bin_tools.md)）——装任何 Python 包环境前必跑它，排除理由写进当次的实验记录/commit 信息。新环境一律钉版本（`pip install "pkg==X.Y.Z"`），版本选择跟着本项目已记录判定走，不跟「最新」走。

## 按任务路由（先读右列文件再动手）

| 任务 | 必读（全文） | 额外硬规则 |
|---|---|---|
| 讲/读新论文（**2026-08-11 起=单产物：只写 Obsidian vault 卡，Paper_Notes 周记雪藏**） | **[feedback_skill_notion_kb.md](feedback_skill_notion_kb.md)（总调度 + 事故校准器）** + [feedback_paper_teaching_method.md](feedback_paper_teaching_method.md)（讲解框架）+ vault CLAUDE.md 与 _meta/CONVENTIONS.md（🧊 周记那两份 [feedback_skill_paper_notes.md](feedback_skill_paper_notes.md) / [project_paper_notes_repo.md](project_paper_notes_repo.md) 只在解冻时读） | 主素材=原文全文（WebFetch/PDF）；先扫 POMDP framing（[feedback_skip_pomdp.md](feedback_skip_pomdp.md)）；**顺序：核查一次（清单全产物共用）→vault 完整卡（tikz 插图义务门+概念原子页补建）→papers/<slug>.md digest+INDEX 行→Zotero**；**周记只有用户明确说要写才写，不主动问、不主动提议**；**chat 全程零讲解正文——讲解框架只落进产物，最终消息=完成摘要+flag（2026-07-10 定规，07-15 用户点名复发）** |
| ~~Notion 建页/改页~~（**2026-07-17 冻结**：不新增不同步不巡检；解冻或查旧页前先读 [project_notion_paper_sync.md](project_notion_paper_sync.md) 存档 + 分账号权限 [feedback_no_notion_on_sheldon_account.md](feedback_no_notion_on_sheldon_account.md)） | —— | —— |
| 🧊 写 Paper_Notes 论文小结（**雪藏中，2026-08-11 用户裁定；只有用户明说才开**） | **[feedback_skill_paper_notes.md](feedback_skill_paper_notes.md)（端到端流程）** + [project_paper_notes_repo.md](project_paper_notes_repo.md)（周模板/bib 管线，开新周必抄） | 内容四纪律（镜像原文/推导写全/归因审计/数字 verbatim）+ 周边界自包含 + 重排后 forward-ref 扫描——全在 skill 文件里，逐步照做；三个每日自动检查已移入 goals/retired/，解冻时移回 |
| LaTeX 笔记通用规则（RL_Note / Paper_Notes 皆适用） | 本行右列即规则全集（各链一个文件） | \top 不用 \intercal（[feedback_transpose_symbol.md](feedback_transpose_symbol.md)）；\mathds{1} 不用 \mathbb{1}（[feedback_indicator_macro.md](feedback_indicator_macro.md)）；.tex 里零 CJK、先译英（[feedback_no_cjk_in_latex.md](feedback_no_cjk_in_latex.md)）；eqref 风格（[feedback_eqref_style.md](feedback_eqref_style.md)）；eqref 指向"就是该量"的式子而非其变换（[feedback_cross_ref_precision.md](feedback_cross_ref_precision.md)）；已讲过的概念引 label 不重讲（[feedback_no_repeat_concepts.md](feedback_no_repeat_concepts.md)）；照抄论文原 notation 不"优化"（[feedback_match_paper_framing.md](feedback_match_paper_framing.md)）；移植推导逐步写全（[feedback_preserve_derivation_detail.md](feedback_preserve_derivation_detail.md)）；不硬扩写（[feedback_no_forced_expansion.md](feedback_no_forced_expansion.md)）；两本笔记互不同步（[feedback_dont_sync_notebooks.md](feedback_dont_sync_notebooks.md)）；编辑完 commit+push（Overleaf 渲染，本地永不编译：[feedback_overleaf_autosync.md](feedback_overleaf_autosync.md)、[feedback_no_local_latex.md](feedback_no_local_latex.md)）；新写正文一句一行、禁 ~66 列硬换行（[feedback_tex_line_breaking.md](feedback_tex_line_breaking.md)，对所有 .tex 生效） |
| 提炼 idea / 立项新论文（全链条调度） | **[feedback_skill_idea_to_paper.md](feedback_skill_idea_to_paper.md)（工序总调度：矿脉→四关判据→gap 论文入库→立项→实验→写作→提交）** + [project_rcmg_next_papers.md](project_rcmg_next_papers.md)（候选台账） | idea 四关：claim 一句话 / KB≥2 分区工具箱 / unfair advantage / scoop check；gap papers 全走双产物入库；candidate 表用户拍板后才动工；每步开工再读对应 skill 全文 |
| 投稿论文（ampmt/arxiv 仓） | **[feedback_skill_paper_writing.md](feedback_skill_paper_writing.md)（端到端方法论 + 提交前 grep 审计）** + [feedback_paper_artifact_hygiene.md](feedback_paper_artifact_hygiene.md) + [feedback_self_citation_discipline.md](feedback_self_citation_discipline.md) | 内部代号(E1/c1_d1/μ-vs-ζ)不进正文和图；图=裸面板无标题无(a)(b)；投稿仓禁 \paragraph{} 和 em-dash（笔记仓不禁：[feedback_no_paragraph_no_emdash.md](feedback_no_paragraph_no_emdash.md)）；自引每结构角色≤1 次；伪代码 TD3/MADDPG 风格、引 label 不内联（[feedback_concise_algorithm_blocks.md](feedback_concise_algorithm_blocks.md)） |
| 设计/跑 <project-A> 实验 | **[feedback_skill_experiment_design.md](feedback_skill_experiment_design.md)（claim 先行、probe→pilot→gate→grid→5-seed、对照公平性）** + ~/<project-A>/EXPERIMENT_PLAN.md + [project_multihost_dispatch.md](project_multihost_dispatch.md) + [feedback_rcmg_experiment_folder_convention.md](feedback_rcmg_experiment_folder_convention.md) | **λ/值结构不许动**（[feedback_lambda.md](feedback_lambda.md)）；launcher 必设 `CUDA_VISIBLE_DEVICES=`；SLURM 8 节点永不 bare-ssh；yoshikiri 不跑训练（home base：cron/GL/交互）；NFS 共享 home——cron 不重复建；folder = E<N>_<env> 自包含 |
| <project-A> 读曲线/评估 | [feedback_convergence_protocol.md](feedback_convergence_protocol.md) + [project_rcmg_eval_protocol.md](project_rcmg_eval_protocol.md) | 对抗+对偶曲线不走平：端点用尾窗均值/多 ckpt，drift-z>1 续训；成功=双方活跃的稳定受限均衡，不是单方压制（[feedback_equilibrium.md](feedback_equilibrium.md)） |
| Beamer 讲稿 | [project_kikura_beamer.md](project_kikura_beamer.md) + [project_flash_talk_convention.md](project_flash_talk_convention.md) | 研究会开头 1 页 flash-talk teaser |
| 读教材→建学科知识库/写课件 | **[feedback_skill_textbook_kb.md](feedback_skill_textbook_kb.md)（/book-read 细节单源：三段式全流程）** + vault CLAUDE.md 与 _meta/CONVENTIONS.md + [project_teaching_repos.md](project_teaching_repos.md)（Phase B 时） | **课件非默认产物（用户明说+圈范围才做）**；Phase 0 用户拍板才开工；每卡/每讲 draft+对抗验证双 agent，原书 typo flag 不传染；课件 anchor-first（L1 用户实渲验收才量产）；共享 worktree 提交必带 pathspec 禁裸 commit；LEDGER=进度唯一记账 |

## 永远不做（跨任务黑名单）

- 不改 λ/对偶机制、不动值结构（除非用户明说）。
- 不用裸 `python`/`python3` 跑任何 <project-A> 代码（含 `-c` 一行命令）——一律绝对路径 `~/miniforge3/envs/rl/bin/python3`（[project_multihost_dispatch.md](project_multihost_dispatch.md)；2026-07-08 十个 eval job 因此全灭）。
- 不在本机编译 LaTeX（没有 pdflatex/biber；用结构性 grep 自检后 commit）。
- 不把 Paper_Notes 和 RL_Note 互相同步，即使"同一条定理"。
- 不臆造 URL、不留"建设中"占位链接（Notion 时代两次翻车；vault 里 dangling wikilink 要么是有意的未来占位、要么修掉）。
- 不把用户给的 DOI/arXiv 号写进 caption/标题（那是学习素材：[feedback_references_for_learning.md](feedback_references_for_learning.md)）。
- 不引用 RL_Note 作为概念页的"延伸阅读"（私人笔记不是引用源；内容可搬进正文）——vault 概念页同样适用。
- 不向 Notion 写任何东西（2026-07-17 冻结；解冻=用户明令 + 重读存档台账）。

## 执行基建（2026-07-06 起，六级保证见 [project_skill_enforcement.md](project_skill_enforcement.md)）

- **六个 native skill 是首选入口**：`/paper-read` `/paper-idea` `/exp-design` `/paper-write` `/kb-audit` `/book-read`——触发即强制载入骨架+Read 清单，比本表的自觉路由可靠；本表仍是兜底与总览。
- **机械检查一律跑脚本**（`~/.claude/scripts/`）：裸编号=scan_bare_refs.py、笔记仓=check_latex.sh、投稿仓=preflight_submission.sh、vault=_meta/scripts/check_links.py——不许现场凭记忆重造 regex/查询。（Notion 审计已随 2026-07-17 冻结退役，notion_audit_queries.md 留档。）
- hooks 已在 ~/.claude/settings.json 自动注入路由提醒（UserPromptSubmit）、Notion 发布前 checklist（PreToolUse）、craft 隔离拦截（PreToolUse），并挂**停止门**（Stop：本会话动过的仓收尾检查不清零不许停，2026-07-15 起，[reference_loop_engineering.md](reference_loop_engineering.md)）。
- **loop 纪律**（2026-07-15，[reference_loop_engineering.md](reference_loop_engineering.md)）：有清晰机械停止条件的迭代任务可建议用户 `/goal <条件>`；将来任何 headless/cron claude——机械核对用 `--model haiku`、判断类才用大模型；实验监控类 routine 永远本地 cron（云 /schedule 摸不到 fleet/NFS）；**prompt 必含日志尾窗纪律：命令输出只取 tail/grep 窗口，禁全量 cat 长日志**（2026-07-15 采纳，理由与出处见 [reference_loop_engineering.md](reference_loop_engineering.md) 追加节）。

## 会话开工顺序（每次照做）

1. 读 MEMORY.md（自动加载）→ 若任务命中上表某行，**优先 invoke 对应 native skill；无对应 skill 才手动 Read 该行指南文件全文**。
2. 有未完成 checkpoint（papers/INDEX.md 底部 / 各 project_* 文件）→ 先向用户确认是否续做。
3. 动手；中途每完成一个可交付单元就记账，不攒到最后。
4. 发布/提交前跑对应自查（裸编号扫描、裸概念扫描、错字形近字、链接可达）。

## 2026-09-09：跑过一次官方 prompt-audit，结论与一处自我否决

`/claude-api prompt-audit` 是**内置技能**，不在 `~/.claude/skills/` 里。
⛔ 别用 `find ~/.claude -name '*claude-api*'` 判断它在不在——查不到不等于没装。

**审计结果：整体是干净的。** 没有写死的旧模型名，没有过时的接口参数
（`budget_tokens`、改过的采样参数、助手回合预填、`stop_sequences` 包 JSON 全都没有），
没有「一步一步思考」这类为旧模型写的咒语，注入内容逐字节固定不破坏缓存。

### 改掉的两处

1. **每轮注入的黑话词表从 62 个精简到 18 个**，注入从 1957 字符降到 1362。
   判据是实测命中率，细节见 [[feedback-chinese-readability]]。
2. **`skills/paper-read/SKILL.md` 里 3 处迁移式表述**（「原先写的是 X」「比原先记的严重」
   「原本只问 A 不问 B」）改写成直接陈述当前规则。
   ⭐ **理由与判例原样保留**——按指引的「不要动」清单，理由是上下文，永远不算冗余。

### ⛔ 一处我提了又自己否掉的：拆分那个 7 万字节的技能文件

我先按「体量是每次触发都要付的代价」建议把它拆开。**回头逐条读过内容后否掉了**：
那 2.9 万字符的大节是 **18 个编号的工作流程步骤**，每一条都是不可跳过的判据，
不是可以挪走的旧事记录。

⭐ 指引自己写着两句话，正好否掉我的建议：
「**Cruft != length，绝不能用字符数替代删除的理由**」，
以及「**易错操作保留精确脚本**——只有一条安全路径时，规定得细是对的」。

⭐ **可复用的教训：拿体量当判据去精简提示词，正是这套审计方法明令禁止的做法。**
下次再想「这个文件太大了」，先问「里面哪一句是为旧模型写的」，答不上来就别动。
