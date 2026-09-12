#!/usr/bin/env python3
"""配置层完整性检查 —— 操控 agent 的那一层，自己也得被测。

## 为什么有这个检查（2026-08-26）

已有的 40 多个检查脚本和 26 条常驻目标，**全都在检查产物**：论文里有没有裸编号、
知识库卡片长度、引用对不对、交接便条新不新。⛔ **没有一个检查「操控层」本身**——
也就是 hooks、skills、goals、settings.json 这些决定 agent 怎么干活的东西。

这个空白的形状是：`guard_the_guards.py` 能拦住**未授权**修改 skill，但一次**已授权**的
修改把某个 hook 的路径改错了、或把某个脚本的自测跑坏了，没有任何东西会告诉你。
它不会报错，只会安静地不再生效 —— 而"安静地不再生效"正是这套体系最怕的失败方式
（gits 状态栏角标那次就是：11 次调用 11 次超时，一次都没成功，而没有任何人发现）。

⭐ 判据来自用户自己的规矩：**检查要键在当事人伪造不了的量上**。这里键的是
「文件在不在、能不能执行、自测跑不跑得过」，全是客观事实，不读任何自述字段。

## 它测什么（五项，全部零成本、秒级、不调用模型）

1. settings.json 里每一条 hook 命令指向的脚本，**存在且可执行**。
2. 每条常驻目标**写了判定命令**。
   ⛔ 「判定命令引用的脚本存不存在」不在这里查 —— check_memory_refs.sh 的 R2 已经在做。
   这里只管它不管的那一面：一条目标压根没写判定命令，就永远不会被自动跑。
3. 每个**自带 `--selftest` 的脚本**，自测真的通过。
   ⭐ 这一项最值钱：用户的规矩要求机械检查装上时必须反向验证「它真的会报红」，
   自测就是那个反向验证的载体。自测坏了 = 那道检查从此没有反向验证。
4. 每个 skill 目录有 `SKILL.md`，且 frontmatter 里 name 与 description 都不为空。
5. settings.json 与 settings.local.json **本身是合法 JSON**。
   （手改 JSON 漏个逗号，Claude Code 会退回默认配置继续跑，不会拒绝启动。）

## 它故意不测什么

- memory 的引用链、以及目标判定命令所引脚本是否存在 —— `check_memory_refs.sh`
  的 R1/R2/R3 已经在做，不重复造。
- 行为（"改了 skill 之后 agent 是不是变差了"）—— 那要真跑模型，见
  `~/.claude/evals/` 与 `run_config_evals.sh`，另有一条常驻目标管它的新鲜度。

## 单独跑

    python3 ~/.claude/scripts/check_config_integrity.py
    python3 ~/.claude/scripts/check_config_integrity.py --selftest
    python3 ~/.claude/scripts/check_config_integrity.py --skip-selftests   # 跳过第 3 项（慢）
"""
import json
import os
import re
import subprocess
import sys

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
SETTINGS = [os.path.join(CLAUDE, "settings.json"),
            os.path.join(CLAUDE, "settings.local.json")]
SCRIPTS = os.path.join(CLAUDE, "scripts")
SKILLS = os.path.join(CLAUDE, "skills")
GOALS = os.path.join(CLAUDE, "goals")

SELFTEST_TIMEOUT = 90


def hook_commands(path):
    """settings.json 里所有 hook 的 command 字符串。文件不存在或不是 JSON 就返回 None。"""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return []
    except (ValueError, OSError):
        return None
    out = []

    def walk(o):
        if isinstance(o, dict):
            c = o.get("command")
            if isinstance(c, str):
                out.append(c)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    return out


def script_paths_in(cmd):
    """一条命令里出现的、看起来像本地脚本的绝对路径。"""
    return re.findall(r"(/[\w./-]+\.(?:py|sh))", cmd)


def has_selftest(path):
    """脚本里是否真的实现了 --selftest。

    ⚠️ 只 grep 字符串会把「注释里提到 --selftest」也算进来。这里要求它出现在
    参数解析的上下文里（argv 判断或 argparse 的 add_argument）。
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return False
    if "--selftest" not in src:
        return False
    # ⚠️ shell 里判参数的写法不止一种，这里必须都认（2026-08-27 实踩）：
    #    原来只认 `"$1" = "--selftest"`，认不出 `"${1:-}" = "--selftest"`（带默认值展开），
    #    于是一个刚写好的自测**没有被计入**，配置层检查照常打绿灯 —— ⛔ 一道漏掉自测的
    #    检查，恰恰会漏掉「那个脚本的自测已经坏了」这件事，而那正是它要盯的东西。
    return bool(re.search(r'(add_argument\(\s*["\']--selftest|--selftest["\']\s*(?:in|==)|'
                          r'\bin\s+sys\.argv|'
                          r'\$\{?1[^}]*\}?"?\s*(?:=|==)\s*"?--selftest|'
                          r'--selftest["\']?\s*\)\s*$)',
                          src, re.M))


def run(cmd, timeout):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return None, f"超时 {timeout}s"
    except OSError as exc:
        return None, str(exc)


def check_hooks():
    problems, n = [], 0
    for s in SETTINGS:
        cmds = hook_commands(s)
        if cmds is None:
            problems.append(f"{os.path.basename(s)}: 不是合法 JSON —— "
                            "⚠️ Claude Code 遇到这种情况会退回默认配置继续跑，不会拒绝启动，"
                            "所以你的 hook 会全部静默失效")
            continue
        for c in cmds:
            for p in script_paths_in(c):
                n += 1
                if not os.path.exists(p):
                    problems.append(f"hook 指向的脚本不存在: {p}  （出自 {os.path.basename(s)}）")
                elif not os.access(p, os.X_OK) and not c.strip().startswith(("python3", "bash", "sh")):
                    problems.append(f"hook 脚本没有执行权限: {p}")
    return n, problems


def check_goal_predicates():
    problems, n = [], 0
    if not os.path.isdir(GOALS):
        return 0, [f"目标目录不存在: {GOALS}"]
    for fn in sorted(os.listdir(GOALS)):
        if not fn.endswith(".md") or fn == "VIOLATIONS.md":
            continue
        path = os.path.join(GOALS, fn)
        try:
            with open(path, encoding="utf-8") as fh:
                head = fh.read(4000)
        except OSError as exc:
            problems.append(f"{fn}: 读不了 ({exc})")
            continue
        m = re.search(r"^predicate:\s*(.+)$", head, re.M)
        if not m:
            problems.append(f"{fn}: 没有 predicate 字段（这条目标无法被自动检查）")
            continue
        n += 1
        # ⛔ 这里**故意不查**「判定命令引用的脚本存不存在」——
        #    check_memory_refs.sh 的 R2 已经在做同一件事（且它是那条检查的最高危项）。
        #    重复造一遍只会让两处对同一件事各报一次，改判据时还要记得改两个地方。
        #    这里只管 R2 不管的那一面：**一条目标压根没写判定命令**，
        #    那种目标永远不会被自动跑，是个不报错的缺口。
    return n, problems


def check_selftests(skip=False):
    ran, problems = 0, []
    if skip:
        return 0, []
    if not os.path.isdir(SCRIPTS):
        return 0, [f"脚本目录不存在: {SCRIPTS}"]
    for fn in sorted(os.listdir(SCRIPTS)):
        path = os.path.join(SCRIPTS, fn)
        if not os.path.isfile(path) or not fn.endswith((".py", ".sh")):
            continue
        if not has_selftest(path):
            continue
        cmd = ["python3", path, "--selftest"] if fn.endswith(".py") else ["bash", path, "--selftest"]
        ran += 1
        rc, out = run(cmd, SELFTEST_TIMEOUT)
        if rc != 0:
            tail = " / ".join(l.strip() for l in out.strip().splitlines()[-3:])
            problems.append(f"{fn} 的自测没通过 (退出码 {rc}): {tail[:160]}")
    return ran, problems


def check_skills():
    problems, n = [], 0
    if not os.path.isdir(SKILLS):
        return 0, []
    for name in sorted(os.listdir(SKILLS)):
        d = os.path.join(SKILLS, name)
        if not os.path.isdir(d):
            continue
        n += 1
        sk = os.path.join(d, "SKILL.md")
        if not os.path.exists(sk):
            problems.append(f"skill {name}: 缺 SKILL.md")
            continue
        try:
            with open(sk, encoding="utf-8") as fh:
                head = fh.read(2500)
        except OSError as exc:
            problems.append(f"skill {name}: 读不了 ({exc})")
            continue
        if not head.startswith("---"):
            problems.append(f"skill {name}: SKILL.md 没有 frontmatter")
            continue
        for field in ("name", "description"):
            m = re.search(rf"^{field}:\s*(\S.*)$", head, re.M)
            if not m:
                problems.append(f"skill {name}: frontmatter 缺 {field}（缺了它不会被触发）")
    return n, problems


def main(argv):
    if "--selftest" in argv:
        return selftest()
    skip = "--skip-selftests" in argv

    print("== 配置层完整性 ==（hooks / 目标判定命令 / 脚本自测 / skills / JSON）")
    all_problems = []

    n, probs = check_hooks()
    print(f"  hook 指向的脚本      {n} 处引用, {len(probs)} 处问题")
    all_problems += probs

    n, probs = check_goal_predicates()
    print(f"  目标写了判定命令     {n} 条, {len(probs)} 处问题")
    all_problems += probs

    n, probs = check_selftests(skip)
    print(f"  脚本自测             {'跳过' if skip else f'{n} 个跑过, {len(probs)} 个没通过'}")
    all_problems += probs

    n, probs = check_skills()
    print(f"  skills               {n} 个, {len(probs)} 处问题")
    all_problems += probs

    if not all_problems:
        print("\n== CONFIG: CLEAN ==")
        return 0
    print(f"\n== CONFIG: {len(all_problems)} 处问题 ==")
    for p in all_problems:
        print(f"  ⛔ {p}")
    print("\n   ⚠️ 这一层坏掉不会报错，只会安静地不再生效 —— 那正是最难发现的一种。")
    return 1


def selftest():
    """反向验证：造出每一类缺陷，确认它真的会被报出来。

    ⛔ 只测「好配置能通过」等于什么都没测 —— 用户的规矩明写：机械检查装上时
    必须证明它会报红，否则它是信念不是控制。
    """
    import tempfile
    import shutil
    global SETTINGS, SCRIPTS, SKILLS, GOALS
    tmp = tempfile.mkdtemp()
    ok = True

    def case(label, want, setup):
        nonlocal ok
        for sub in ("scripts", "skills", "goals"):
            shutil.rmtree(os.path.join(tmp, sub), ignore_errors=True)
            os.makedirs(os.path.join(tmp, sub), exist_ok=True)
        setup()
        got = 0
        probs = []
        for fn in (check_hooks, check_goal_predicates, lambda: check_selftests(False), check_skills):
            _n, p = fn()
            probs += p
        got = 1 if probs else 0
        mark = "PASS" if got == want else f"FAIL(得到 {got}, 应为 {want})"
        if got != want:
            ok = False
            print(f"    实际问题: {probs}")
        print(f"  [{mark}] {label}")

    SCRIPTS = os.path.join(tmp, "scripts")
    SKILLS = os.path.join(tmp, "skills")
    GOALS = os.path.join(tmp, "goals")
    good_settings = os.path.join(tmp, "settings.json")

    def write(path, text, mode=0o644):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(path, mode)

    # 干净的一份，作为对照
    def clean():
        write(os.path.join(SCRIPTS, "ok.py"), "import sys\nsys.exit(0)\n")
        write(good_settings, json.dumps({"hooks": {"X": [{"hooks": [
            {"command": f"python3 {os.path.join(SCRIPTS, 'ok.py')}"}]}]}}))
        os.makedirs(os.path.join(SKILLS, "s1"), exist_ok=True)
        write(os.path.join(SKILLS, "s1", "SKILL.md"), "---\nname: s1\ndescription: d\n---\n")
        write(os.path.join(GOALS, "g.md"),
              f"---\nname: g\npredicate: python3 {os.path.join(SCRIPTS, 'ok.py')}\n---\n")

    SETTINGS = [good_settings]
    case("干净的配置应当通过", 0, clean)

    def missing_hook():
        clean()
        write(good_settings, json.dumps({"hooks": {"X": [{"hooks": [
            {"command": f"python3 {os.path.join(SCRIPTS, 'gone.py')}"}]}]}}))
    case("hook 指向不存在的脚本应当报红", 1, missing_hook)

    def bad_json():
        clean()
        write(good_settings, "{ this is not json ")
    case("settings.json 不是合法 JSON 应当报红", 1, bad_json)

    def broken_selftest():
        clean()
        write(os.path.join(SCRIPTS, "bad.py"),
              "import sys\nif '--selftest' in sys.argv:\n    sys.exit(1)\n")
    case("脚本自带的自测跑不过应当报红", 1, broken_selftest)

    def skill_no_desc():
        clean()
        write(os.path.join(SKILLS, "s1", "SKILL.md"), "---\nname: s1\n---\n")
    case("skill 的 frontmatter 缺 description 应当报红", 1, skill_no_desc)

    def goal_no_pred():
        clean()
        write(os.path.join(GOALS, "g.md"), "---\nname: g\n---\n")
    case("目标没有判定命令应当报红", 1, goal_no_pred)

    def goal_missing_script():
        clean()
        write(os.path.join(GOALS, "g.md"),
              f"---\nname: g\npredicate: python3 {os.path.join(SCRIPTS, 'nope.py')}\n---\n")
    # ⭐ 期望是 0（不报红）而不是 1：这一项**有意交给** check_memory_refs.sh 的 R2。
    #    这条用例留着不是多余的 —— 它把「这里不管这件事」这个分工写成了可执行的断言，
    #    将来谁顺手把这项加回来，这条会立刻变红提醒他重复了。
    case("目标引用不存在的脚本 —— 归 R2 管，这里不该报", 0, goal_missing_script)

    shutil.rmtree(tmp, ignore_errors=True)
    print("\n== SELFTEST: 全部通过 ==" if ok else "\n== SELFTEST: 有失败 ==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
