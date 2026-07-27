#!/usr/bin/env python3
"""Mechanically validate extraction output. No model judges the model.

This is the concrete answer to "how did you deal with hallucinations": the
strongest check available is not a prompt instruction but a program that
verifies a claim against the source text.

THE CENTRAL CHECK -- excerpt grounding:
    Every `excerpt` must be an exact substring of the snippet the model was
    shown. If it is not, the model did not copy from the passage; it produced
    the text from somewhere else. That is detectable with `in`, requires no
    judgement, and cannot be argued with.

Written BEFORE the v2 runs (see git history) so that its checks are motivated by
v1's observed failures rather than tuned to flatter v2's output.

Checks:
  E1  excerpt is an exact substring of the source snippet        [grounding]
  E2  constraints contain no signal word as a value              [category error]
  E3  defined_by names only extensions present in the passage    [ungrounded]
  E4  description introduces no unit absent from the passage     [ungrounded]
  E5  name matches UDB's param_name pattern ^[A-Z][A-Z_0-9]*$    [schema]
  E6  type is one of the permitted values                        [schema]
  E7  rejected entries carry a known reason code                 [schema]
  E8  required fields are present                                [schema]

Exit code is nonzero if any ERROR-severity check fails.

Usage:
    python3 scripts/validate.py results/gemini-3-6-flash/v2
    python3 scripts/validate.py results/*/v2 --json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
HEADER_PREFIXES = ("Source:", "Provided ")

PARAM_NAME = re.compile(r"^[A-Z][A-Z_0-9]*$")
VALID_TYPES = {"integer", "boolean", "string", "enum", "array"}
VALID_REASONS = {
    "NOT_STATED_IN_TEXT",
    "FIXED_BY_ARCHITECTURE",
    "NOT_ISA_VISIBLE",
    "CONSTRAINT_NOT_PARAMETER",
}

# A signal word is evidence a parameter exists, never a restriction on its
# value. See analysis/v1_failures.md section 4.3.
SIGNAL_WORDS = [
    "implementation-specific", "implementation specific",
    "implementation-defined", "implementation defined",
    "optional", "optionally", "may", "might", "should",
]

# Units a model might introduce that the passage does not state.
UNITS = ["byte", "bytes", "bit", "bits", "kib", "mib", "kb", "mb", "word", "words"]

REQUIRED_PARAM_FIELDS = ["name", "description", "type", "excerpt"]


def snippet_text(key: str) -> str:
    p = REPO / "snippets" / f"{key}.txt"
    lines = p.read_text(encoding="utf-8").splitlines()
    return "\n".join(ln for ln in lines if not ln.startswith(HEADER_PREFIXES)).strip()


def strip_fence(s: str) -> str:
    """Tolerate markdown fences. v1 produced them in 15/18 outputs despite an
    explicit instruction, so the parser must cope rather than the prompt."""
    s = s.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        lines = lines[1:]
        while lines and not lines[-1].strip().startswith("```"):
            lines.pop()
        if lines:
            lines.pop()
        return "\n".join(lines).strip()
    return s


def norm(s: str) -> str:
    """Collapse whitespace for substring comparison.

    Deliberate leniency: a model that re-wraps a long quoted line has still
    copied it. A model that paraphrases has not, and still fails. We are
    testing provenance, not whitespace fidelity.
    """
    return re.sub(r"\s+", " ", s).strip()


def flatten(v, out=None):
    """Yield every scalar in a nested structure, as a string."""
    out = [] if out is None else out
    if isinstance(v, dict):
        for x in v.values():
            flatten(x, out)
    elif isinstance(v, list):
        for x in v:
            flatten(x, out)
    elif v is not None:
        out.append(str(v))
    return out


def check_run(record: dict) -> list[dict]:
    """Return a list of findings for one run record."""
    findings: list[dict] = []

    def add(code: str, severity: str, msg: str, item: str = "") -> None:
        findings.append({"code": code, "severity": severity, "message": msg, "item": item})

    if record.get("status") != "ok":
        add("RUN", "skip", f"status={record.get('status')} -- not an empty extraction")
        return findings

    source = snippet_text(record["snippet"])
    source_n = norm(source).lower()

    try:
        import yaml
    except ImportError:
        add("PARSE", "error", "PyYAML not installed: pip install pyyaml")
        return findings

    raw = strip_fence(record.get("content", ""))
    if not raw:
        add("PARSE", "error", "empty content on an ok run")
        return findings
    try:
        doc = yaml.safe_load(raw)
    except Exception as e:  # noqa: BLE001
        add("PARSE", "error", f"YAML parse failed: {type(e).__name__}: {str(e)[:120]}")
        return findings
    if not isinstance(doc, dict):
        add("PARSE", "error", f"top level is {type(doc).__name__}, expected mapping")
        return findings

    params = doc.get("parameters") or []
    rejected = doc.get("rejected") or []
    if not isinstance(params, list):
        add("PARSE", "error", "`parameters` is not a list")
        return findings

    for p in params:
        if not isinstance(p, dict):
            add("E8", "error", f"parameter entry is {type(p).__name__}, expected mapping")
            continue
        name = str(p.get("name", "<unnamed>"))

        for f in REQUIRED_PARAM_FIELDS:
            if not p.get(f):
                add("E8", "error", f"missing required field `{f}`", name)

        # E1 -- the central grounding check.
        exc = p.get("excerpt")
        if exc:
            if norm(str(exc)).lower() in source_n:
                add("E1", "pass", "excerpt is an exact substring of the source", name)
            else:
                add("E1", "error", f"excerpt NOT found in source: {str(exc)[:90]!r}", name)

        # E2 -- signal word used as a constraint value.
        for val in flatten(p.get("constraints")):
            low = val.lower()
            for w in SIGNAL_WORDS:
                if w in low:
                    add("E2", "error", f"signal word {w!r} used as a constraint value: {val[:70]!r}", name)
                    break

        # E3 -- extension named that the passage does not contain.
        db = p.get("defined_by")
        if db:
            for tok in re.findall(r"[A-Za-z][A-Za-z0-9_]+", str(db)):
                if tok.lower() not in source.lower():
                    add("E3", "error", f"defined_by names {tok!r}, absent from the passage", name)

        # E4 -- unit introduced that the passage does not state.
        desc = str(p.get("description", "")).lower()
        for u in UNITS:
            if re.search(rf"\b{u}\b", desc) and not re.search(rf"\b{u}\b", source_n):
                add("E4", "warn", f"description introduces unit {u!r}, absent from the passage", name)
                break

        # E5 / E6 -- schema conformance.
        if name != "<unnamed>" and not PARAM_NAME.match(name):
            add("E5", "error", f"name does not match UDB pattern ^[A-Z][A-Z_0-9]*$", name)
        t = p.get("type")
        if t and str(t) not in VALID_TYPES:
            add("E6", "error", f"type {t!r} not in {sorted(VALID_TYPES)}", name)

    # E7 -- rejection reason codes.
    for r in rejected:
        if not isinstance(r, dict):
            continue
        cand = str(r.get("candidate", "<unnamed>"))
        reason = r.get("reason")
        if reason and str(reason) not in VALID_REASONS:
            add("E7", "error", f"unknown reason code {reason!r}", cand)
        exc = r.get("excerpt")
        if exc and norm(str(exc)).lower() not in source_n:
            add("E1", "error", f"rejected-item excerpt NOT in source: {str(exc)[:70]!r}", cand)

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dirs", nargs="+", help="result directories, e.g. results/*/v2")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    files: list[pathlib.Path] = []
    for d in args.dirs:
        p = pathlib.Path(d)
        files.extend(sorted(p.glob("*.json")) if p.is_dir() else [p])

    all_out, errors = [], 0
    for f in files:
        rec = json.loads(f.read_text(encoding="utf-8"))
        findings = check_run(rec)
        n_err = sum(1 for x in findings if x["severity"] == "error")
        errors += n_err
        all_out.append({"file": str(f), "findings": findings, "errors": n_err})

        if not args.json:
            status = "FAIL" if n_err else "ok"
            print(f"{status:4} {f}")
            for x in findings:
                if x["severity"] == "pass":
                    continue
                mark = {"error": "  ERROR", "warn": "  warn ", "skip": "  skip "}[x["severity"]]
                item = f" [{x['item']}]" if x["item"] else ""
                print(f"{mark} {x['code']}{item}: {x['message']}")

    if args.json:
        print(json.dumps(all_out, indent=2))
    else:
        n_pass = sum(1 for o in all_out if not o["errors"])
        print(f"\n{n_pass}/{len(all_out)} runs clean · {errors} errors total")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
