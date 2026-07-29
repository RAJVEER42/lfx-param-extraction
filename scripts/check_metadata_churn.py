#!/usr/bin/env python3
"""Re-derive the metadata-churn figures reported in analysis/v1_failures.md 6.2.

Kept as its own script rather than inlined into audit_claims.py, because it needs
the full parsed document per run rather than just the parameter names.

    python3 scripts/check_metadata_churn.py
"""
from __future__ import annotations
import collections, hashlib, json, pathlib, sys
REPO = pathlib.Path(__file__).resolve().parent.parent
FIELDS = ["defined_by", "trigger", "confidence", "type", "long_name"]


def unfence(r: str) -> str:
    r = r.strip()
    if r.startswith("```"):
        ls = r.splitlines()[1:]
        while ls and not ls[-1].strip().startswith("```"):
            ls.pop()
        if ls:
            ls.pop()
        return "\n".join(ls)
    return r


def main() -> int:
    import yaml
    cells: dict = collections.defaultdict(list)
    for f in sorted(REPO.glob("results/*/*/*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("status") == "error":
            continue
        try:
            doc = yaml.safe_load(unfence(d.get("content", "")))
            doc = doc if isinstance(doc, dict) else ({} if doc is None else None)
        except Exception:
            doc = None
        names = None if doc is None else tuple(sorted(
            {str(p.get("name", "")).upper() for p in (doc.get("parameters") or [])}))
        cells[(f.parts[-3], f.parts[-2], d["snippet"])].append(
            (hashlib.sha256(d.get("content", "").encode()).hexdigest(), names, doc))

    eligible = attr = reason_same_cand = 0
    for v in cells.values():
        if len(v) < 2 or any(x[1] is None for x in v):
            continue
        if not (len({x[0] for x in v}) > 1 and len({x[1] for x in v}) == 1):
            continue
        eligible += 1
        per: dict = collections.defaultdict(lambda: collections.defaultdict(set))
        maps = []
        for _, _, doc in v:
            for p in doc.get("parameters") or []:
                n = str(p.get("name", "")).upper()
                for fl in FIELDS:
                    per[n][fl].add(str(p.get(fl)))
            maps.append({" ".join(str(r.get("candidate")).lower().split()): str(r.get("reason"))
                         for r in (doc.get("rejected") or [])})
        if any(len(vals) > 1 for fs in per.values() for vals in fs.values()):
            attr += 1
        shared = [c for c in set().union(*[set(m) for m in maps]) if all(c in m for m in maps)]
        if any(len({m[c] for m in maps}) > 1 for c in shared):
            reason_same_cand += 1

    checks = [
        ("byte-different, name-identical cells", eligible, 13),
        ("cells where a per-parameter attribute moves", attr, 4),
        ("cells where the same candidate gets a different reason code", reason_same_cand, 1),
    ]
    bad = 0
    for label, got, want in checks:
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}: {got} (expected {want})")
    print(f"\n{len(checks)-bad}/{len(checks)} metadata-churn claims verified")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
