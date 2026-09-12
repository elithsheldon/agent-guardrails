#!/usr/bin/env python3
"""memory 易腐状态检查 (goal: memory-state, 2026-08-10 加)。

事故来源: 一个教材战役的 memory 文件断言「已批准但一次都没开跑」, 而战役其实
四天前就跑完了, 真状态只在 vault LEDGER 里。会话读了 memory 就信了, 于是向用户
报告「战役正好轮到开跑」。当天更正了正文, 但同一句假话还留在该文件的
frontmatter `description:` 和 MEMORY.md 的索引行里 —— 状态事实存了三份, 更正只
到了一份。

本检查器管的就是这个形状: **索引行与 description 是耐久文档, 只该说一个文件是
关于什么的, 不该说一个项目现在站在哪里。** 项目站位是易腐事实, 归各自的活单源
(vault LEDGER / EXPERIMENT_PLAN / crontab / TODO.md)。

扫描面 (只读, 永不自动改):
  1. MEMORY.md 的索引行  `- [标题](file.md) — 摘要`  (标题+摘要全扫)
  2. 每个 memory 文件 frontmatter 的 `description:` 字段

四类命中 (每一条都是「耐久文档断言了易腐状态」):
  W1 状态词   —— 待批/待拍板/已批/在飞/下一步/已挂/收官/approved/pending/
                 awaiting/in flight/next step/already wired/done ...
  W2 cron 表达式 —— 排程是机器状态, 归 crontab, 不归散文
  W3 终端窗口地址 —— `main:5`、`窗口 j-seeds`; 窗口随会话消失, 写进文档必朽
  W4 日期字面量 —— 会议截止日、立项日这类会被官方改掉或被时间超过的数字

三类可机械证伪的矛盾 (ERROR, 直接决定退出码, 永不进 baseline):
  E1 幽灵 cron —— 文档宣称某脚本在定时跑, `crontab -l` 里根本没有它
  E2 索引行 ↔ description 状态互斥 —— 一处只说收官, 另一处说还在等用户拍板
  E3 截止日没说是谁的 —— 写了「截止 + 摘要/全文 + 日期」却不说是官方硬截止还是
                        自定提前锚 (同一会议在库里存了两套数字时, 单读一处必错)

退出码: 0 = 无 ERROR 且 W 类无新增; 1 = 有 ERROR 或有新增 W 命中; 2 = 检查器自身
跑不起来 (verify_goals.sh 把 2 记 CHECK-ERROR, 与产物违规分开)。

存量 W 命中走 baseline 增量制 (同 check_bare_refs_delta.sh 的先例): 冻结在
goals/baselines/memory-state.txt, 只有【新增】命中才 FAIL。处置新增命中 = 把状态
从耐久文档里删掉、改成指向活单源的指针; 确属不朽事实才手动追加进 baseline。

用法:
  check_memory_state.py [--memory-dir DIR] [--baseline FILE]
                        [--write-baseline FILE] [--all] [--selftest]
  --all            W 类逐条全列 (默认每类截断 30 行)
  --write-baseline 把当前 W 命中写成新 baseline (人工动作, 需在报告里说明理由)
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

MEMORY_DIR = Path.home() / ".claude" / "projects" / "-home-mil-n-chang" / "memory"
BASELINE = Path.home() / ".claude" / "goals" / "baselines" / "memory-state.txt"
MAX_SHOW = 30

# ---------------------------------------------------------------- vocabulary
# 分三档不是为了宽严, 是为了让报告能读: OPEN 会翻脸, WIRED 可被 crontab 证伪,
# DONE 是吸收态 (不会自己变假, 但会掩盖「后面又开了新阶段」)。
ZH_OPEN = ["待批", "待拍板", "待用户", "待开", "待定", "待签", "待验", "待跑",
           "待办", "待评", "待收", "待补", "待同步", "待分诊", "待处理", "待读",
           "待议", "已批准", "已批", "在飞", "进行中", "未开工", "没开跑",
           "下一步", "下步", "断点", "提案待", "冲刺"]
ZH_WIRED = ["已挂", "已装", "已配", "已接", "已上线", "已启用", "已就绪",
            "已焊", "已发射", "已开跑", "常驻中"]
ZH_DONE = ["收官", "已完成", "已完工", "完工", "已交付", "已归档", "已退役"]

EN_OPEN = ["approved", "pending", "awaiting", "in flight", "in-flight",
           "next step", "next steps", "in progress", "in-progress", "ongoing",
           "blocked", "queued", "tbd", "to be decided", "not started",
           "upcoming", "will start", "about to"]
EN_WIRED = ["already wired", "wired", "installed", "enabled", "armed",
            "scheduled", "running"]
EN_DONE = ["done", "finished", "completed", "closed", "shipped", "delivered",
           "retired"]

STATUS_SETS = [("OPEN", ZH_OPEN, EN_OPEN),
               ("WIRED", ZH_WIRED, EN_WIRED),
               ("DONE", ZH_DONE, EN_DONE)]

# 五段 cron 表达式。至少两段含 `*` —— 纯数字串 (实验读数 "1 2 3 4 5") 不是排程。
CRON_RE = re.compile(r"(?<![\w*/-])((?:[*\d][\d*/,-]*)(?:\s+[*\d][\d*/,-]*){4})(?![\w/-])")
SCRIPT_RE = re.compile(r"[\w./~$-]+\.(?:sh|py)")

# tmux 目标: `main:5` / `main:5.1`。端口号 (arowana:8080) 位数多, 排除在外;
# URL 里的 host:port 也排除。
WINDOW_ADDR_RE = re.compile(r"(?<![\w/:])([A-Za-z][\w-]{1,20}):(\d{1,2})(?:\.(\d{1,2}))?(?![\w.:])")
WINDOW_NAME_RE = re.compile(r"(?:窗口|window|pane)\s*[「『\"'`]?([A-Za-z][\w-]{2,24})")

DATE_ISO_RE = re.compile(r"\b20\d\d[-/](\d{1,2})[-/](\d{1,2})\b")
DATE_PAD_RE = re.compile(r"(?<![\d/-])(0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])(?![\d/-])")
DATE_SLASH_RE = re.compile(r"(?<![\d/-])([1-9]|1[0-2])/([1-9]|[12]\d|3[01])(?![\d/-])")
DATE_CONTEXT = ("截止", "deadline", "AoE", "摘要", "全文", "abstract", "due")

DEADLINE_WORDS = ("截止", "deadline", "AoE")
PHASE_WORDS = ("摘要", "全文", "abstract", "full paper")
# 归属标记: 断言一个截止日时必须说清这是谁定的 —— 官方硬截止, 还是自己提前排的锚。
ATTRIB_WORDS = ("官方", "official", "内部锚", "内部", "自定", "self-imposed",
                "internal", "锚")
DEADLINE_PROX = 40  # 截止词/阶段词须落在日期前后这么多字符内才算同一句断言
# 「截止」的非投稿义: 模型知识截止、「截止到今天」的时点义 —— 判前先从窗口抹掉,
# 否则 "审稿 agent 知识截止 artifact（scoop 三篇 07-09）" 会被当成一句截止日断言。
DEADLINE_NEG = ("知识截止", "knowledge cutoff", "训练截止", "数据截止",
                "截止到", "截止至", "截止目前", "截止当前")

INDEX_RE = re.compile(r"^-\s*\[(?P<title>[^\]]*)\]\((?P<target>[^)]+\.md)\)"
                      r"\s*(?:—|–|-)?\s*(?P<blurb>.*)$")


# ------------------------------------------------------------------ scanning
def status_hits(text):
    """[(class, token)] — 长词优先, 重叠的短词不重复报 (已批准 不再报 已批)。"""
    spans, hits = [], []
    cands = []
    for cls, zh, en in STATUS_SETS:
        for w in zh:
            # 中文没有 \b, 裸匹配会咬进更大的词里: 「认真对待用户的贡献」被读成状态词
            # 「待用户」, 「Q 表 360 项」被别的检查器读成「表 3」是同一类。凡以「待」
            # 起头的状态词, 前面若是与「待」成词的动词(对待/等待/期待/看待/招待/优待/
            # 虐待/亏待), 则该处不是状态词。(2026-08-15 加, 起因=一条真实误报卡住停止门)
            pat = re.escape(w)
            if w.startswith("待"):
                pat = r"(?<![对等期看招优虐亏])" + pat
            cands.append((cls, w, [m.start() for m in
                                   re.finditer(pat, text)], len(w)))
        for w in en:
            cands.append((cls, w, [m.start() for m in
                                   re.finditer(r"\b" + re.escape(w) + r"\b",
                                               text, re.IGNORECASE)], len(w)))
    for cls, w, starts, ln in sorted(cands, key=lambda c: -c[3]):
        for s in starts:
            if any(s < e2 and s + ln > s2 for s2, e2 in spans):
                continue
            spans.append((s, s + ln))
            hits.append((cls, w))
    return hits


def cron_spans(text):
    """[(expr, start, end)] — 五段 cron 表达式及其位置。"""
    out = []
    for m in CRON_RE.finditer(text):
        expr = m.group(1)
        fields = expr.split()
        if sum(1 for f in fields if "*" in f) < 2:
            continue
        out.append((expr, m.start(1), m.end(1)))
    return out


def cron_hits(text):
    return [e for e, _, _ in cron_spans(text)]


def window_hits(text):
    out = []
    for m in WINDOW_ADDR_RE.finditer(text):
        out.append(m.group(0))
    for m in WINDOW_NAME_RE.finditer(text):
        out.append(m.group(0).strip())
    return out


def date_hits(text):
    out = []
    for m in DATE_ISO_RE.finditer(text):
        out.append(m.group(0))
    for m in DATE_PAD_RE.finditer(text):
        out.append(m.group(0))
    if any(k in text for k in DATE_CONTEXT):
        for m in DATE_SLASH_RE.finditer(text):
            out.append(m.group(0))
    return out


def scan_line(text):
    """一条耐久文本 -> [(class, token)]。"""
    found = [("状态词/" + cls, tok) for cls, tok in status_hits(text)]
    found += [("cron", t) for t in cron_hits(text)]
    found += [("窗口地址", t) for t in window_hits(text)]
    found += [("日期", t) for t in date_hits(text)]
    return found


def read_description(path):
    """frontmatter 的 description: 值 (单行, 去引号); 没有则 None。"""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for i, ln in enumerate(lines[1:], 1):
        if ln.strip() == "---":
            return None
        if ln.startswith("description:"):
            v = ln[len("description:"):].strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            return v
    return None


def durable_lines(mem_dir):
    """[(kind, key, path, lineno, text)] — 全部耐久文本面。"""
    out = []
    index = mem_dir / "MEMORY.md"
    if index.exists():
        for n, ln in enumerate(index.read_text(encoding="utf-8",
                                               errors="replace").splitlines(), 1):
            m = INDEX_RE.match(ln.strip())
            if m:
                out.append(("INDEX", m.group("target"), index, n,
                            m.group("title") + " — " + m.group("blurb")))
    for p in sorted(mem_dir.glob("*.md")) + sorted(mem_dir.glob("*/*.md")):
        if p.name == "MEMORY.md":
            continue
        d = read_description(p)
        if d:
            rel = str(p.relative_to(mem_dir))
            out.append(("DESC", rel, p, 3, d))
    return out


# --------------------------------------------------------- E1: 幽灵 cron
def crontab_text():
    """crontab -l 的输出; 拿不到返回 None (fail-open, 不把环境问题记成产物违规)。"""
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True,
                           timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


GHOST_GAP = 40  # 脚本名与 cron 表达式的最大间隔 (字符)


def cron_script_pairs(text):
    """[(script, expr)] — 只配对【彼此相邻】的脚本名与 cron 表达式。

    一行里常常并列好几个脚本名和一个 cron 表达式 ("`a.sh` + cron `X` ... 顺带
    提一句 b.py"), 早期版本把该行所有脚本都算成受该 cron 管辖 → 假阳性淹没真
    命中。真正的宣称形态总是紧挨着的:
        cron `0 * * * * ~/x/overnight_agent.sh`      (间隔 0)
        **`recover_pilot.py`** (cron `22 * * * *`)   (间隔 ~8)
    因此只认间隔 ≤ GHOST_GAP 的配对; 更远的同行脚本名视为无关提及。
    """
    spans = cron_spans(text)
    if not spans:
        return []
    pairs = []
    for m in SCRIPT_RE.finditer(text):
        s0, s1 = m.start(), m.end()
        best = None
        for expr, c0, c1 in spans:
            gap = c0 - s1 if s1 <= c0 else (s0 - c1 if c1 <= s0 else 0)
            # 一行里并列多条 cron 时取【最近】的那条, 不是文档序第一条 ——
            # "`A` a.sh + `B` b.sh" 里 b.sh 归 B, 否则排程漂移会报错对象。
            if gap <= GHOST_GAP and (best is None or gap < best[0]):
                best = (gap, expr)
        if best:
            pairs.append((Path(m.group(0)).name, best[1]))
    return pairs


def ghost_crons(mem_dir, cron_text):
    """正文里带五段 cron 表达式且紧挨着点名脚本的行, 拿脚本名去 crontab 对账。"""
    ghosts, drifts = [], []
    if cron_text is None:
        return ghosts, drifts
    for p in sorted(mem_dir.glob("*.md")) + sorted(mem_dir.glob("*/*.md")):
        rel = str(p.relative_to(mem_dir))
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for n, ln in enumerate(lines, 1):
            seen = set()
            for s, expr in cron_script_pairs(ln):
                if s in seen:
                    continue
                seen.add(s)
                if s not in cron_text:
                    ghosts.append((rel, n, s, expr, ln.strip()[:150]))
                elif expr not in cron_text:
                    drifts.append((rel, n, s, expr))
    return ghosts, drifts


# --------------------------------------- E2: 索引行 ↔ description 状态互斥
def status_classes(text):
    return {cls for cls, _ in status_hits(text)}


def index_desc_conflicts(mem_dir, lines):
    """索引行只说 DONE, 而目标文件的 description 还说 OPEN —— 更正只到了一份。"""
    desc = {key: text for kind, key, _, _, text in lines if kind == "DESC"}
    out = []
    for kind, key, path, n, text in lines:
        if kind != "INDEX" or key not in desc:
            continue
        icls, dcls = status_classes(text), status_classes(desc[key])
        if "DONE" in icls and "OPEN" not in icls and "OPEN" in dcls:
            out.append((key, n, text[:90], desc[key][:110]))
    return out


# ------------------------------------------ E3: 同文件内截止日自相矛盾
def norm_dates(text):
    got = set()
    for m in DATE_ISO_RE.finditer(text):
        got.add((int(m.group(1)), int(m.group(2))))
    for m in DATE_PAD_RE.finditer(text):
        got.add((int(m.group(1)), int(m.group(2))))
    for m in DATE_SLASH_RE.finditer(text):
        got.add((int(m.group(1)), int(m.group(2))))
    return got


def deadline_unattributed(mem_dir):
    """截止日期必须说明是谁的日期 (ERROR)。

    事故形态: 同一个会议截止日在库里存了八份、两套数字 (官方复核值 vs 蓄意提前
    一周的内部锚), 每份都把自己那套写成「实际截止」。任何一份被单独读到, 读者
    都无从判断手上这个数是硬截止还是自定缓冲。

    早期版本比较同文件内两行的日期【集合】是否互相包含, 判「自相矛盾」。那条
    规则在正确写法下反而翻脸: 一行同时写出官方值和内部锚以后, 两行的集合各自
    还夹着不相干的记录日 (08-04 / 08-10), 于是互不包含 → 假阳性。而且它只看得
    见同文件内的打架, 跨文件的两套数字照样漏。

    改成单行可判的归属规则: 一行同时出现【截止词 + 阶段词 + 日期】就是在断言某
    个截止日, 此时必须带归属标记 (官方 / official / 内部锚 / 自定 ...)。不带 =
    ERROR。这条既覆盖原事故 (旧写法「<venue> 实际=9/11 abstract」无归属→报),
    又对修好的写法零误报, 且不依赖跨行比较。
    """
    out = []
    for p in sorted(mem_dir.glob("*.md")) + sorted(mem_dir.glob("*/*.md")):
        rel = str(p.relative_to(mem_dir))
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for n, ln in enumerate(lines, 1):
            for dates in deadline_unattributed_text(ln):
                out.append((rel, n, dates, ln.strip()[:150]))
    return out


def date_spans(text):
    """[(月, 日, start, end)] — 三种日期写法及其位置。"""
    out = []
    for rx in (DATE_ISO_RE, DATE_PAD_RE, DATE_SLASH_RE):
        for m in rx.finditer(text):
            out.append((int(m.group(1)), int(m.group(2)), m.start(), m.end()))
    return out


def deadline_unattributed_text(ln):
    """单行判据 -> [] 干净 / [日期列表] 断言了截止日却没说是谁的。

    截止词/阶段词/日期必须【彼此靠近】才算一句截止断言。memory 里的行动辄几千
    字, 只要求三者同行会把「单约束 tight 3/5 seed」这种计数配上远处另一句里的
    「知识截止 artifact」和「abstract」误判成截止日。真断言总是挤在一处:
        「摘要截止 9/18」「abstract 9/11 / 全文 9/16（AoE）」
    归属标记则不要求靠近 —— 同一行任何位置说清「官方/内部锚」都算数。
    """
    if not any(w in strip_neg(ln) for w in DEADLINE_WORDS):
        return []
    low = ln.lower()
    if any(w.lower() in low for w in ATTRIB_WORDS):
        return []
    hits = set()
    for mo, dy, s, e in date_spans(ln):
        win = strip_neg(ln[max(0, s - DEADLINE_PROX):e + DEADLINE_PROX])
        wlow = win.lower()
        if any(w in win for w in DEADLINE_WORDS) and \
                any(w.lower() in wlow for w in PHASE_WORDS):
            hits.add((mo, dy))
    return [sorted(hits)] if hits else []


def strip_neg(text):
    """抹掉「截止」的非投稿义用法, 再判是不是一句截止日断言。"""
    for neg in DEADLINE_NEG:
        text = re.sub(re.escape(neg), "", text, flags=re.IGNORECASE)
    return text


# --------------------------------------------------------------- reporting
def signature(kind, key, cls, token):
    return f"{kind}\t{key}\t{cls}\t{token}"


def collect(mem_dir):
    lines = durable_lines(mem_dir)
    rows = []
    for kind, key, path, n, text in lines:
        for cls, token in scan_line(text):
            rows.append((signature(kind, key, cls, token), kind, key, path.name,
                         n, cls, token, text[:110]))
    return lines, rows


def run(mem_dir, baseline_path, show_all=False, out=print):
    lines, rows = collect(mem_dir)
    n_index = sum(1 for k, *_ in lines if k == "INDEX")
    n_desc = sum(1 for k, *_ in lines if k == "DESC")
    out(f"扫描面: MEMORY.md 索引行 {n_index} 条 · description 字段 {n_desc} 个"
        f" ({mem_dir})")

    ctext = crontab_text()
    ghosts, drifts = ghost_crons(mem_dir, ctext)
    conflicts = index_desc_conflicts(mem_dir, lines)
    dl = deadline_unattributed(mem_dir)

    out("\n== E1 幽灵 cron (ERROR — 文档说在定时跑, crontab -l 里没有) ==")
    if ctext is None:
        out("SKIP: 读不到 crontab -l (fail-open, 不判违规)")
    elif ghosts:
        for rel, n, s, expr, ln in ghosts:
            out(f"{rel}:{n}: {s} 宣称 `{expr}` 但不在 crontab —— {ln}")
    else:
        out("OK")
    if drifts:
        out("  WARN 排程漂移 (脚本在 crontab, 但时间跟文档写的不一样):")
        for rel, n, s, expr in drifts:
            out(f"    {rel}:{n}: {s} 文档写 `{expr}`")

    out("\n== E2 索引行 ↔ description 状态互斥 (ERROR — 更正只到了一份) ==")
    if conflicts:
        for key, n, itxt, dtxt in conflicts:
            out(f"{key}: MEMORY.md:{n} 说完了 << {itxt} >>")
            out(f"{' ' * len(key)}  description 说还开着 << {dtxt} >>")
    else:
        out("OK")

    out("\n== E3 截止日没说是谁的 (ERROR — 官方硬截止? 还是自定提前锚?) ==")
    if dl:
        for rel, n, dates, ln in dl:
            out(f"{rel}:{n}: {dates} 无归属标记 —— {ln}")
    else:
        out("OK")

    groups = {}
    for row in rows:
        groups.setdefault(row[5], []).append(row)
    base = set()
    if baseline_path and Path(baseline_path).exists():
        base = {l for l in Path(baseline_path).read_text(
            encoding="utf-8").splitlines() if l.strip()}
    new_rows = [r for r in rows if r[0] not in base]

    out(f"\n== W 类命中清单 (耐久文档里的易腐断言; 存量 baseline "
        f"{len(base)} 条, 本次 {len(rows)} 条, 新增 {len(new_rows)} 条) ==")
    for cls in sorted(groups):
        rs = groups[cls]
        out(f"\n-- {cls} ({len(rs)}) --")
        shown = rs if show_all else rs[:MAX_SHOW]
        for sig, kind, key, fname, n, c, token, text in shown:
            mark = "NEW " if sig not in base else "    "
            where = f"MEMORY.md:{n}[{key}]" if kind == "INDEX" else f"{key}:description"
            out(f"{mark}{where}  «{token}»  {text}")
        if len(rs) > len(shown):
            out(f"    ...(+{len(rs) - len(shown)} 条, --all 看全)")

    n_err = len(ghosts) + len(conflicts) + len(dl)
    if new_rows:
        out(f"\n新增 W 命中 {len(new_rows)} 条 —— 处置: 把状态从索引行/description "
            f"里删掉, 改成指向活单源的指针; 确属不朽事实才追加进 {baseline_path}")
    ok = n_err == 0 and not new_rows
    out(f"\n== 结论: {'PASS' if ok else 'FAIL'} (ERROR {n_err} · 新增 W "
        f"{len(new_rows)}) ==")
    return 0 if ok else 1


# ---------------------------------------------------------------- selftest
def _write(d, name, front_desc, body=""):
    p = Path(d) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\nname: x\ndescription: " + front_desc +
                 "\n---\n\n" + body + "\n", encoding="utf-8")
    return p


def selftest():
    fails = 0

    def check(name, cond):
        nonlocal fails
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        fails += 0 if cond else 1

    # --- 单元: 词表与正则
    check("状态词 OPEN 认得中文待批", ("OPEN", "待批") in status_hits("立项待批"))
    check("状态词 OPEN 认得 approved", any(c == "OPEN" and t == "approved"
                                          for c, t in status_hits("ALL approved")))
    check("状态词 DONE 认得收官", any(c == "DONE" for c, t in status_hits("全收官")))
    check("已批准 不再重复报 已批",
          [t for c, t in status_hits("已批准")] == ["已批准"])
    check("cron 五段认出来", cron_hits("cron `0 * * * *` hourly") == ["0 * * * *"])
    check("纯数字读数不当 cron", cron_hits("seeds 1 2 3 4 5") == [])
    check("窗口地址 main:5 认出来", "main:5" in window_hits("main:5 全权委托窗口"))
    check("host:8080 不当窗口地址", window_hits("arowana:8080") == [])
    check("具名窗口认出来", any("j-seeds" in h for h in window_hits("已派专用窗口 j-seeds")))
    check("ISO 日期认出来", "2026-07-24" in date_hits("立项 2026-07-24"))
    check("补零月日认出来", "08-06" in date_hits("08-06 收工"))
    check("裸 9/11 只在截止语境算日期",
          date_hits("9/11 AoE") == ["9/11"] and date_hits("消融 9/11 任务") == [])
    check("日期归一: ISO 与短式同值",
          norm_dates("2026-09-18") == norm_dates("9/18") == {(9, 18)})

    # --- 集成: 植入缺陷的小语料
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        _write(d, "project_camp.md", "战役（立项待批）——16 本新书入库",
               "正文\n")
        _write(d, "project_clean.md", "某学科建卡工序；计划单源=vault LEDGER",
               "正文\n")
        _write(d, "project_ghost.md", "reporter 说明",
               "- `zzz_ghost_job.py` (cron `22 * * * *`): 定时跑\n")
        _write(d, "reference_dl.md", "会议投稿要求单源",
               "- 摘要截止 9/18、全文截止 9/25\n"
               "- ⚠️ 截止日更正: abstract 9/11 / 全文 9/16\n")
        _write(d, "reference_dl_ok.md", "会议投稿要求单源 (归属写清版)",
               "- 官方截止: 摘要 9/18、全文 9/25; 内部锚提前一周=9/11 / 9/16\n")
        (d / "MEMORY.md").write_text(
            "- [战役（P1–P9 已批）](project_camp.md) — P1 先行；单源=vault LEDGER\n"
            "- [✅ 某学科收官](project_clean.md) — 117 卡\n"
            "- [会议投稿要求](reference_dl.md) — 9/11+9/16 AoE\n",
            encoding="utf-8")

        lines, rows = collect(d)
        check("索引行被扫到", sum(1 for k, *_ in lines if k == "INDEX") == 3)
        check("description 被扫到", sum(1 for k, *_ in lines if k == "DESC") == 5)
        sigs = {r[0] for r in rows}
        check("索引行的『已批』被抓",
              signature("INDEX", "project_camp.md", "状态词/OPEN", "已批") in sigs)
        check("description 的『待批』被抓",
              signature("DESC", "project_camp.md", "状态词/OPEN", "待批") in sigs)
        check("索引行的截止日期被抓",
              signature("INDEX", "reference_dl.md", "日期", "9/11") in sigs)
        check("干净的 description 零命中",
              not any(r[2] == "project_clean.md" and r[1] == "DESC" for r in rows))

        ghosts, _ = ghost_crons(d, "0 5 * * * /bin/true\n")
        check("幽灵 cron 被抓", len(ghosts) == 1 and ghosts[0][2] == "zzz_ghost_job.py")
        ghosts2, _ = ghost_crons(d, "22 * * * * zzz_ghost_job.py\n")
        check("真在 crontab 的 cron 不报", ghosts2 == [])
        check("crontab 读不到时 fail-open", ghost_crons(d, None) == ([], []))

        # E1 相邻性: 同一行里离 cron 表达式很远的脚本名不算受它管辖
        near = cron_script_pairs("`a_near.sh` + cron `*/10 * * * *` 幂等")
        check("E1 相邻脚本配对上", [s for s, _ in near] == ["a_near.sh"])
        far = cron_script_pairs(
            "cron `*/10 * * * *` 跑完发网格" + "，" * 60 + "顺带提一句 b_far.py")
        check("E1 远处同行脚本名不配对", far == [])
        check("E1 并列两条 cron 时各归各的最近者",
              cron_script_pairs("`30 21 * * *` a.sh + `0 22 * * 0` b.sh") ==
              [("a.sh", "30 21 * * *"), ("b.sh", "0 22 * * 0")])

        # E3: 无归属的截止日必报, 写清官方/内部锚的零报
        dlrows = deadline_unattributed(d)
        check("E3 抓到无归属截止日", len(dlrows) == 2
              and all(r[0] == "reference_dl.md" for r in dlrows))
        check("E3 对写清归属的行零误报",
              not any(r[0] == "reference_dl_ok.md" for r in dlrows))
        check("E3 不再跨行比集合 (夹着无关记录日也不翻脸)",
              deadline_unattributed_text(
                  "官方截止 摘要 9/18 全文 9/25（08-04 复核）") == [] and
              deadline_unattributed_text(
                  "内部锚 摘要 9/11 全文 9/16（08-10 记）") == [])
        check("E3 真断言仍被抓 (无归属)",
              deadline_unattributed_text("ICLR 实际=9/11 abstract / 9/16 全文（AoE）")
              == [[(9, 11), (9, 16)]])
        # 长行远距离共现: 计数 3/5 + 别处的「知识截止」「abstract」不是截止断言
        check("E3 长行里远距离共现不误判",
              deadline_unattributed_text(
                  "单约束 tight 3/5 seed 塌到 .01" + "，" * 80 +
                  "「未来日期文献」是审稿 agent 知识截止 artifact；abstract 已改")
              == [])
        check("E3 「知识截止」不是投稿截止",
              deadline_unattributed_text(
                  "审稿 agent 知识截止 artifact（scoop 三篇 07-09 已核）；abstract 已改")
              == [])

        # E2 需要索引行只说完了、description 还说开着
        _write(d, "project_shut.md", "计划已写就待用户拍板 D1–D5")
        (d / "MEMORY.md").write_text(
            (d / "MEMORY.md").read_text(encoding="utf-8") +
            "- [✅ 某重组收官](project_shut.md) — 117 卡\n", encoding="utf-8")
        lines2, _ = collect(d)
        conf = index_desc_conflicts(d, lines2)
        check("E2 抓到索引说完了/description 说没完",
              len(conf) == 1 and conf[0][0] == "project_shut.md")

        buf = []
        rc = run(d, None, out=buf.append)
        check("有缺陷时退出码 1", rc == 1)

        # baseline: 冻结全部存量后, 只剩 ERROR 决定退出码
        bl = d / "baseline.txt"
        _, rows2 = collect(d)
        bl.write_text("\n".join(sorted({r[0] for r in rows2})) + "\n",
                      encoding="utf-8")
        buf = []
        rc = run(d, bl, out=buf.append)
        check("冻结存量后仍因 ERROR FAIL", rc == 1)
        check("报告里出现新增 0", "新增 0 条" in "\n".join(buf))

    print(f"selftest: {'all green' if fails == 0 else str(fails) + ' failing'}")
    return 1 if fails else 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    mem = Path(argv[argv.index("--memory-dir") + 1]) if "--memory-dir" in argv \
        else MEMORY_DIR
    if not mem.is_dir():
        print(f"CHECK-ERROR: memory 目录不存在: {mem}")
        return 2
    if "--write-baseline" in argv:
        target = Path(argv[argv.index("--write-baseline") + 1])
        _, rows = collect(mem)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(sorted({r[0] for r in rows})) + "\n",
                          encoding="utf-8")
        print(f"baseline written: {target} ({len(set(r[0] for r in rows))} 条)")
        return 0
    base = Path(argv[argv.index("--baseline") + 1]) if "--baseline" in argv \
        else BASELINE
    return run(mem, base, show_all="--all" in argv)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:  # 检查器自身炸了 = CHECK-ERROR, 不是产物违规
        print(f"CHECK-ERROR: {type(e).__name__}: {e}")
        sys.exit(2)
