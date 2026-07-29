#!/usr/bin/env python3
"""Re-derive every quantitative claim in the submission from the raw data.

A submission that asserts numbers nobody recomputed is asking to be trusted.
This script recomputes them from results/ and the committed artifacts, and fails
loudly on any mismatch. Run it before submitting, and after any edit.

    python3 scripts/audit_claims.py [--udb <path>]

Exit code is nonzero if any claim fails.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
HEADER = ("Source:", "Provided ")

results: list[tuple[bool, str, str]] = []


def check(label: str, actual, expected) -> None:
    ok = actual == expected
    results.append((ok, label, f"expected {expected!r}, got {actual!r}"))


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


def load_runs(version: str) -> list[dict]:
    out = []
    for f in sorted(REPO.glob(f"results/*/{version}/*.json")):
        out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def names_in(rec: dict) -> list[str]:
    import yaml
    try:
        doc = yaml.safe_load(unfence(rec.get("content", ""))) or {}
    except Exception:
        return []
    if not isinstance(doc, dict):
        return []
    return [str(p.get("name")) for p in (doc.get("parameters") or []) if isinstance(p, dict)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--udb")
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        print(
            "PyYAML is required here: the audit parses parameters.yaml and the UDB\n"
            "parameter files in order to re-derive the numbers.\n\n"
            "    pip install pyyaml\n\n"
            "The trigger scan and the grounding check (run.sh stages 1-2) do not need\n"
            "it and are unaffected.",
            file=sys.stderr,
        )
        return 2

    # --- snippets -----------------------------------------------------------
    bodies = {}
    for key in ("priv_19_3_1", "priv_2_1"):
        lines = (REPO / "snippets" / f"{key}.txt").read_text(encoding="utf-8").splitlines()
        bodies[key] = "\n".join(l for l in lines if not l.startswith(HEADER)).strip()

    check("snippet 19.3.1 word count = 96", len(bodies["priv_19_3_1"].split()), 96)
    check("snippet 2.1 word count = 89", len(bodies["priv_2_1"].split()), 89)
    check("both snippets = 185 words",
          sum(len(b.split()) for b in bodies.values()), 185)

    BRIEF = ["may", "might", "should", "optional", "optionally",
             "implementation defined", "implementation-defined",
             "implementation specific", "implementation-specific"]
    total = 0
    for b in bodies.values():
        for t in BRIEF:
            total += len(re.findall(r"(?<![A-Za-z-])" + re.escape(t) + r"(?![A-Za-z])", b, re.I))
    check("exactly 1 brief-listed signal phrase across both snippets", total, 1)
    check("snippet 2.1 has 0 signal phrases",
          sum(len(re.findall(r"(?<![A-Za-z-])" + re.escape(t) + r"(?![A-Za-z])", bodies["priv_2_1"], re.I))
              for t in BRIEF), 0)
    check("19.3.1 contains 'shall'", "shall" in bodies["priv_19_3_1"].lower(), True)

    for z in ("Zicbom", "Zicbop", "Zicboz"):
        check(f"{z} absent from both snippets",
              any(z.lower() in b.lower() for b in bodies.values()), False)
    check("'CMO' present in 19.3.1", "cmo" in bodies["priv_19_3_1"].lower(), True)

    # --- run inventory ------------------------------------------------------
    v1, v2 = load_runs("v1"), load_runs("v2")
    allr = v1 + v2
    check("42 run records total", len(allr), 42)
    check("36 usable (status ok)", sum(1 for r in allr if r.get("status") == "ok"), 36)
    check("6 error runs", sum(1 for r in allr if r.get("status") == "error"), 6)
    check("all 6 errors are gemini-2.5-pro",
          {r["model_requested"] for r in allr if r.get("status") == "error"}, {"gemini-2.5-pro"})
    check("no run supplied a name list",
          all(r.get("name_list_supplied") is False for r in allr), True)
    check("all ok runs used temperature 0",
          {r["params"]["temperature"] for r in allr if r.get("status") == "ok"}, {0.0})

    # --- per-version behaviour ---------------------------------------------
    for tag, runs in (("v1", v1), ("v2", v2)):
        ok = [r for r in runs if r.get("status") == "ok"]
        s19 = [r for r in ok if r["snippet"] == "priv_19_3_1"]
        s21 = [r for r in ok if r["snippet"] == "priv_2_1"]
        check(f"{tag}: 9 usable runs on 19.3.1", len(s19), 9)
        check(f"{tag}: 9 usable runs on 2.1", len(s21), 9)
        check(f"{tag}: CACHE_BLOCK_SIZE found in 9/9 on 19.3.1",
              sum(1 for r in s19 if "CACHE_BLOCK_SIZE" in names_in(r)), 9)
        check(f"{tag}: 2.1 empty in 9/9",
              sum(1 for r in s21 if not names_in(r)), 9)
        over = sum(1 for r in s19
                   if any("CAPACIT" in n.upper() or "ORGANIZ" in n.upper() or "CONFIGURATION" in n.upper()
                          for n in names_in(r)))
        check(f"{tag}: over-extraction count on 19.3.1", over, 9 if tag == "v1" else 6)
        fenced = sum(1 for r in ok if r.get("content", "").lstrip().startswith("```"))
        check(f"{tag}: fenced outputs", fenced, 15 if tag == "v1" else 6)

    # gemini-3.6-flash is the only model that improved
    g36 = [r for r in v2 if r["model_requested"] == "gemini-3.6-flash"
           and r["snippet"] == "priv_19_3_1" and r.get("status") == "ok"]
    check("v2: gemini-3.6-flash emits ONLY CACHE_BLOCK_SIZE, 3/3",
          sum(1 for r in g36 if names_in(r) == ["CACHE_BLOCK_SIZE"]), 3)

    # --- tokens -------------------------------------------------------------
    def toks(model, version):
        p = c = 0
        for r in load_runs(version):
            if r["model_requested"] == model and r.get("status") == "ok":
                p += r.get("prompt_tokens") or 0
                c += r.get("completion_tokens") or 0
        return p, c

    check("DeepSeek v1 tokens", toks("deepseek-ai/DeepSeek-V4-Pro", "v1"), (2217, 6255))
    check("DeepSeek v2 tokens", toks("deepseek-ai/DeepSeek-V4-Pro", "v2"), (9087, 17618))
    check("gemini-3.6-flash v1 tokens", toks("gemini-3.6-flash", "v1"), (2310, 457))
    check("gemini-2.5-flash v2 tokens", toks("gemini-2.5-flash", "v2"), (9396, 2491))

    # --- deliverable contents ----------------------------------------------
    pf = yaml.safe_load((REPO / "parameters.yaml").read_text(encoding="utf-8"))
    # --- 6.1: byte churn vs answer churn ------------------------------------
    import hashlib as _hl
    _cells: dict = {}
    for _f in sorted(REPO.glob("results/*/*/*.json")):
        _r = json.loads(_f.read_text(encoding="utf-8"))
        if _r.get("status") == "error":
            continue
        _m = re.match(r"(priv_\d+_\d+(?:_\d+)?)_run(\d+)\.json", _f.name)
        if not _m:
            continue
        _key = (_f.parts[-3], _f.parts[-2], _m.group(1))
        _cells.setdefault(_key, []).append(
            (_hl.sha256(_r.get("content", "").encode()).hexdigest(),
             tuple(sorted(set(names_in(_r))))))
    _both = _byte_only = _differ = 0
    for _v in _cells.values():
        if len(_v) < 2:
            continue
        _b = len({x[0] for x in _v}) == 1
        _n = len({x[1] for x in _v}) == 1
        if _b and _n:
            _both += 1
        elif _n:
            _byte_only += 1
        else:
            _differ += 1
    check("6.1: cells byte-identical and answer-identical", _both, 5)
    check("6.1: cells byte-different but answer-identical", _byte_only, 13)
    check("6.1: cells whose parameter set differs", _differ, 5)

    check("parameters.yaml has exactly 1 parameter", len(pf.get("parameters") or []), 1)
    check("parameters.yaml parameter is CACHE_BLOCK_SIZE",
          pf["parameters"][0]["name"], "CACHE_BLOCK_SIZE")
    check("parameters.yaml has 11 rejected candidates", len(pf.get("rejected") or []), 11)
    check("metadata self-consistent: parameters_extracted",
          pf["metadata"]["parameters_extracted"], len(pf["parameters"]))
    check("metadata self-consistent: candidates_rejected",
          pf["metadata"]["candidates_rejected"], len(pf["rejected"]))

    VALID_REASONS = {"NOT_STATED_IN_TEXT", "FIXED_BY_ARCHITECTURE",
                     "NOT_ISA_VISIBLE", "CONSTRAINT_NOT_PARAMETER"}
    check("all rejection reason codes are valid",
          {r["reason"] for r in pf["rejected"]} <= VALID_REASONS, True)
    check("6 rejections from 19.3.1",
          sum(1 for r in pf["rejected"] if "19_3_1" in str(r.get("snippet"))), 6)
    check("5 rejections from 2.1",
          sum(1 for r in pf["rejected"] if r.get("snippet", "").endswith("priv_2_1.txt")), 5)

    # every non-null excerpt in the deliverable must be a real substring
    def norm(s):
        return re.sub(r"\s+", " ", str(s)).strip().lower()
    bad = []
    for r in pf["rejected"]:
        e = r.get("excerpt")
        if e:
            key = "priv_19_3_1" if "19_3_1" in str(r.get("snippet")) else "priv_2_1"
            if norm(e) not in norm(bodies[key]):
                bad.append(r["candidate"])
    for k, v in pf["parameters"][0]["source"].items():
        if k.startswith("excerpt") or k.startswith("supporting_excerpt"):
            if norm(v) not in norm(bodies["priv_19_3_1"]):
                bad.append(f"parameter/{k}")
    check("every excerpt in parameters.yaml is a verbatim substring", bad, [])

    # --- UDB (optional) -----------------------------------------------------
    if args.udb:
        P = pathlib.Path(args.udb) / "spec/std/isa/param"
        files = sorted(P.glob("*.yaml"))
        check("UDB has 227 parameter files", len(files), 227)
        todo = sum(1 for f in files
                   if str(yaml.safe_load(f.read_text()).get("long_name", "")).strip() == "TODO")
        check("163 files have long_name: TODO", todo, 163)
        check("no cache-capacity parameter exists",
              [f.name for f in files if "CAPACIT" in f.name.upper()], [])
        sd = json.loads((pathlib.Path(args.udb) / "spec/schemas/schema_defs.json").read_text())
        for d in ("32bit_unsigned_pow2", "64bit_unsigned_pow2"):
            enum = sd["$defs"][d]["enum"]
            check(f"{d}: 4095 present (the bug)", 4095 in enum, True)
            check(f"{d}: 4096 absent (the bug)", 4096 in enum, False)
            check(f"{d}: 4095 is the only non-power-of-two",
                  [v for v in enum if v < 1 or (v & (v - 1))], [4095])

    # --- report -------------------------------------------------------------
    failed = [r for r in results if not r[0]]
    for ok, label, detail in results:
        if not ok:
            print(f"  FAIL  {label}\n        {detail}")
    print(f"\n{len(results) - len(failed)}/{len(results)} claims verified")
    if failed:
        print(f"{len(failed)} FAILED — fix the document or the claim before submitting")
        return 1
    print("All quantitative claims in the submission re-derive from the raw data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
