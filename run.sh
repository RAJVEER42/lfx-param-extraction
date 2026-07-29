#!/usr/bin/env bash
# One-command reproduction of the whole submission.
#
# Stages 1-2 are offline and deterministic; they need no credentials and will
# always reproduce. Stages 3-4 call models and are skipped unless --with-models
# is passed, so that a reviewer can verify everything checkable without needing
# an API key or spending anything.
#
#   ./run.sh                  offline: trigger scan, validate committed output
#   ./run.sh --with-models    also re-run the models (needs credentials)
#   ./run.sh --udb <path>     also validate against a riscv-unified-db checkout
#
# Credentials, if used, are read from the provider's own store or a gitignored
# .env. Nothing secret is read from or written to this repository.

set -euo pipefail
cd "$(dirname "$0")"

WITH_MODELS=0
UDB="${UDB_PATH:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --with-models) WITH_MODELS=1; shift ;;
    --udb) UDB="$2"; shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

hr() { printf '\n%s\n%s\n%s\n' "========================================" "$1" "========================================"; }

hr "1. Trigger-word scan (offline, no model)"
# Establishes as fact which signal words the snippets contain, before any
# interpretation. Snippet 2.1 contains none of the challenge's signal words.
python3 scripts/scan_triggers.py

hr "2. Validate committed model output (offline)"
# Runs the same checks that caught a fabricated quotation in the committed v2
# output. Expected: v1 fails (it has no excerpt field at all, and contains
# signal words used as constraint values); v2 has exactly one E1 failure.
if python3 -c "import yaml" 2>/dev/null; then
  echo "--- v1 (expected to FAIL: no provenance fields, category errors) ---"
else
  # Without PyYAML only E1 runs, and v1 has no excerpt field for E1 to check, so
  # v1 reports clean. Its real failures are E2 and E8, which need the parsed
  # document. Say so, rather than letting "24/24 clean" contradict the label.
  echo "--- v1 (PyYAML absent: will report CLEAN, which is misleading) ---"
  echo "    v1's failures are E2 and E8 and need PyYAML. E1 alone cannot fail on"
  echo "    v1 because v1 has no excerpt field. Install pyyaml to see the real result."
fi
python3 scripts/validate.py results/*/v1 2>&1 | tail -5 || true
echo
echo "--- v2 (expected: 17/18 clean, 1 elided-quote failure; holds without PyYAML) ---"
python3 scripts/validate.py results/*/v2 2>&1 | tail -8 || true

hr "3. Audit every quantitative claim against the raw data (offline)"
# The metadata-churn figures in analysis/v1_failures.md 6.2 need the full parsed
# document per run, so they are checked by their own script.
python3 scripts/check_metadata_churn.py 2>&1 | tail -5 || \
  echo "  (skipped: needs pyyaml)"
echo
# Re-derives the numbers in README.md, parameters.yaml and analysis/ from
# results/. A submission asserting numbers nobody recomputed is asking to be
# trusted; this makes them checkable in one command.
if ! python3 -c "import yaml" 2>/dev/null; then
  echo "SKIPPED: the claim audit parses YAML and needs PyYAML."
  echo "  pip install pyyaml   then re-run to check all 42 claims."
  echo "Stages 1 and 2 above do not need it and have completed."
elif [ -n "$UDB" ]; then
  python3 scripts/audit_claims.py --udb "$UDB"
else
  python3 scripts/audit_claims.py
fi

if [ -n "$UDB" ]; then
  hr "4. Validate UDB-native output against the real param_schema.json"
  python3 scripts/validate_udb.py --udb "$UDB"
else
  hr "4. UDB schema validation -- SKIPPED"
  echo "Pass --udb <path> or set UDB_PATH to a riscv-unified-db checkout:"
  echo "  git clone --depth 1 https://github.com/riscv/riscv-unified-db"
  echo "(this also unlocks the UDB-side claims in stage 3)"
fi

if [ "$WITH_MODELS" -eq 1 ]; then
  hr "5. Re-run models (costs tokens)"
  echo "N=3 per model per snippet. temperature=0. finish_reason is checked."
  for m in "deepseek-ai/DeepSeek-V4-Pro:hf" "gemini-3.6-flash:gemini" "gemini-2.5-flash:gemini"; do
    model="${m%:*}"; provider="${m##*:}"
    echo
    echo "--- $model via $provider ---"
    python3 scripts/run_extraction.py --prompt v2 --model "$model" \
      --provider "$provider" --runs 3 --max-tokens 16000 || \
      echo "  (failed -- recorded with status != ok, not treated as empty)"
  done
  echo
  echo "Re-validating freshly generated output:"
  python3 scripts/validate.py results/*/v2 2>&1 | tail -6 || true
else
  hr "5. Model re-runs -- SKIPPED"
  echo "Pass --with-models to re-run. Committed raw output is in results/."
fi

hr "Done"
cat <<'EOF'
Deliverables:
  parameters.yaml              1 parameter, 11 rejected candidates, with provenance
  udb/CACHE_BLOCK_SIZE.yaml    UDB-native shape, schema-validated
  ground_truth.md              committed before any model ran
  analysis/v1_failures.md      v1 failure modes, 3 of 7 predictions refuted
  analysis/v2_delta.md         v1 -> v2 delta, 2 of 9 predictions refuted
  README.md                    the submission
EOF
