#!/usr/bin/env bash
# memory 失效引用检查 (2026-07-15, 规则设计采自 Ctxlint stale-file-ref + agnix
# CC-HK-008 的提取→豁免→展开→验证流水线, 调研报告见 memory feedback_memory_ref_audit.md)。
# 用法: check_memory_refs.sh [memory_dir]
# ERROR (R1-R3) 计入退出码; WARN (R4) / INFO (R5 悬空 wikilink) 只报告 —
# wikilink 设计上允许"值得以后写"的有意悬空, 永不判死。
set -u
MEM=${1:-$HOME/.claude/projects/-home-mil-n-chang/memory}
GOALS=$HOME/.claude/goals
FAIL=0
note() { printf '\n== %s ==\n' "$1"; }
expand() { echo "${1/#~\//$HOME/}"; }

note 'R1 局部 md 链接 (ERROR — [text](x.md) 指向不存在的 memory 文件)'
BAD=0
while IFS=: read -r f link; do
  rel=${link#\(}; rel=${rel%\)}
  [ -f "$MEM/$rel" ] || [ -f "$(dirname "$f")/$rel" ] || { echo "$f -> $rel"; BAD=1; }
done < <(grep -roE '\]\([A-Za-z0-9_./-]+\.md\)' "$MEM" --include='*.md' | sed 's/\]//')
[ $BAD -eq 0 ] && echo OK || FAIL=1

note 'R2 goals predicate 脚本 (ERROR — 谓词脚本失踪=巡检静默失效, 最高危)'
BAD=0
for g in "$GOALS"/*.md; do
  [ -f "$g" ] || continue
  pred=$(sed -n 's/^predicate: //p' "$g" | head -1)
  for tok in $(grep -oE '(~|/home/[^ ]+)?/[^ ]+\.(sh|py)' <<<"$pred"); do
    p=$(expand "$tok")
    [ -f "$p" ] || { echo "$(basename "$g"): $tok 不存在"; BAD=1; }
  done
done
[ $BAD -eq 0 ] && echo OK || FAIL=1

note 'R3 正文显式脚本调用 (ERROR — "bash ~/x.sh" 形态是操作指令, 失效必报)'
BAD=0
while IFS= read -r line; do
  f=${line%%:*}; rest=${line#*:}
  tok=$(grep -oE '(~|/home)[A-Za-z0-9_./-]+\.(sh|py)' <<<"$rest" | head -1)
  [ -z "$tok" ] && continue
  p=$(expand "$tok")
  [ -f "$p" ] || { echo "$f: $tok 不存在"; BAD=1; }
done < <(grep -roE '(bash|sh|python3?) +(~|/home)[A-Za-z0-9_./-]+\.(sh|py)' "$MEM" --include='*.md')
[ $BAD -eq 0 ] && echo OK || FAIL=1

note 'R4 白名单根下 ~ 路径 (WARN — 含 $ 或 * 的跳过; 改名后的旧引用集中在这)'
while IFS= read -r tok; do
  case "$tok" in *'$'*|*'*'*) continue;; esac
  t=${tok%%[),.:;\'\"]}
  p=$(expand "$t")
  [ -e "$p" ] || echo "WARN: $t"
done < <(grep -rhoE '~/(<project-A>|Overleaf|\.claude|zotero_tools)/[A-Za-z0-9_./*$-]+' "$MEM" --include='*.md' | sort -u)
echo done

note 'R6 反投毒候选 (INFO — 负面能力断言且同行无修法/替代; 采自 ARIS capture-antipatterns'
printf '%s\n' '    2026-07-22: 只筛候选供人工分诊, 判据单源 feedback_memory_capture_rules.md)'
N6=0
while IFS= read -r line; do
  rest=${line#*:*:}
  case "$rest" in
    *修*|*绕过*|*改用*|*替代*|*workaround*|*instead*|*fallback*|*用*即可*|*解法*|*→*) continue;;
  esac
  echo "INFO: $line" | cut -c1-160; N6=$((N6+1))
  [ $N6 -ge 20 ] && { echo 'INFO: ...(>20 截断)'; break; }
done < <(grep -rnE "永不能|永远无法|不可能实现|(cannot|can't) be (done|used|fixed)|is (fundamentally )?broken|doesn'?t work at all" "$MEM" --include='*.md' 2>/dev/null)
echo "candidates: $N6"

note 'R5 悬空 wikilink (INFO — 有意悬空合法, 只供周巡检分诊, 不计退出码)'
# [[x]] 解析目标 = 各 memory 文件 frontmatter 的 name: slug (文件名仅兜底)
SLUGS=$(mktemp)
# 注意 memory 目录可能是软链, find 不跟随 → 一律用 glob
{ sed -n 's/^name: *//p' "$MEM"/*.md "$MEM"/*/*.md 2>/dev/null
  for f in "$MEM"/*.md "$MEM"/*/*.md; do [ -f "$f" ] && basename "$f" .md; done; } | sort -u > "$SLUGS"
N=0
while IFS= read -r w; do
  name=${w#\[\[}; name=${name%\]\]}
  grep -qxF "$name" "$SLUGS" || { echo "INFO: [[$name]]"; N=$((N+1)); }
done < <(grep -rhoE '\[\[[A-Za-z0-9_-]+\]\]' "$MEM" --include='*.md' | sort -u)
rm -f "$SLUGS"
echo "dangling: $N"

printf '\n== 结论: %s ==\n' "$([ $FAIL -eq 0 ] && echo PASS || echo 'FAIL (R1-R3 逐条修)')"
exit $FAIL
