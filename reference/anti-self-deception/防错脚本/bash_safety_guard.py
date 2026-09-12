#!/usr/bin/env python3
"""PreToolUse(Bash) destructive-command guard — 执行保证第七级 (2026-07-15).

设计采自 kenryu42/claude-code-safety-net (MIT) 的调研结论 (报告见 memory
feedback_bash_safety_guard.md), 但按本环境重写: 只拦"已知事故形状"的高置信
破坏性命令, 宁缺勿滥 (它默认拦 git restore/stash drop 等日常操作, 且 rm 的
cwd 内放行恰好漏掉无 git 史的 ~/<project-A> —— 与本环境需求相反)。

通道: stdout JSON permissionDecision "deny"(硬拦) / "ask"(交互确认, headless
下无人应答=拒, 正好自治从严)。放行=零输出。本 hook 是防事故安全网, 不是
安全边界 —— 自身异常时放行 (fail-open), 只追加日志; 别让守门人变成路障。
"""
import json
import os
import re
import shlex
import sys

HOME = os.path.expanduser('~')
LOG = os.path.join(HOME, '.claude', 'safety_guard.log')

PROTECT_TOPLEVEL = [  # rm -rf 直指这些 = deny (更深层放行, prune_runs.sh 不受影响)
    f'{HOME}/<project-A>', f'{HOME}/Overleaf', f'{HOME}/.claude',
]
PROTECT_TREE = [      # 任意 rm 指向其内 = deny (不可再生资产, 整树)
    f'{HOME}/.claude/goals', f'{HOME}/.claude/scripts', f'{HOME}/.claude/rules',
]
ROOT_LITERALS = {'/', '/*', '~', '~/', '~/*', HOME, HOME + '/', HOME + '/*'}


def expand(tok):
    t = tok.replace('${HOME}', HOME).replace('$HOME', HOME)
    if t == '~' or t.startswith('~/'):
        t = HOME + t[1:]
    return os.path.normpath(t) if t not in ('/', '/*') else t


def split_segments(cmd):
    """按 ; && || | & 与换行切段, 引号内不切; 解析不动时整串作一段兜底."""
    segs, cur, q, i = [], '', '', 0
    while i < len(cmd):
        c = cmd[i]
        if q:
            cur += c
            if c == q:
                q = ''
        elif c in '"\'':
            q = c; cur += c
        elif c in ';\n|&':
            if cur.strip():
                segs.append(cur.strip())
            cur = ''
            while i + 1 < len(cmd) and cmd[i + 1] in '|&':
                i += 1
        else:
            cur += c
        i += 1
    if cur.strip():
        segs.append(cur.strip())
    return segs or [cmd]


def rm_recursive_force(toks):
    short = ''.join(t[1:] for t in toks if re.match(r'^-[A-Za-z]+$', t))
    rec = bool(set('rR') & set(short)) or '--recursive' in toks
    frc = 'f' in short or 'F' in short or '--force' in toks
    return rec and frc


def under(path, roots):
    return any(path == r or path.startswith(r + '/') for r in roots)


def git_dir(toks, cwd):
    for j, t in enumerate(toks):
        if t == '-C' and j + 1 < len(toks):
            return expand(toks[j + 1])
    return cwd


def mktemp_vars_of(cmd):
    """同一命令串内由 $(mktemp ...) 赋值的变量名集合 (2026-08-05 Compost 提案三,
    用户签字): rm -rf $T 若 T 在同串由 mktemp 赋值 → 放行+记账。豁免刻意窄:
    只认字面 `VAR=$(mktemp` 形态, 跨命令/间接赋值不豁免, headless 从严不变。"""
    return set(re.findall(r'\b(\w+)=\$\(\s*mktemp\b', cmd))


ASSIGN_RE = re.compile(
    r'(?:^|[;&|(]\s*|\s)(?:export\s+)?(\w+)=("[^"`]*"|\'[^\']*\'|[^\s;|&"\'`()]+)')


def literal_path_vars(cmd):
    """同一命令串内 VAR=<字面路径> 赋值 (2026-08-10 Compost 提案二, 用户签字):
    值展开 ~/$HOME 后不得再含 $/` (命令替换/嵌套变量不算字面)。同名后写覆盖
    先写; 后写若非字面则整个变量作废 (维持 ask), 与 shell 实际取值一致从严。"""
    out = {}
    for name, val in ASSIGN_RE.findall(cmd):
        v = val.strip('"\'')
        v = v.replace('${HOME}', HOME).replace('$HOME', HOME)
        if v == '~' or v.startswith('~/'):
            v = HOME + v[1:]
        if not v or re.search(r'[$`]', v):
            out.pop(name, None)
            continue
        out[name] = v
    return out


def resolve_literal_target(raw, lit_vars, cwd):
    """把 rm 目标里的 $VAR/${VAR} 全部换成同串字面赋值的值。任一变量解析不出
    或结果仍含 $/` = None (调用侧维持 ask); 相对路径拼 cwd 后归一化。"""
    hit = []

    def sub(m):
        name = m.group(1) or m.group(2)
        v = lit_vars.get(name)
        if v is None:
            return '\x00'
        hit.append(name)
        return v

    out = re.sub(r'\$\{(\w+)\}|\$(\w+)', sub, raw)
    if not hit or '\x00' in out or re.search(r'[$`]', out):
        return None
    out = expand(out)
    if not os.path.isabs(out):
        out = os.path.normpath(os.path.join(cwd, out))
    return out


def check_segment(seg, cwd, mktemp_vars=frozenset(), lit_vars=None):
    """返回 (level, reason) 或 None; level ∈ {'deny','ask'}."""
    # 2026-07-22 (ECC block-no-verify 调研, GHSA-4v57-ph3x-gf55 同类): 引号包
    # 命令名 ("r"m / 'd'd) 可穿透裸 regex — 前置 regex 检查一律跑去引号副本。
    norm = seg.replace('"', '').replace("'", '')
    low = norm.lower()
    # 12. 顶层 dd/mkfs/shred (safety-net 的漏项; 共享服务器零正常用例)
    if re.search(r'^\s*(?:sudo\s+)?(?:dd\b.*\bof=/dev/|mkfs(?:\.\w+)?\b|shred\b)', norm):
        return 'deny', '磁盘毁灭级命令 (dd of=/dev|mkfs|shred)'
    # 4. Zotero API DELETE = 永久删
    if 'api.zotero.org' in low and re.search(r'(?:-x\s*|--request[= ]|--method[= ])delete', low):
        return 'deny', 'Zotero API DELETE 是永久删除, 需用户手动执行'
    # 5. crontab -r 清空全部 cron
    if re.search(r'\bcrontab\s+-[a-z]*r', norm):
        return 'deny', 'crontab -r 会清空全部哨兵/goal/prune cron 且无恢复'
    try:
        toks = shlex.split(seg)
    except ValueError:
        # shlex 解析不动的畸形引号串: 去引号后再分词, 防 "r"m 类绕过
        toks = norm.split()
    if not toks:
        return None
    head = os.path.basename(toks[0])
    while head in ('sudo', 'env', 'command', 'nohup', 'timeout') and len(toks) > 1:
        toks = [t for t in toks[1:] if '=' not in t or not re.match(r'^\w+=', t)]
        if not toks:
            return None
        head = os.path.basename(toks[0])

    if head == 'rm':
        raws = [x for x in toks[1:] if not x.startswith('-')]
        # 2026-08-10 (Compost 提案二): 变量目标先按同串字面赋值解析成实路径,
        # 解析成功者与字面目标同过下面全部 deny 检查 (顺带补了 deny 对变量
        # 目标的盲区); 解析不出/跨命令赋值维持 ask 从严。
        resolved = {}
        for x in raws:
            if re.search(r'[$`]', x):
                rp = resolve_literal_target(x, lit_vars or {}, cwd)
                if rp is not None:
                    resolved[x] = rp
        targets = [expand(resolved.get(x, x)) for x in raws]
        for t in targets:
            if under(t, PROTECT_TREE) or re.match(
                    rf'{re.escape(HOME)}/\.claude/(projects/[^/]+/memory(/|$)|settings[^/]*\.json$)', t):
                return 'deny', f'rm 指向不可再生资产 {t} (memory/goals/scripts/rules/settings)'
        if rm_recursive_force(toks):
            for raw, t in zip(raws, targets):
                if raw in ROOT_LITERALS or t in ROOT_LITERALS:
                    return 'deny', 'rm -rf 指向 / 或 $HOME'
                if t in PROTECT_TOPLEVEL or re.match(
                        rf'{re.escape(HOME)}/(Overleaf/[^/]+|<project-A>/(E[^/]*|RCMGs\.py|rcmg_nagent\.py))$', t):
                    return 'deny', f'rm -rf 指向受保护顶层资产 {t} (无 git 史/Overleaf 仓)'
                if raw in resolved:
                    continue  # 解析出的实路径已通过上面全部 deny 检查: 放行
                if re.search(r'[$`]', raw) and not under(t, ['/tmp', '/var/tmp']) \
                        and 'scratchpad' not in raw and '$TMPDIR' not in raw:
                    mv = re.match(r'^"?\$\{?(\w+)\}?"?(/.*)?$', raw)
                    if mv and mv.group(1) in mktemp_vars and not mv.group(2):
                        continue  # 同串 mktemp 赋值的裸变量: 放行 (main 里记账)
                    return 'ask', f'rm -rf 目标含变量 {raw}, 静态无法验证'
        return None

    if head == 'git':
        gd = git_dir(toks, cwd)
        in_ol = under(gd, [f'{HOME}/Overleaf'])
        # 2026-08-05 修: -C <path> 的路径参数曾被误当子命令, git -C <ol仓> reset
        # --hard 静默溜过 (回归测试抓到; 台账 reference_paper_skill_survey.md)
        sub, skip = '', False
        for t in toks[1:]:
            if skip:
                skip = False; continue
            if t == '-C':
                skip = True; continue
            if not t.startswith('-'):
                sub = t; break
        if sub == 'push' and in_ol and any(
                t in ('-f', '--force', '--mirror') for t in toks):
            return 'deny', 'Overleaf 仓 force push 会改写同步端历史 (--force-with-lease 可用)'
        if sub == 'reset' and in_ol and any(t.startswith('--ha') or t == '--merge' for t in toks):
            return 'ask', 'Overleaf 仓 git reset --hard, 会丢未推送工作'
        if sub == 'clean' and in_ol and any(re.match(r'^-[a-z]*f', t) or t == '--force' for t in toks) \
                and not any(t in ('-n', '--dry-run') for t in toks):
            return 'ask', 'Overleaf 仓 git clean -f, 会删未跟踪文件'
        if in_ol and (
                (sub == 'checkout' and '--' in toks and not any(t in ('-b', '-B') for t in toks))
                or (sub == 'restore' and not any(t in ('--staged', '-S') for t in toks))):
            return 'ask', 'Overleaf 仓丢弃工作树改动 (checkout --/restore)'
        return None

    if head == 'find':
        roots = [expand(t) for t in toks[1:2]]
        if roots and under(roots[0], PROTECT_TOPLEVEL + PROTECT_TREE):
            if '-delete' in toks:
                return 'deny', f'find {roots[0]} -delete 指向受保护树'
            if '-exec' in toks and 'rm' in toks[toks.index('-exec'):]:
                sub = toks[toks.index('-exec'):]
                if rm_recursive_force(sub):
                    return 'deny', f'find {roots[0]} -exec rm -rf 指向受保护树'
        return None

    if head in ('xargs', 'parallel') and 'rm' in toks and rm_recursive_force(toks):
        return 'ask', 'xargs/parallel rm -rf, 目标在管道里静态不可见'

    if head.startswith('python') or head in ('node', 'perl'):
        code = ' '.join(toks)
        if re.search(r'shutil\.rmtree|os\.system\([^)]*rm -rf', code) and any(
                p in code for p in ('<project-A>', 'Overleaf', '.claude')):
            return 'ask', '解释器代码内递归删除且提及受保护路径'
    return None


def main():
    try:
        data = json.load(sys.stdin)
        if data.get('tool_name') != 'Bash':
            return
        cmd = (data.get('tool_input') or {}).get('command') or ''
        cwd = data.get('cwd') or os.getcwd()
        worst, reasons = None, []
        mtv = mktemp_vars_of(cmd)
        litv = literal_path_vars(cmd)
        used_lit = sorted(n for n in litv
                          if re.search(r'\$\{?%s\b' % re.escape(n), cmd)) \
            if litv else []
        if used_lit and re.search(r'\brm\b', cmd):
            try:  # 字面路径豁免同 mktemp 纪律: 走过必留痕 (append-only 台账)
                import datetime
                ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                with open(LOG, 'a') as f:
                    f.write(json.dumps({'ts': ts, 'cwd': cwd, 'decision': 'allow-litvar',
                                        'vars': used_lit, 'cmd': cmd[:200]}) + '\n')
            except Exception:
                pass
        if mtv and re.search(r'\brm\b', cmd):
            try:  # 豁免走过必留痕 (append-only 台账, 规则14 对账用)
                import datetime
                ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                with open(LOG, 'a') as f:
                    f.write(json.dumps({'ts': ts, 'cwd': cwd, 'decision': 'allow-mktemp',
                                        'vars': sorted(mtv), 'cmd': cmd[:200]}) + '\n')
            except Exception:
                pass
        for seg in split_segments(cmd):
            r = check_segment(seg, cwd, mtv, litv)
            if r:
                reasons.append(f'[{r[0]}] {r[1]} <- {seg[:100]}')
                if r[0] == 'deny':
                    worst = 'deny'
                elif worst is None:
                    worst = 'ask'
        if worst:
            msg = ('bash_safety_guard: ' + '; '.join(reasons)
                   + ' | 如确属合法操作, 请让用户本人确认或手动执行。')
            if worst == 'ask':
                # 2026-07-22 采自 ECC gateguard-fact-force: 索要调查产物而非口头
                # 确认 ("确认吗"永远得到 yes; 列对象+回滚+逐字指令骗不了)
                msg += (' 请求确认前先给出: 1) 本命令将修改/删除的对象清单;'
                        ' 2) 一行回滚方案; 3) 用户当前指令的逐字引用。')
            print(json.dumps({'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': worst,
                'permissionDecisionReason': msg}}))
            try:
                # 2026-08-05 (LongHorizon 收割件4, 台账 reference_paper_skill_survey.md):
                # 记账补 ts+cwd, 使日志可对账 ("声称删了" 要能对 "何时何地拦/放了什么")
                import datetime
                ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                with open(LOG, 'a') as f:
                    f.write(json.dumps({'ts': ts, 'cwd': cwd, 'decision': worst,
                                        'cmd': cmd[:400], 'reasons': reasons}) + '\n')
            except Exception:
                pass
    except Exception:
        # fail-open: 安全网自身故障不得瘫痪全部 Bash; 静默放行
        pass


if __name__ == '__main__':
    main()
    sys.exit(0)
