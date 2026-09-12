#!/usr/bin/env python3
"""wild 自治窗口的写入边界检查（PreToolUse hook）。

只在 wild 会话里生效，其他会话一律直接放行。wild 会话的识别是双通道，
任一命中即生效：
  ① 环境变量 WILD_SESSION=1（发射命令里带上，重启后自动覆盖）；
  ② hook 输入的 session_id 出现在 ~/wild/_meta/wild_sessions.txt（每行一个 id，
     用于给已在跑、没带环境变量的会话现场补上边界）。
生效时：
  - Write/Edit/MultiEdit/NotebookEdit：目标路径必须在允许区内，否则拒绝。
  - Bash：启发式扫描写入动作（重定向、rm/mv/cp、sed -i、git 写操作等），
    写入目标落在保护区内则拒绝；纯读命令不拦。
  - 解析失败一律放行（fail-open，与 bash_safety_guard 同哲学）。

允许区（wild 会话可写）：
  ~/wild/                                     自治实验仓
  ~/.claude/projects/-home-mil-n-chang/memory/ 跨会话记忆
  ~/ObsidianVault/Research Ideas/              已关闭实验的结论页（写完须 git commit+push）
  /tmp/                                        scratchpad
保护区（发现问题登记不代修）：
  ~/<project-A>  ~/Overleaf  ~/ObsidianVault(除上述例外)  ~/offline_rcmg
  ~/kb_tools  ~/Teaching  ~/TIEC  ~/zotero_tools  ~/.claude(除 memory)
另外：wild 会话禁止改 crontab（crontab -l 只读除外）。
"""
import json
import os
import re
import sys

HOME = "/home/<user>/n-chang"

ALLOWED = [
    HOME + "/wild/",
    HOME + "/.claude/projects/-home-mil-n-chang/memory/",
    HOME + "/ObsidianVault/Research Ideas/",
    "/tmp/",
]

PROTECTED = [
    HOME + "/<project-A>",
    HOME + "/Overleaf",
    HOME + "/ObsidianVault",
    HOME + "/offline_rcmg",
    HOME + "/kb_tools",
    HOME + "/Teaching",
    HOME + "/TIEC",
    HOME + "/zotero_tools",
    HOME + "/.claude",
]


def allow():
    sys.exit(0)


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def norm(p):
    p = p.strip().strip('"').strip("'")
    if p.startswith("~"):
        p = HOME + p[1:]
    return os.path.normpath(p)


def in_allowed(p):
    p = norm(p)
    return any(p + "/" == a or (p + "/").startswith(a) for a in ALLOWED)


def in_protected(p):
    p = norm(p)
    if in_allowed(p):
        return False
    return any(p == r or p.startswith(r + "/") for r in PROTECTED)


DENY_HINT = ("[wild 写入边界] 只许写 ~/wild、memory、scratchpad、vault 的 Research Ideas。"
             "主线仓/知识库/工具仓只读；发现问题登记进 ~/wild 下的记录文件或发邮件，不代修。")


def check_file_tool(ti):
    fp = ti.get("file_path") or ti.get("notebook_path") or ""
    if fp and not in_allowed(fp):
        deny(DENY_HINT + f" 本次目标: {fp}")
    allow()


PATH_TOKEN = re.compile(r"(?:~|/)[\w.+\-/@ ]*")
SAFE_GIT = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(add|commit|push|pull|fetch|status|diff|log|show|remote)\b")
UNSAFE_GIT = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(checkout|reset|clean|rm|mv|restore|rebase|merge|stash|am|apply)\b")
REDIRECT = re.compile(r">{1,2}\s*((?:~|/)[\w.+\-/@]*)")
DESTRUCTIVE_CMD = re.compile(
    r"^\s*(?:[A-Za-z_][\w]*=\S*\s+)*"
    r"(sudo\s+)?(rm|mv|sed|tee|touch|mkdir|ln|truncate|chmod|chown|dd|unzip|shred)\b")
CP_CMD = re.compile(r"^\s*(?:[A-Za-z_][\w]*=\S*\s+)*(sudo\s+)?(cp|rsync|install)\b")


CD_TARGET = re.compile(r"\bcd\s+((?:~|/)[\w.+\-/@]*)")
ANY_REDIRECT = re.compile(r">{1,2}\s*([^\s&|;]+)")


def check_bash(cmd):
    # crontab：只许 -l
    if re.search(r"\bcrontab\b", cmd) and not re.search(r"\bcrontab\s+-l\b", cmd):
        deny("[wild 写入边界] wild 会话不许改 crontab（只读 crontab -l 允许）。要加定时任务请发邮件请示。")

    # 重定向直指保护区
    for m in REDIRECT.finditer(cmd):
        if in_protected(m.group(1)):
            deny(DENY_HINT + f" 重定向目标越界: {m.group(1)}")

    # cd 进保护区后，相对路径的写入动作同样落在保护区内
    if any(in_protected(m.group(1)) for m in CD_TARGET.finditer(cmd)):
        if UNSAFE_GIT.search(cmd):
            deny(DENY_HINT + " 在保护区目录内执行 git 写操作。")
        for seg in re.split(r"&&|\|\||;|\|", cmd):
            if re.match(r"^\s*(?:[A-Za-z_][\w]*=\S*\s+)*(sudo\s+)?sed\b", seg) and "-i" not in seg:
                continue
            if DESTRUCTIVE_CMD.match(seg) or CP_CMD.match(seg):
                deny(DENY_HINT + " cd 进保护区后出现写入类命令。")
        for m in ANY_REDIRECT.finditer(cmd):
            if not m.group(1).startswith(("/", "~")):
                deny(DENY_HINT + " cd 进保护区后出现相对路径重定向。")

    # 分段检查各子命令
    for seg in re.split(r"&&|\|\||;|\|", cmd):
        # sed 不带 -i 是纯读，跳过
        if re.match(r"^\s*(?:[A-Za-z_][\w]*=\S*\s+)*(sudo\s+)?sed\b", seg) and "-i" not in seg:
            continue
        if DESTRUCTIVE_CMD.match(seg):
            for t in PATH_TOKEN.findall(seg):
                if in_protected(t):
                    deny(DENY_HINT + f" 写入类命令触及保护区: {t.strip()}")
        elif CP_CMD.match(seg):
            toks = [t for t in PATH_TOKEN.findall(seg)]
            if toks and in_protected(toks[-1]):
                deny(DENY_HINT + f" 复制目的地越界: {toks[-1].strip()}")
        elif UNSAFE_GIT.search(seg):
            for t in PATH_TOKEN.findall(seg):
                if in_protected(t):
                    deny(DENY_HINT + f" git 写操作触及保护区: {t.strip()}")
        elif SAFE_GIT.search(seg):
            # add/commit/push 类：vault 例外只为 Research Ideas 页服务，放行
            continue
    allow()


REGISTRY = HOME + "/wild/_meta/wild_sessions.txt"


def is_wild_session(data):
    if os.environ.get("WILD_SESSION") == "1":
        return True
    sid = data.get("session_id") or ""
    if not sid:
        return False
    try:
        with open(REGISTRY) as f:
            return sid in {line.strip() for line in f if line.strip()}
    except OSError:
        return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        allow()
    if not is_wild_session(data):
        allow()
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        check_file_tool(ti)
    elif tool == "Bash":
        check_bash(ti.get("command", "") or "")
    allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
