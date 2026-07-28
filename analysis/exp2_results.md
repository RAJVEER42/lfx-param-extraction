# Experiment 2 — results

Scored against [`exp2_prereg.md`](exp2_prereg.md) and the classifier
`scripts/classify_justification.py`, both committed at `abce296` before any run.

**Part A confirms the mechanism on unseen models. Part B shows the fix works on the
justification and only partly on the behaviour.** That second result is the useful
one, and it qualifies a claim made in `exp1_results.md`.

---

# Part A — the mechanism, tested prospectively

`exp1_results.md` §4a observed, post-hoc on 3 models, that the `isa_visible`
justification tracked over-extraction. Part A tested it on **four models never used
in this project**.

## A.1 The association held

| Model | Class | Emitted cache capacity? |
|---|---|---|
| `Kimi-K2-Instruct-0905` | DISCOVERY 3/3 | **yes** 3/3 |
| `Ling-2.6-1T` | DISCOVERY 3/3 | **yes** 3/3 |
| `Nemotron-3-Ultra-550B` | OPERATIONS 1/3, MIXED 2/3 | no on the OPERATIONS run, yes on both MIXED runs |
| `GLM-5.2` | — | no usable runs, see A.4 |

**Association: 7 of 7 scored runs.** Combined with the original three models scored
by the same committed classifier, **15 of 15**.

| | no false positive | false positive |
|---|---:|---:|
| **OPERATIONS** | 1 | 0 |
| **DISCOVERY** | 0 | 6 |

Two MIXED runs excluded as preregistered.

## A.2 🔴 The strongest evidence: the same model flips between runs

`Nemotron-3-Ultra`, `temperature=0`, three runs of an identical prompt:

| Run | `isa_visible` | Params |
|---|---|---|
| 1 | *"Software can **discover** … via the execution environment's discovery mechanism;* CMO instructions depend on this" | **3**, over-extracts |
| 2 | *"CMO instructions (CBO.CLEAN, CBO.FLUSH, CBO.INVAL) **operate on** cache blocks of this size; software must know the block size to use them correctly"* | **1**, correct |
| 3 | *"Software can **discover** … through the execution environment's cache discovery mechanism;* CMO instructions operate on…" | **3**, over-extracts |

The reasoning changes between runs of one model and **the answer changes with it.**
That removes model capability as a confound, which a between-model correlation
cannot do. It is the single cleanest result in this project.

Note also the *form*: runs 1 and 3 lead with discovery and mention operations
second. Run 2 gives operations only. Leading with the wrong argument was enough.

## A.3 Predictions

| # | Prediction | Outcome |
|---|---|---|
| **Y1** | Association holds in ≥10/12 runs | ✅ **7 of 7 scored**, though on 9 usable runs not 12 (A.4) |
| Y2 | ≥1 model is OPERATIONS-type | ✅ but thinly, 1 run |
| Y3 | ≥1 model is DISCOVERY-type | ✅ 2 models fully |
| Y4 | `CACHE_BLOCK_SIZE` in ≥10/12 | ✅ 9 of 9 usable |
| Y5 | ≥1 new model produces an elided quote | ❌ **REFUTED — 9/9 clean** |

Y5's refutation is worth stating: the elided-quote failure appears in 3 of 7 models
tested overall, not all of them. It is a real failure mode, not a universal one.

## A.4 Two honest problems with Part A

**`GLM-5.2` produced no usable runs.** Six attempts, all `504 Gateway Time-out` at
the HF router. So Y1's denominator is 9, not the 12 planned.

**I destroyed a successful run.** GLM's first batch produced 1 ok run of 3. I then
re-ran the whole cell to retry the two failures, and the runner writes by run
index, so it overwrote the good result with an error. That is a harness defect
worth naming: **re-running a cell silently replaces prior successes.** The one GLM
data point is unrecoverable, and the loss is mine, not the provider's.

---

# Part B — the two-part fix

`prompts/v3/` changes **only** the T3 section of v2, verified byte-identical
elsewhere. It excludes discoverability *and* requires a named instruction whose
defined behaviour depends on the value.

## B.1 Predictions

| # | Prediction | Outcome |
|---|---|---|
| **Z1** | Capacity emitted in ≤2 of 18 runs | ❌ **REFUTED — 3 of 11 usable** |
| **Z2** | `CACHE_BLOCK_SIZE` in ≥15 of 18 | ⚠️ **9 of 11 usable**, proportionally on target but see B.3 |
| **Z3** | Justifications shift to OPERATIONS in ≥12/18 | ✅ **9 of 9 classified runs, no DISCOVERY at all** |
| **Z4** | Snippet 2.1 empty in 6 of 6 | ❌ **REFUTED — 4 of 5 parsed, plus 1 regression and 1 parse failure** |
| Z5 | ≥1 run still over-extracts | ✅ confirmed |

## B.2 🔴 The finding: the fix taught the words, not the reasoning

Z3 succeeded completely. Under v3 **no run gave a DISCOVERY justification.** The
wording intervention worked exactly as designed.

Z1 failed anyway. `Ling-2.6-1T` emitted cache capacity in **3 of 3** v3 runs, while
giving OPERATIONS-class justifications.

So one model learned to *state* the correct argument and kept the incorrect
behaviour. Under v2 that model was DISCOVERY/false-positive, consistent with the
mechanism. Under v3 it is OPERATIONS/false-positive, which the mechanism does not
predict.

**This qualifies `exp1_results.md` §4a.** The association between justification and
answer held because the justification was *unprompted* and therefore revealed what
the model was actually doing. Once the prompt requires a particular form of
justification, models can satisfy the form without changing the judgement, and the
diagnostic value degrades. Under v3 the association falls to **6 of 9**.

The practical lesson is uncomfortable and worth stating plainly: **requiring a
model to state the right reason makes its output look better without necessarily
making it better.** A justification field is a good instrument exactly while you
are not optimising against it.

## B.3 Partial collapse, as Arm B warned

`Kimi-K2` found `CACHE_BLOCK_SIZE` in only **1 of 3** v3 runs; the other two
emitted nothing. That is the exp1 Arm B failure appearing under v3, in the one
model tested that is most sensitive to it.

So the two-part fix reduced but did not eliminate the risk exp1 identified.
Excluding the wrong reason still costs some true positives, even when the right
reason is supplied alongside.

## B.4 Two new defects on snippet 2.1

**A regression on the negative control.** `gpt-oss-120b` run 3 emitted a parameter
from snippet 2.1, which every previous run of every model correctly left empty:

```yaml
name: CSR_ACCESS_ENCODING
isa_visible: The defined behaviour of CSR access instructions (e.g., CSRRW, CSRRS,
             CSRRWI) depends on how these bits are interpreted to enforce
             read/write permissions
excerpt: "By convention, the upper 4 bits of the CSR address (csr[11:8]) are used
          to encode the read and write accessibility of the..."
```

The excerpt is genuine and the argument is *superficially* the shape v3 asked for:
it names instructions. It is still wrong, because the encoding is architecturally
fixed and fails T2, not T3. **Strengthening T3 induced a T2 failure**, by making
"name an instruction" the salient requirement.

**A YAML parse failure.** `Kimi-K2` run 1 emitted an unquoted candidate beginning
with a quote character:

```yaml
- candidate: "By convention" encoding
```

That is invalid YAML. The validator reports it as `PARSE`, not as an empty
extraction, which is the behaviour the `finish_reason` guard was built for
generalising correctly.

## B.5 Validator totals

12 of 15 runs clean, 5 errors: 4 elided-quote E1 failures on `rejected` entries in
`Ling-2.6-1T` and `gpt-oss-120b`, plus the parse failure above.

The elided quote now appears in **4 models across 4 labs**, all eliding the same
eight words from the same sentence.

---

# What experiment 2 changes

1. **The mechanism is real and prospectively confirmed** — 15 of 15 under v2, with
   a within-model flip that rules out capability confounds.
2. **It is not robust to being optimised against.** v3 removed DISCOVERY
   justifications entirely and one model kept over-extracting anyway. Report §4a
   with this caveat attached.
3. **The two-part fix is an improvement, not a solution.** Over-extraction 5/6 →
   3/11, no DISCOVERY reasoning, but one model partly collapsed and a new T2
   failure appeared on the negative control.
4. **Do not ship v3 as the recommended prompt.** On this evidence it trades one
   failure mode for two smaller ones. The honest position is that T3 needs the
   exclusion *and* T2 needs strengthening against "names an instruction" as a
   sufficient argument.

## Limits

- 11 usable v3 runs on 19.3.1, 5 parsed on 2.1, 9 usable in Part A. Counts, not
  rates.
- `GLM-5.2` unusable; one data point destroyed by my own rerun (A.4).
- Gemini absent throughout: no working key.
- Part B has no v2 baseline for `Nemotron` on the same models in the same session,
  so the v2 → v3 comparison mixes Part A's v2 runs with Part B's v3 runs. Same
  prompt bytes and same parameters, but not interleaved.
- The OPERATIONS/DISCOVERY classifier is keyword-based and committed in advance.
  It cannot detect a justification that uses the right vocabulary with the wrong
  logic, which is precisely what B.2 found. That limitation is now demonstrated
  rather than hypothetical.
