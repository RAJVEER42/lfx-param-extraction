#!/usr/bin/env python3
"""Classify an `isa_visible` justification as OPERATIONS, DISCOVERY, or MIXED.

Committed BEFORE the experiment-2 runs, so the classifier cannot be tuned to the
outcome it is used to score. See analysis/exp2_prereg.md.

The distinction being tested:

  OPERATIONS  the value matters because some instruction's defined behaviour
              depends on it. This is the correct ISA-visibility argument.
  DISCOVERY   the value matters because software can find it out, typically via
              the execution environment. This is the incorrect argument, since
              the execution environment is outside the ISA.

exp1_results.md section 4a observed that OPERATIONS-type models rejected cache
capacity and DISCOVERY-type models emitted it. This script applies that
classification mechanically so the association can be scored.

Usage:
    python3 scripts/classify_justification.py results/*/exp2a
    python3 scripts/classify_justification.py results/*/exp2a --json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

OPERATIONS = ["cbo", "cache management", "cache-management", "management operation",
              "instruction", "operates on", "operate on", "acts on", "act on"]
DISCOVERY = ["execution environment", "execution-environment", "discover",
             "discovery", "query", "queries", "querying"]

FALSE_POSITIVE = ["CAPACIT", "ORGANIZ", "CONFIGURATION"]


def classify(text: str) -> str:
    t = (text or "").lower()
    op = any(k in t for k in OPERATIONS)
    di = any(k in t for k in DISCOVERY)
    if op and di:
        return "MIXED"
    if op:
        return "OPERATIONS"
    if di:
        return "DISCOVERY"
    return "NEITHER"


def unfence(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        ls = raw.splitlines()[1:]
        while ls and not ls[-1].strip().startswith("```"):
            ls.pop()
        if ls:
            ls.pop()
        return "\n".join(ls)
    return raw


def score_run(rec: dict) -> dict | None:
    """Return the classification and whether the run emitted a false positive."""
    import yaml
    if rec.get("status") != "ok":
        return None
    try:
        doc = yaml.safe_load(unfence(rec.get("content", ""))) or {}
    except Exception:
        return None
    if not isinstance(doc, dict):
        return None
    params = doc.get("parameters") or []
    just, found_block = "", False
    for p in params:
        if not isinstance(p, dict):
            continue
        name = str(p.get("name", "")).upper()
        if "BLOCK_SIZE" in name:
            found_block = True
            just = str(p.get("isa_visible", ""))
    fp = any(any(k in str(p.get("name", "")).upper() for k in FALSE_POSITIVE)
             for p in params if isinstance(p, dict))
    return {
        "model": rec.get("model_requested"),
        "snippet": rec.get("snippet"),
        "run": rec.get("run_index"),
        "block_size_found": found_block,
        "class": classify(just) if found_block else "N/A",
        "false_positive": fp,
        "justification": just[:150],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = []
    for d in args.dirs:
        p = pathlib.Path(d)
        files = sorted(p.glob("*.json")) if p.is_dir() else [p]
        for f in files:
            r = score_run(json.loads(f.read_text(encoding="utf-8")))
            if r:
                rows.append(r)

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print(f"{'model':34} {'run':>3}  {'blk':>3}  {'class':<11} {'FP':>3}")
    print("-" * 66)
    for r in rows:
        print(f"{str(r['model'])[:34]:34} {r['run']:>3}  "
              f"{'yes' if r['block_size_found'] else 'no':>3}  {r['class']:<11} "
              f"{'YES' if r['false_positive'] else 'no':>3}")

    # the 2x2 the preregistration asks for
    scored = [r for r in rows if r["class"] in ("OPERATIONS", "DISCOVERY")]
    excluded = [r for r in rows if r["class"] not in ("OPERATIONS", "DISCOVERY")]
    print()
    print("  2x2, MIXED and N/A excluded as preregistered:")
    print(f"    {'':14} {'no FP':>7} {'FP':>7}")
    for cls in ("OPERATIONS", "DISCOVERY"):
        no_fp = sum(1 for r in scored if r["class"] == cls and not r["false_positive"])
        fp = sum(1 for r in scored if r["class"] == cls and r["false_positive"])
        print(f"    {cls:14} {no_fp:>7} {fp:>7}")
    agree = sum(1 for r in scored
                if (r["class"] == "OPERATIONS") == (not r["false_positive"]))
    print(f"\n  association holds in {agree} of {len(scored)} scored runs "
          f"({len(excluded)} excluded: "
          f"{', '.join(sorted({r['class'] for r in excluded})) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
