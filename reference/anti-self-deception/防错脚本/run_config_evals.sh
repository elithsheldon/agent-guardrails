#!/bin/bash
# 行为回归测试 —— 改完 skill / hook / memory / settings 之后，agent 的行为有没有变差。
#
# ## 为什么有这个（2026-08-26）
#
# `check_config_integrity.py` 测的是「配置有没有坏」（文件在不在、自测过不过）。
# 这个测的是**另一件事**：配置**没坏**，但一次合法的修改把行为改差了。
# 例如注入语言规则的那个 hook 还在、还能跑，只是内容被改动后不再生效 ——
# 前一道检查全绿，而回答从此变成英文。
#
# ⭐ 判据是机械的，不用模型当裁判：每条用例给一组正则，命中/不命中即判。
#    ⛔ 有意不引入「让另一个模型判分」——那会把不确定性引进闸门本身，
#    而这道闸门存在的意义正是给出确定的红绿。
#
# ## 成本
#
# 每条用例开一个 headless 会话（`claude -p`），实测每条几秒到几十秒。
# 三条用例合计约一分钟。⛔ 别把它塞进每晚的常驻检查里逐日跑 ——
# 它该在**你改了配置之后**跑，由 config-evals-fresh 那条目标提醒你什么时候该跑。
#
# ## 用法
#
#   bash ~/.claude/scripts/run_config_evals.sh              # 跑全部用例
#   bash ~/.claude/scripts/run_config_evals.sh lang-pin     # 只跑一条
#   bash ~/.claude/scripts/run_config_evals.sh --selftest   # 不调用模型，验判定逻辑
#
# 结果逐行追加到 ~/.claude/evals/eval-ledger.tsv（与 goal-ledger.tsv 同风格）。

set -u
EVALS="${EVALS_DIR:-$HOME/.claude/evals}"
CASES="$EVALS/cases"
LEDGER="$EVALS/eval-ledger.tsv"
OUTDIR="$EVALS/last"
MODEL="${EVAL_MODEL:-sonnet}"      # 用便宜的档；测的是配置层是否生效，不是模型能力
TIMEOUT="${EVAL_TIMEOUT:-180}"
CLAUDE_BIN="${CLAUDE_BIN:-$HOME/.local/bin/claude}"

# ── 判定：把一段回答按用例里的断言逐条判 ──────────────────────────────
# 用法: judge <回答文件> <用例 json>；打印每条断言结果，全过返回 0
judge() {
  local resp="$1" case_json="$2"
  python3 - "$resp" "$case_json" <<'PY'
import json, re, sys
resp = open(sys.argv[1], encoding="utf-8", errors="replace").read()
case = json.load(open(sys.argv[2], encoding="utf-8"))
bad = 0
for a in case.get("assert", []):
    pat, must = a["pattern"], a.get("must", True)
    hit = bool(re.search(pat, resp, re.M))
    ok = (hit == must)
    if not ok:
        bad += 1
        want = "应当出现" if must else "不该出现"
        print(f"      ✗ {a.get('desc','(无说明)')} —— {want}，实际{'出现了' if hit else '没出现'}")
    else:
        print(f"      ✓ {a.get('desc','(无说明)')}")
sys.exit(1 if bad else 0)
PY
}

# ── 自测：不调用模型，只验判定逻辑真的会判错为错 ──────────────────────
if [ "${1:-}" = "--selftest" ]; then
  tmp=$(mktemp -d); ok=1
  cat > "$tmp/c.json" <<'EOF'
{"id":"t","prompt":"x","assert":[
 {"type":"regex","must":true,"pattern":"苹果","desc":"要有苹果"},
 {"type":"regex","must":false,"pattern":"香蕉","desc":"不该有香蕉"}]}
EOF
  printf '这里有苹果\n' > "$tmp/good.txt"
  printf '这里有香蕉\n' > "$tmp/bad.txt"
  printf '这里有苹果和香蕉\n' > "$tmp/mixed.txt"
  echo "== 判定逻辑自测 =="
  judge "$tmp/good.txt"  "$tmp/c.json" >/dev/null 2>&1 && echo "  [PASS] 满足全部断言 -> 通过" || { echo "  [FAIL] 满足全部断言却判失败"; ok=0; }
  judge "$tmp/bad.txt"   "$tmp/c.json" >/dev/null 2>&1 && { echo "  [FAIL] 缺必需内容却判通过"; ok=0; } || echo "  [PASS] 缺必需内容 -> 报红"
  judge "$tmp/mixed.txt" "$tmp/c.json" >/dev/null 2>&1 && { echo "  [FAIL] 出现禁止内容却判通过"; ok=0; } || echo "  [PASS] 出现禁止内容 -> 报红"
  rm -rf "$tmp"
  [ "$ok" = 1 ] && { echo "== SELFTEST: 全部通过 =="; exit 0; } || { echo "== SELFTEST: 有失败 =="; exit 1; }
fi

# ── 真跑 ───────────────────────────────────────────────────────────────
[ -d "$CASES" ] || { echo "⛔ 用例目录不存在: $CASES" >&2; exit 1; }
[ -x "$CLAUDE_BIN" ] || { echo "⛔ 找不到 claude: $CLAUDE_BIN" >&2; exit 1; }
mkdir -p "$OUTDIR"

only="${1:-}"
today=$(date +%F)
pass=0; fail=0; skipped=0

echo "== 行为回归测试 ==（模型 $MODEL，每条一个独立 headless 会话）"
for c in "$CASES"/*.json; do
  [ -f "$c" ] || continue
  id=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['id'])" "$c")
  [ -n "$only" ] && [ "$only" != "$id" ] && continue
  prompt=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['prompt'])" "$c")
  out="$OUTDIR/$id.txt"

  printf '  %-26s ' "$id"
  # ⚠️ 必须用 cd $HOME：hook 与 memory 的加载依赖工作目录，在别处跑等于测了另一套配置。
  # ⭐ CLAUDE_CONFIG_EVAL=1 让开场注入常驻目标违规的那个 hook 闭嘴 —— 它注入的内容
  #    随当天有哪些目标没达标而变，会漏进被测会话的回答里，让判定随环境漂移。
  if ! (cd "$HOME" && CLAUDE_CONFIG_EVAL=1 timeout "$TIMEOUT" "$CLAUDE_BIN" -p "$prompt" --model "$MODEL" \
        > "$out" 2>"$OUTDIR/$id.err"); then
    echo "跑不起来（超时或报错）"
    sed 's/^/        /' "$OUTDIR/$id.err" | head -3
    fail=$((fail+1)); printf '%s\t%s\t%s\n' "$today" "$id" "ERROR" >> "$LEDGER"
    continue
  fi
  if judge "$out" "$c" > "$OUTDIR/$id.judge" 2>&1; then
    echo "PASS"; pass=$((pass+1)); printf '%s\t%s\t%s\n' "$today" "$id" "PASS" >> "$LEDGER"
  else
    echo "FAIL"; cat "$OUTDIR/$id.judge"; fail=$((fail+1))
    printf '%s\t%s\t%s\n' "$today" "$id" "FAIL" >> "$LEDGER"
  fi
done

echo
echo "  通过 $pass · 失败 $fail"
echo "  回答原文留在 $OUTDIR/，判定明细在同目录的 .judge 文件里"
if [ "$fail" -eq 0 ] && [ "$pass" -gt 0 ]; then
  # ⭐ 这一行是 config-evals-fresh 那条目标读的。
  # ⛔ 记的是**配置内容的指纹**，不是时间戳 —— verify_goals.sh 每晚会回写目标文件，
  #    按时间判会天天误报，而一条天天无故变红的检查两周内就会被当噪声忽略。
  fp=$(python3 "$HOME/.claude/scripts/check_config_evals_fresh.py" --print-hash)
  printf '%s\tALL\tGREEN %s\n' "$(date -Iseconds)" "$fp" >> "$LEDGER"
  echo "  已记入 $LEDGER（含一行 ALL GREEN 时间戳）"
  exit 0
fi
[ "$pass" -eq 0 ] && [ "$fail" -eq 0 ] && { echo "  ⛔ 一条用例都没跑到"; exit 1; }
exit 1
