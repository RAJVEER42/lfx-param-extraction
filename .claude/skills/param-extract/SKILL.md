---
name: param-extract
description: Extract architectural parameters from RISC-V specification text into UDB-shaped YAML, with verbatim provenance and mechanical validation. Use when given a passage of the RISC-V ISA Manual (privileged or unprivileged) and asked to identify architectural parameters, implementation-defined values, or configuration options — or when asked to review or audit a parameter extraction someone else produced.
---

# Extracting architectural parameters from RISC-V spec text

## The rule that matters

Most false positives come from treating a signal word as sufficient. It is not.

> **A word signalling implementation freedom is necessary but not sufficient. A
> parameter exists only where the implementation genuinely chooses, AND that
> choice is ISA-visible.**

Apply three tests in order. A candidate must pass all three.

**T1 — Is it stated in this text?**
Use only what the passage says. You will often know true facts about RISC-V that
the passage does not state; those are not extractable here. If you cannot quote
a span supporting the candidate, it fails T1.

**T2 — Does the implementation genuinely choose?**
A value the architecture assigns is not a parameter, even under hedging language
like "by convention". Ask: could two conforming implementations differ?

Special case: a field labelled **WARL** is not a parameter unless **the set of
legal values itself is implementation-chosen**. Many WARL fields have
architecturally fixed legal sets. This is the single largest source of CSR-side
false positives.

**T3 — Is the choice ISA-visible?**
Does any *instruction's defined behaviour*, or software-readable architectural
state, depend on the value?

⚠️ **Discoverability through the execution environment does NOT count.** The
execution environment — device tree, configuration structure, SBI — is outside
the ISA. "Software can discover it somehow" is the most persuasive wrong answer
there is, and models produce it with high confidence. A passage that mentions a
discovery mechanism next to an implementation-specific value is actively baiting
this error.

Cache capacity and associativity, pipeline depth, branch predictor size: real
implementation choices, invisible to the ISA, therefore not architectural
parameters.

## Signal words

Parameters are often marked by: "may", "might", "should", "optional",
"optionally", "implementation defined", "implementation specific".

**"shall" and "must" are not signal words.** They are mandates: they *remove*
implementation freedom. "X shall be Y" usually describes a **constraint on** a
parameter. Do not let stemming or synonym matching conflate `shall` with
`should` — they are near-opposites in specification language.

## Procedure

1. **Scan mechanically first.** `python3 scripts/scan_triggers.py` establishes
   which signal words are actually present. Do this before reading
   interpretively, so a later disagreement is about interpretation rather than
   about what the text says.
2. **Enumerate every candidate**, including ones you expect to reject. If a
   passage has no signal words, the expected yield is zero — say so explicitly
   rather than producing something.
3. **Adjudicate each against T1/T2/T3**, recording the reason for rejections.
4. **Emit both shapes** — flat (`name`/`description`/`type`/`constraints`) and
   UDB-native, where `type` and `constraints` live inside `schema:`.
5. **Validate.** `scripts/validate.py` for grounding and schema;
   `scripts/validate_udb.py --udb <checkout>` against the real
   `param_schema.json`.

## Output contract

```yaml
parameters:
  - name: UPPER_SNAKE_CASE
    long_name: short human-readable name
    description: what is chosen, and what depends on it
    type: integer | boolean | string | enum | array
    constraints:            # structured keys only; omit if none stated
      minimum: / maximum: / enum: / power_of_two: / note:
    excerpt: "verbatim span, checked as an exact substring"
    trigger: "the signal phrase that fired"
    defined_by: extension name ONLY if the passage names it, else null
    isa_visible: the concrete software-observable consequence
    confidence: high | medium | low
rejected:
  - candidate: what was considered
    reason: NOT_STATED_IN_TEXT | FIXED_BY_ARCHITECTURE | NOT_ISA_VISIBLE | CONSTRAINT_NOT_PARAMETER
    excerpt: "verbatim span, or null"
    explanation: one sentence
```

### Non-negotiable rules

1. **`excerpt` must be copied character for character.** It is checked as an
   exact substring. Do **not** elide with an ellipsis — an elided quote reads as
   verbatim, passes human review, and fails the check. This was observed in real
   output: a model wrote `"The ... size of a cache block are both
   implementation-specific"`, eliding eleven words, while quoting the same
   sentence correctly elsewhere in the same response.
2. **A signal word is never a constraint value.** `constraints:
   implementation-specific` is a category error: the phrase is evidence the
   parameter exists, not a limit on its value.
3. **Never add units the passage omits.** If it does not say "bytes", do not.
4. **`defined_by` only from the passage.** A passage saying "the CMO extensions"
   without naming `Zicbom`/`Zicbop`/`Zicboz` means `null`.
5. **Record what you rejected.** A correctly rejected candidate is a result. An
   extraction that cannot say what it declined cannot be reviewed.
6. **`isa_visible` must name a concrete consequence.** If you cannot, the
   candidate failed T3 and belongs in `rejected`.

## Verification, not instruction

Do not trust the output — check it. The strongest defence against a fabricated
quote is a program, not a prompt:

```bash
python3 scripts/validate.py results/<model>/<version>
```

Checks: E1 excerpt is an exact substring · E2 no signal word as a constraint
value · E3 `defined_by` names nothing absent from the passage · E4 no invented
units · E5 name matches `^[A-Z][A-Z_0-9]*$` · E6 type domain · E7 known reason
codes · E8 required fields.

## Running models

```bash
python3 scripts/run_extraction.py --prompt v2 --model <id> [--provider hf|gemini] --runs 3
```

Two constraints, both learned the hard way:

- **`temperature=0` is not necessarily deterministic.** It is model- and
  provider-dependent: one model tested was byte-identical across 6 runs, another
  produced 3 distinct outputs with a 3.2× spread in token use. **Run N≥3 and
  report agreement** rather than assuming.
- **`finish_reason != "stop"` is a run FAILURE, never an empty result.**
  Reasoning models that exhaust their budget return empty content. Parsed
  naively that reads as "no parameters found" — which is the *correct* answer
  for some passages, so truncation masquerades as success. This guard caught six
  such cases on its first use.

## Reference

| Topic | File |
|---|---|
| Adjudicated worked example, 2 snippets | `ground_truth.md` |
| UDB schema, verified field-by-field | `reference/udb-schema-notes.md` |
| Prior art and known failure classes | `reference/prior-art.md` |
| Observed failure modes with real output | `analysis/v1_failures.md`, `analysis/v2_delta.md` |
| Prompt, current | `prompts/v2/system.md` |
