#!/usr/bin/env python3
"""配置改了、行为回归测试没重跑 —— 就报红。

## 为什么有这个（2026-08-26）

`run_config_evals.sh` 能测出「改完配置之后 agent 行为有没有变差」，但它是手动跑的。
一个只在你想起来时才跑的测试，等于没有。这条检查负责提醒：**操控层变了，而最近一次
全绿的行为测试是在变之前跑的。**

## ⛔ 为什么按内容指纹判，而不是按文件修改时间

最自然的写法是「配置文件的最新修改时间不得晚于最近一次全绿的时间戳」。
那样写会**每晚误报一次**：`verify_goals.sh` 自己会把 `status:` 与 `last-pass:`
回写进每个目标文件，于是每天夜里所有目标文件的修改时间都会更新一遍，
而行为测试并没有必要重跑 —— 一条每天都无故变红的检查，两周内就会被当成噪声忽略，
那时它就再也拦不住真正的问题了。

所以判据是**内容指纹**：把配置面所有文件的内容拼起来算一个哈希，
并且在读目标文件时**剥掉那两个自动回写的字段**。内容没变 = 指纹不变 = 不报红，
无论文件被重写过多少次。

## 配置面包含什么

- `~/.claude/skills/**` 里的 SKILL.md（决定 agent 会被什么触发、怎么做那件事）
- `~/.claude/scripts/*.py` `*.sh`（hook 与检查的实现）
- `~/.claude/goals/*.md`（剥掉 status / last-pass 两行）
- `settings.json` `settings.local.json`

⛔⛔ **memory 不在里面，而这是一处真实的缺口，不是"没风险"（2026-08-27 自审改口）。**
原文这里写的是「memory 每天都在长，且改一条记录不构成行为回归风险」——⚠️ **后半句是假的**：
memory 里全是塑造行为的规矩（房规、可读性要求、各类纪律），改一条完全可能改变 agent 的行为。
真实理由只有前半句：memory 每天都在增长，把它算进指纹会让这条检查**天天变红**，
而一条天天无故变红的检查两周内就会被当噪声忽略 —— 那时它连现在这点作用也没有了。

⭐ 所以这里必须把边界说出来，而不是把取舍粉饰成"没风险"：
**这条检查绿，只意味着「我定义的那个配置面没变过」，不意味着「影响行为的东西都没变过」。**
判据来自反自欺协议第 32 条 2026-08-27 补的第二问：一个不可伪造的量，未必是你要问的那个量。
这里的量（配置面哈希）不可伪造，但它答的问题比我想问的窄，**窄在 memory 上**。
⚠️ 改了 memory 里的规矩之后想确认行为没变差，**得自己手动跑一次** 
`bash ~/.claude/scripts/run_config_evals.sh`，这条检查不会替你想起来。

## 单独跑

    python3 ~/.claude/scripts/check_config_evals_fresh.py
    python3 ~/.claude/scripts/check_config_evals_fresh.py --print-hash
    python3 ~/.claude/scripts/check_config_evals_fresh.py --selftest
"""
import hashlib
import os
import re
import sys

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
LEDGER = os.path.join(CLAUDE, "evals", "eval-ledger.tsv")

# verify_goals.sh 每晚回写这两个字段，它们不代表配置内容变化，算指纹时必须剥掉
AUTO_FIELDS = re.compile(r"^(status|last-pass):.*$", re.M)


def config_files(root=None):
    root = root or CLAUDE
    out = []
    for sub, exts in (("skills", (".md",)), ("scripts", (".py", ".sh")), ("goals", (".md",))):
        d = os.path.join(root, sub)
        for dirpath, _dirs, files in os.walk(d):
            for f in sorted(files):
                if f.endswith(exts) and f != "VIOLATIONS.md":
                    out.append(os.path.join(dirpath, f))
    for f in ("settings.json", "settings.local.json"):
        p = os.path.join(root, f)
        if os.path.exists(p):
            out.append(p)
    return sorted(out)


def config_hash(root=None):
    h = hashlib.sha256()
    for p in config_files(root):
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        if os.sep + "goals" + os.sep in p:
            text = AUTO_FIELDS.sub("", text)
        h.update(os.path.relpath(p, root or CLAUDE).encode())
        h.update(b"\0")
        h.update(text.encode("utf-8", "replace"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def last_green(ledger=None):
    """最近一次全绿时记录的配置指纹与时间。没有就返回 (None, None)。"""
    ledger = ledger or LEDGER
    try:
        with open(ledger, encoding="utf-8") as fh:
            rows = fh.read().splitlines()
    except OSError:
        return None, None
    for line in reversed(rows):
        parts = line.split("\t")
        if len(parts) >= 3 and parts[1] == "ALL" and parts[2].startswith("GREEN"):
            # 格式: <时间戳>\tALL\tGREEN <指纹>
            m = re.search(r"GREEN\s+(\S+)", parts[2])
            return (m.group(1) if m else None), parts[0]
    return None, None


def main(argv):
    if "--selftest" in argv:
        return selftest()
    cur = config_hash()
    if "--print-hash" in argv:
        print(cur)
        return 0

    green, when = last_green()
    print("== 行为回归测试的新鲜度 ==")
    print(f"  当前配置指纹        {cur}")
    if green is None:
        print(f"  最近一次全绿        （没有记录）")
        print("\n== EVALS: 从没跑过全绿 ==")
        print("   跑一次：bash ~/.claude/scripts/run_config_evals.sh")
        return 1
    print(f"  最近一次全绿        {green}  于 {when}")
    if green == cur:
        print("\n== EVALS: FRESH ==")
        return 0
    print("\n== EVALS: 配置在最近一次全绿之后变过 ==")
    print("   ⚠️ 变的是 skills / scripts / goals / settings 之一 —— 也就是决定 agent")
    print("      怎么干活的那一层。它变了而行为没有重测，正是这条检查存在的理由。")
    print("   重跑：bash ~/.claude/scripts/run_config_evals.sh")
    print("   ⛔ 别为了转绿而删用例。用例变少 = 这条检查覆盖变小，而它照样会变绿。")
    return 1


def selftest():
    """反向验证：指纹要对内容敏感，且要对「自动回写字段」免疫。"""
    import tempfile
    import shutil
    ok = True
    tmp = tempfile.mkdtemp()
    for sub in ("skills", "scripts", "goals"):
        os.makedirs(os.path.join(tmp, sub), exist_ok=True)

    def w(rel, text):
        p = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)

    w("skills/a/SKILL.md", "---\nname: a\ndescription: d\n---\n正文\n")
    w("scripts/x.py", "print(1)\n")
    w("goals/g.md", "---\nname: g\npredicate: true\nstatus: PASS\nlast-pass: 2026-08-01\n---\n说明\n")
    w("settings.json", '{"a":1}')
    h0 = config_hash(tmp)

    # 1. 只改目标文件里自动回写的两个字段 -> 指纹必须不变
    w("goals/g.md", "---\nname: g\npredicate: true\nstatus: FAIL\nlast-pass: 2026-08-26\n---\n说明\n")
    h1 = config_hash(tmp)
    if h1 != h0:
        print("  [FAIL] 只改 status/last-pass，指纹却变了 —— 这会导致每晚误报"); ok = False
    else:
        print("  [PASS] 只改 status/last-pass，指纹不变")

    # 2. 改 skill 的正文 -> 指纹必须变
    w("skills/a/SKILL.md", "---\nname: a\ndescription: d\n---\n换了内容\n")
    h2 = config_hash(tmp)
    if h2 == h0:
        print("  [FAIL] 改了 skill 正文，指纹没变 —— 这条检查会漏掉真正的改动"); ok = False
    else:
        print("  [PASS] 改了 skill 正文，指纹变了")

    # 3. 新增一个脚本 -> 指纹必须变
    w("scripts/y.sh", "echo hi\n")
    if config_hash(tmp) == h2:
        print("  [FAIL] 新增脚本，指纹没变"); ok = False
    else:
        print("  [PASS] 新增脚本，指纹变了")

    # 4. 台账解析：能取到最后一行全绿的指纹
    led = os.path.join(tmp, "led.tsv")
    with open(led, "w", encoding="utf-8") as fh:
        fh.write("2026-08-25\tx\tPASS\n")
        fh.write("2026-08-25T00:00:00+00:00\tALL\tGREEN abc123\n")
        fh.write("2026-08-26\ty\tFAIL\n")
        fh.write("2026-08-26T00:00:00+00:00\tALL\tGREEN def456\n")
    g, _w2 = last_green(led)
    if g != "def456":
        print(f"  [FAIL] 台账里取到的全绿指纹是 {g!r}，应为 'def456'"); ok = False
    else:
        print("  [PASS] 台账里取到最后一次全绿的指纹")

    shutil.rmtree(tmp, ignore_errors=True)
    print("\n== SELFTEST: 全部通过 ==" if ok else "\n== SELFTEST: 有失败 ==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
