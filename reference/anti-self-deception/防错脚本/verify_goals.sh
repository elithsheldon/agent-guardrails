#!/usr/bin/env bash
# 常驻目标验证器 — Standing Goals (Agentic OS BUILD 5) 的机械执行版。
# 每天 cron 跑 ~/.claude/goals/*.md 里的全部谓词; 详情见 memory/project_skill_enforcement.md。
#
# goal 文件契约: frontmatter 里 predicate: <一行shell> / manual: true|false /
#   status: / last-pass: — 后两项由本脚本回写, 手工只改 predicate 和 manual。
# 产物: goal-ledger.tsv (date,goal,result) / VIOLATIONS.md (未消化的违反, Claude
#   会话开场 hook 会念它, 修复并 re-verify 通过后自动清除) / logs/<goal>.log。
# 退出码: 0=全过, 1=有违反。谓词只诊断不修 (Sentinel 原则)。
set -u
# GOALS_DIR 只作 RED 测试沙盒用 (设了它同时跳过违规邮件); 生产永远默认路径。
GDIR="${GOALS_DIR:-$HOME/.claude/goals}"
LEDGER="$GDIR/goal-ledger.tsv"
VIOL="$GDIR/VIOLATIONS.md"
TODAY=$(date +%F)
ANYFAIL=0
NEWVIOL=$(mktemp)

for g in "$GDIR"/*.md; do
  name=$(sed -n 's/^name: //p' "$g" | head -1)
  [ -z "$name" ] && continue
  manual=$(sed -n 's/^manual: //p' "$g" | head -1)
  if [ "$manual" = "true" ]; then
    # 2026-08-05 Compost 提案二 (用户签字): manual:true 必须带 review-by 日期,
    # 缺失或过期 = STALE-SKIP 进违规 (perma-SKIP 死账与 perma-FAIL 同罪;
    # 事故=kappa-naming 挂 17 天无日期无复活机制)。
    rb=$(sed -n 's/^review-by: //p' "$g" | head -1)
    if [ -z "$rb" ] || [ "$rb" \< "$TODAY" ]; then
      printf '%s\t%s\tSTALE-SKIP\n' "$TODAY" "$name" >> "$LEDGER"
      ANYFAIL=1
      {
        printf '## %s — STALE-SKIP (%s)\n' "$name" "$TODAY"
        printf 'manual:true 但 review-by=%s (缺失或已过期)。怎么修: 复审该 goal——\n' "${rb:-无}"
        printf '要么复活 (manual:false), 要么退役记原因, 要么给新的 review-by 日期。\n\n'
      } >> "$NEWVIOL"
    else
      printf '%s\t%s\tMANUAL-SKIP\n' "$TODAY" "$name" >> "$LEDGER"
    fi
    continue
  fi
  pred=$(sed -n 's/^predicate: //p' "$g" | head -1)
  log="$GDIR/logs/$name.log"
  if timeout 60 bash -c "$pred" > "$log" 2>&1; then
    printf '%s\t%s\tPASS\n' "$TODAY" "$name" >> "$LEDGER"
    sed -i "s/^status: .*/status: PASS/; s/^last-pass: .*/last-pass: $TODAY/" "$g"
  else
    rc=$?
    # 2026-08-10 Compost 提案三 (用户签字): 退出码 2 = 检查器自身无法运行
    # (预检脚本的保留语义; bash 语法错也是 2), 记 CHECK-ERROR 与 FAIL 分开——
    # 真违规修产物, CHECK-ERROR 修检查器, 混记会把门 bug 当产品债务追查。
    res=FAIL; [ "$rc" -eq 124 ] && res=TIMEOUT; [ "$rc" -eq 2 ] && res=CHECK-ERROR
    printf '%s\t%s\t%s\n' "$TODAY" "$name" "$res" >> "$LEDGER"
    sed -i "s/^status: .*/status: VIOLATED/" "$g"
    ANYFAIL=1
    {
      lastpass=$(sed -n 's/^last-pass: //p' "$g" | head -1)
      printf '## %s — %s (%s)\n' "$name" "$res" "$TODAY"
      if [ "$res" = "CHECK-ERROR" ]; then
        printf '检查器自身退出码 2 (无法运行), 不是产物违规——先修检查命令/环境再谈产物。\n'
      fi
      printf '上次通过: %s · 检查命令输出的前 15 行 (全文 logs/%s.log):\n```\n' "${lastpass:-?}" "$name"
      head -15 "$log"
      printf '```\n\n'
    } >> "$NEWVIOL"
  fi
done

if [ "$ANYFAIL" -eq 1 ]; then
  {
    printf '# STANDING-GOAL VIOLATIONS · %s\n' "$TODAY"
    printf '怎么修: 修产物本身 (检查命令只负责发现问题, 不负责修); 修完重跑 verify_goals.sh 确认全部通过。\n'
    printf '先确认仓库归属 (防自欺规则15): 别的活跃会话正在用的仓库, 只把问题登记给对方处理, 不直接改它的文件。\n'
    printf '排查范围: 各目标上次通过之后, 对相应仓库/知识库做过的改动。\n\n'
    cat "$NEWVIOL"
  } > "$VIOL"
  echo "VIOLATIONS -> $VIOL" >&2
  # 2026-08-05 邮件去重 (事故: 多会话一日 10 轮调用 x 持久红 deadlines = 10 封轰炸):
  # 违规内容 hash 与上次已发一致 -> 只落文件不重发; 内容变化 (新违规/组合变了) 才发。
  VHASH=$(sha256sum "$VIOL" | cut -c1-16)
  LASTMAIL="$GDIR/.last_mailed_viol"
  if [ -n "${GOALS_DIR:-}" ]; then
    echo "[verify_goals] test sandbox (GOALS_DIR set): mail skipped" >&2
  elif [ "$VHASH" = "$(cat "$LASTMAIL" 2>/dev/null)" ]; then
    echo "[verify_goals] violations unchanged since last mail: mail skipped" >&2
  else
  # loop-engineering 采纳 2026-07-15: 违规当天邮件直达 (原来只等下会话开场 hook 念)。
  # house 样式单源 mail_style.py + mailer.py (未配 ~/.rcmg_mail 时静默跳过, 不破巡检)。
  PY="$HOME/miniforge3/envs/rl/bin/python3"; [ -x "$PY" ] || PY=python3
  HTML=$(mktemp --suffix=.html)
  # 2026-07-15 可读版: goals_mail.py 出总表+分节高亮; 渲染失败回退旧版整块 pre。
  { "$PY" "$HOME/.claude/scripts/goals_mail.py" > "$HTML" 2>/dev/null \
    || "$PY" "$HOME/<project-A>/mail_style.py" --title "Standing-goal VIOLATIONS · $TODAY" \
        --pre "$VIOL" --footnote "修产物本身 (检查命令只负责发现问题); 修完重跑 verify_goals.sh 确认全部通过。" \
        > "$HTML" 2>/dev/null; } \
    && "$PY" "$HOME/<project-A>/E1_vmas_navigation/mailer.py" \
      --subject "[goals] VIOLATIONS $TODAY" --body-file "$VIOL" --html-file "$HTML" \
    || echo "[verify_goals] violation mail failed (non-fatal)" >&2
  rm -f "$HTML"
  echo "$VHASH" > "$LASTMAIL"
  fi
else
  # 2026-08-25 用户要求: 违规解决后邮箱别停在红信上——仅在「上次发过违规信且本轮全过」
  # 的转变时刻补发一封绿色 ALL CLEAR (平时全绿不发信, 违规信去重逻辑不变)。
  if [ -f "$GDIR/.last_mailed_viol" ]; then
    if [ -n "${GOALS_DIR:-}" ]; then
      echo "[verify_goals] test sandbox (GOALS_DIR set): all-clear mail skipped" >&2
    else
      PY="$HOME/miniforge3/envs/rl/bin/python3"; [ -x "$PY" ] || PY=python3
      HTML=$(mktemp --suffix=.html)
      "$PY" "$HOME/<project-A>/mail_style.py" --title "Standing goals ALL CLEAR · $TODAY"         --pre "此前邮件里的常驻目标违规已全部解决, 本轮检查全部通过。此信为转绿通知, 无需任何处理。"         --footnote "verify_goals.sh: 违规→全过 转变时刻自动发送 (每次转绿仅一封)。" > "$HTML" 2>/dev/null         && "$PY" "$HOME/<project-A>/E1_vmas_navigation/mailer.py"           --subject "[goals] ALL CLEAR $TODAY"           --body "此前邮件里的常驻目标违规已全部解决, 本轮检查全部通过。(转绿通知, 无需处理)"           --html-file "$HTML"         || echo "[verify_goals] all-clear mail failed (non-fatal)" >&2
      rm -f "$HTML"
    fi
  fi
  rm -f "$VIOL"
  rm -f "$GDIR/.last_mailed_viol"
fi
rm -f "$NEWVIOL"
exit $ANYFAIL
