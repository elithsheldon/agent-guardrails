#!/usr/bin/env python3
"""audit_hash.py — 审计结论与文件内容的哈希绑定（防「改了文件还引用旧审计结论」自欺）.

蓝本: wanshuiyin/ARIS (Auto-claude-code-research-in-sleep) 的
skills/shared-references/assurance-contract.md（audited_input_hashes 语义）+
tools/verify_paper_audits.sh（rehash→STALE 判定）. 极简移植, 2026-07-22.

用法:
  audit_hash.py record --ledger a.json --audit name --verdict PASS file1 file2 ...
  audit_hash.py verify --ledger a.json [--audit name]

verify: 全部一致=FRESH; 任一哈希变=STALE(列出变了哪些); 文件消失=MISSING.
退出码: 有 STALE/MISSING = 1.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path):
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"audits": {}}


def cmd_record(args):
    ledger = _load(args.ledger)
    files = {os.path.abspath(f): _sha256(os.path.abspath(f)) for f in args.files}
    entry = {"verdict": args.verdict, "recorded_at": _now(), "files": files}
    old = ledger["audits"].get(args.audit)
    if old is not None:
        history = old.pop("history", [])
        history.append(old)          # 覆盖前把旧条目压入 history, 永不丢
        entry["history"] = history
    ledger["audits"][args.audit] = entry
    with open(args.ledger, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=2, ensure_ascii=False)
    print(f"recorded audit '{args.audit}' ({args.verdict}), {len(files)} files -> {args.ledger}")
    return 0


def cmd_verify(args):
    ledger = _load(args.ledger)
    names = [args.audit] if args.audit else sorted(ledger["audits"])
    bad = 0
    for name in names:
        entry = ledger["audits"].get(name)
        if entry is None:
            print(f"== {name} ==\n  UNKNOWN: 台账里没有这条 audit")
            bad += 1
            continue
        changed, missing = [], []
        for path, recorded in entry["files"].items():
            if not os.path.isfile(path):
                missing.append(path)
            elif _sha256(path) != recorded:
                changed.append(path)
        if missing:
            status = "MISSING"
        elif changed:
            status = "STALE"
        else:
            status = "FRESH"
        print(f"== {name} (verdict={entry['verdict']}, recorded={entry['recorded_at']}) ==")
        print(f"  {status}: {len(entry['files'])} files 登记")
        for p in changed:
            print(f"  changed: {p}")
        for p in missing:
            print(f"  missing: {p}")
        if status != "FRESH":
            bad += 1
    print(f"\n== 结论: {'FRESH' if bad == 0 else f'{bad} 条 audit 失效 (结论不再绑定当前文件, 需重审)'} ==")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--ledger", required=True)
    r.add_argument("--audit", required=True)
    r.add_argument("--verdict", required=True)
    r.add_argument("files", nargs="+")
    v = sub.add_parser("verify")
    v.add_argument("--ledger", required=True)
    v.add_argument("--audit", default=None)
    a = ap.parse_args()
    return cmd_record(a) if a.cmd == "record" else cmd_verify(a)


if __name__ == "__main__":
    sys.exit(main())
