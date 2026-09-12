#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit) guard-the-guards — 护栏自保护 (2026-07-22).

设计采自 affaan-m/ECC config-protection.js (调研台账 reference_awesome_claude_code
07-21 批): agent 在检查不过时会倾向改检查器/谓词/hook 配置让检查通过, 而不是修
产物本身。七级执行保证此前全部是"查产物", 没有一级防"被审者改判卷人"。

行为: 编辑目标命中护栏文件 -> permissionDecision "ask" (交互场景由用户放行;
headless 无人应答=拒, 正好从严)。不用 deny: 用户授权的基建维护是常态, 硬拦会
变路障。自身异常 fail-open, 只记日志。
"""
import json
import os
import sys

HOME = os.path.expanduser('~')
LOG = os.path.join(HOME, '.claude', 'safety_guard.log')

PROTECTED_DIRS = [
    f'{HOME}/.claude/scripts',        # 全部检查器/hook 脚本
    f'{HOME}/.claude/goals',          # 停止门/日巡谓词单源
    f'{HOME}/.claude/rules',          # path-scoped 硬门槛卡
]
PROTECTED_FILES = [
    f'{HOME}/.claude/settings.json',
    f'{HOME}/.claude/settings.local.json',
]
# vault checker 也是护栏 (在 vault 仓内, 不在 ~/.claude)
PROTECTED_SUFFIX = ['_meta/scripts/check_links.py']


def is_protected(path):
    p = os.path.normpath(os.path.realpath(path) if os.path.lexists(path) else path)
    if any(p == d or p.startswith(d + '/') for d in PROTECTED_DIRS):
        return True
    if p in PROTECTED_FILES:
        return True
    return any(p.endswith(s) for s in PROTECTED_SUFFIX)


def main():
    try:
        data = json.load(sys.stdin)
        if data.get('tool_name') not in ('Edit', 'Write', 'MultiEdit'):
            return
        fp = (data.get('tool_input') or {}).get('file_path') or ''
        if not fp or not is_protected(os.path.expanduser(fp)):
            return
        msg = ('guard-the-guards: 目标是护栏文件 (检查器/goal 谓词/hooks 配置)。'
               '若动机是"让某个检查通过", 停下——修产物本身, 不改判卷人。'
               '确属用户授权的基建维护再继续。')
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'ask',
            'permissionDecisionReason': msg}}))
        try:
            with open(LOG, 'a') as f:
                f.write(json.dumps({'guard': 'guards', 'file': fp[:300]}) + '\n')
        except OSError:
            pass
    except Exception:
        pass  # fail-open


if __name__ == '__main__':
    main()
    sys.exit(0)
