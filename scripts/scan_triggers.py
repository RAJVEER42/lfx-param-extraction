#!/usr/bin/env python3
"""Mechanical trigger-word scan of the challenge snippets.

Produces the fact base for ground_truth.md section 1. Makes no API calls.

The point of running this *before* any LLM is that the set of trigger phrases
present in the text is a matter of fact, not judgement. Establishing it
mechanically means a later disagreement with a model can be about
interpretation rather than about what the text says.

Usage:
    python3 scripts/scan_triggers.py
    python3 scripts/scan_triggers.py --json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SNIPPETS = ["snippets/priv_19_3_1.txt", "snippets/priv_2_1.txt"]

# Exactly the phrases the challenge document names as parameter signals.
BRIEF_TRIGGERS = [
    "may", "might", "should",
    "optional", "optionally",
    "implementation defined", "implementation-defined",
    "implementation specific", "implementation-specific",
]

# Words a naive matcher might treat as equivalent, but which are not on the
# brief's list. Tracked separately because the distinctions matter:
#   - "shall"/"must" are MANDATES; they remove implementation freedom, and are
#     near-opposites of "should". Loose stemming or synonym expansion inverts
#     the meaning of the sentence.
#   - "by convention"/"conventional" describe fixed architectural convention,
#     not per-implementation choice.
NEAR_MISS = [
    "shall", "must", "can", "could",
    "typically", "usually", "recommended",
    "by convention", "conventional",
]

# Extension names deliberately checked for absence. The snippets say "CMO" but
# never name the three CMO extensions, while UDB's CACHE_BLOCK_SIZE is
# definedBy anyOf [Zicbom, Zicbop, Zicboz]. Any model output naming them is
# therefore correct-but-ungrounded. See ground_truth.md section 1.1.
GROUNDING_PROBES = ["Zicbom", "Zicbop", "Zicboz", "CMO"]

# Provenance header lines added when the snippets were stored; not spec text.
HEADER_PREFIXES = ("Source:", "Provided ")


def body_of(path: pathlib.Path) -> str:
    """Snippet text with our own provenance header stripped."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(
        ln for ln in lines if not ln.startswith(HEADER_PREFIXES)
    ).strip()


def find(term: str, text: str) -> list[dict]:
    """Case-insensitive whole-phrase matches, not substring matches.

    The negative lookbehind/lookahead prevent 'may' matching 'maybe' and
    'can' matching 'cannot' -- a substring scan would overcount badly.
    """
    pattern = r"(?<![A-Za-z-])" + re.escape(term) + r"(?![A-Za-z])"
    out = []
    for m in re.finditer(pattern, text, re.IGNORECASE):
        start = m.start()
        out.append(
            {
                "offset": start,
                "matched": m.group(0),
                "context": text[max(0, start - 50) : start + len(term) + 50].replace("\n", " "),
            }
        )
    return out


def scan(path: pathlib.Path) -> dict:
    text = body_of(path)
    brief = {t: find(t, text) for t in BRIEF_TRIGGERS}
    near = {t: find(t, text) for t in NEAR_MISS}
    probes = {p: (p.lower() in text.lower()) for p in GROUNDING_PROBES}
    return {
        "file": str(path.relative_to(REPO)),
        "word_count": len(text.split()),
        "brief_triggers": {k: v for k, v in brief.items() if v},
        "near_miss": {k: v for k, v in near.items() if v},
        "brief_trigger_count": sum(len(v) for v in brief.values()),
        "grounding_probes": probes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    results = []
    for rel in SNIPPETS:
        p = REPO / rel
        if not p.exists():
            print(f"missing snippet: {rel}", file=sys.stderr)
            return 1
        results.append(scan(p))

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    total_brief = 0
    for r in results:
        print(f"=== {r['file']} ({r['word_count']} words) ===")
        total_brief += r["brief_trigger_count"]

        if r["brief_triggers"]:
            for term, hits in r["brief_triggers"].items():
                for h in hits:
                    print(f"  [BRIEF-LISTED] {term:24} ...{h['context']}...")
        else:
            print("  [BRIEF-LISTED] none -- expected yield is ZERO parameters")

        for term, hits in r["near_miss"].items():
            for h in hits:
                print(f"  [not-in-brief] {term:24} ...{h['context']}...")
        print()

    print(f"brief-listed trigger phrases across all snippets: {total_brief}")
    print()
    print("=== grounding probes (absence is the point) ===")
    for r in results:
        name = r["file"].split("/")[-1]
        for probe, present in r["grounding_probes"].items():
            print(f"  {name:20} {probe:8} present={present}")
    print()
    print("Any model output naming Zicbom/Zicbop/Zicboz is correct per UDB but")
    print("ungrounded in these snippets. See ground_truth.md section 1.1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
