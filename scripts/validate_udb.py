#!/usr/bin/env python3
"""Validate our UDB-shaped output against riscv-unified-db's real param_schema.json.

The claim "this is UDB-shaped" is worth nothing unless it is checked against the
actual schema, with its actual $refs resolved. This script does that, or says
plainly that it could not.

Requires a local checkout of riscv-unified-db. Point --udb at it, or set
UDB_PATH. The schemas live at <udb>/spec/schemas/.

Usage:
    python3 scripts/validate_udb.py --udb /path/to/riscv-unified-db
    python3 scripts/validate_udb.py --udb ... --file udb/CACHE_BLOCK_SIZE.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--udb", default=os.environ.get("UDB_PATH"),
                    help="path to a riscv-unified-db checkout")
    ap.add_argument("--file", default="udb/CACHE_BLOCK_SIZE.yaml",
                    help="parameter file to validate, relative to this repo")
    args = ap.parse_args()

    if not args.udb:
        print("No UDB checkout given. Pass --udb or set UDB_PATH.")
        print("  git clone --depth 1 https://github.com/riscv/riscv-unified-db")
        return 2

    schemas = pathlib.Path(args.udb) / "spec" / "schemas"
    param_schema = schemas / "param_schema.json"
    if not param_schema.exists():
        print(f"Not found: {param_schema}")
        return 2

    try:
        import warnings

        import yaml
        with warnings.catch_warnings():
            # RefResolver is deprecated but is the simplest way to resolve
            # UDB's bare-filename sibling $refs. Behaviour is adequate here.
            warnings.simplefilter("ignore", DeprecationWarning)
            from jsonschema import Draft7Validator, RefResolver
    except ImportError as e:
        print(f"Missing dependency: {e}. pip install pyyaml jsonschema")
        return 2

    target = REPO / args.file
    doc = yaml.safe_load(target.read_text(encoding="utf-8"))
    schema = json.loads(param_schema.read_text(encoding="utf-8"))

    # param_schema.json $refs sibling files by bare filename
    # (e.g. "schema_defs.json#/$defs/param_name"), so resolve against the
    # schemas directory.
    store = {}
    for f in schemas.glob("*.json"):
        try:
            store[f.name] = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - a malformed sibling is not our problem
            pass

    resolver = RefResolver(base_uri=f"{schemas.as_uri()}/", referrer=schema, store=store)
    validator = Draft7Validator(schema, resolver=resolver)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))

    print(f"file   : {args.file}")
    print(f"schema : {param_schema}")
    print(f"udb    : {args.udb}")
    print()
    if not errors:
        print("VALID -- conforms to param_schema.json")
        print()
        print("Fields present:", ", ".join(sorted(doc.keys())))
        req = schema.get("required", [])
        print("Required by schema:", ", ".join(sorted(req)))
        missing = [r for r in req if r not in doc]
        print("Missing required:", missing or "none")
        return 0

    print(f"INVALID -- {len(errors)} error(s)")
    for e in errors:
        loc = "/".join(str(p) for p in e.path) or "<root>"
        print(f"  at {loc}: {e.message[:200]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
