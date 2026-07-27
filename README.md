# AI-assisted extraction of architectural parameters from RISC-V specifications

**Coding challenge submission — LFX Mentorship, Fall 2026**
RISC-V International · [`riscv/riscv-unified-db`](https://github.com/riscv/riscv-unified-db)

Author: Rajveer Bishnoi ([@RAJVEER42](https://github.com/RAJVEER42))

---

## Summary

Two snippets of the Privileged specification, 185 words total. Result:
**1 architectural parameter, 11 rejected candidates.**

The interesting part is not the parameter — `CACHE_BLOCK_SIZE` already exists
upstream, and every model found it in all 18 runs. The interesting parts are:

- **The one signal word in 185 words.** Across both snippets exactly *one*
  challenge-listed signal phrase occurs. Snippet 2.1 contains none, so its
  correct yield is **zero**. Verified mechanically, not by reading.
- **A failure that reproduced in 9 of 9 runs across 3 models from 2 labs** —
  and therefore is a property of the prompt, not of any model.
- **A fabricated quotation, caught by a program.** One model elided eleven
  words behind an ellipsis and presented it as verbatim. A human reviewer
  would have accepted it. One substring test did not.
- **A defect in my own reasoning, found by the models.** Two models defeated my
  ISA-visibility test with a coherent argument grounded in the passage. They
  were wrong, but the gap they exploited was real and mine.
- **Two latent defects in `riscv-unified-db`**, found by reading the schema the
  output has to fit.

Everything asserted here was checked against source. Where something is
unverified, it says so.

### Reproduce it

```bash
./run.sh                 # offline: trigger scan + revalidate committed output
./run.sh --udb <path>    # also validate against a riscv-unified-db checkout
./run.sh --with-models   # re-run the models (needs credentials)
```

Stages 1–3 need no credentials and no spend. Stage 3 **re-derives every numeric
claim in this README from the raw output in `results/`** — 51 checks, and it
fails loudly on any mismatch. None of the figures below are asserted; all of
them are recomputed.

---

## 1. Deliverable 1 — the models

| | Model A | Model B | Model C |
|---|---|---|---|
| **Name** | DeepSeek-V4-Pro | Gemini 3.6 Flash | Gemini 2.5 Flash |
| **Exact ID** | `deepseek-ai/DeepSeek-V4-Pro` | `gemini-3.6-flash` | `gemini-2.5-flash` |
| **Context (input)** | **1,048,576** | 1,048,576 | 1,048,576 |
| **Max output** | — | 65,536 | 65,536 |
| **Weights** | open, **MIT** | proprietary | proprietary |
| **Access** | HF Inference Providers | Google AI Studio, free tier | Google AI Studio, free tier |
| **Architecture** | `DeepseekV4ForCausalLM`, bfloat16, MoE | undisclosed | undisclosed |
| **Reasoning model** | yes | yes | yes |

Context lengths read from each model's own `config.json` / API metadata, not
recalled. DeepSeek's 1,048,576 is reached by **YaRN** RoPE scaling (`factor: 16`)
from a native `original_max_position_embeddings` of **65,536** — stated precisely
because effective quality at full extension is not guaranteed. Irrelevant for
185-word snippets; relevant if the pipeline is ever pointed at the whole spec.

**Run parameters:** `temperature=0`, `max_tokens` 8,000–16,000 recorded per run,
**N=3 runs per model per snippet per prompt version**, `finish_reason` asserted.
No parameter-name list supplied — see §5.1.

### Two models that are not here, and why

**`gemini-2.5-pro`** is not on the free tier. All 6 calls returned
`429 RESOURCE_EXHAUSTED` — quota zero, not exhausted. The failures are committed
with `status: "error"` rather than deleted.

**Claude Opus 5** was deliberately excluded. The session that produced this work
had already read `ground_truth.md`; anything it generated would not be an
independent extraction, and substituting it would have inflated the submission's
central number. This is a real limitation, stated rather than hidden. Fixing it
needs a clean-context or API-key run.

### Cost

| Model | v1 prompt / completion | v2 prompt / completion | Cost |
|---|---|---|---|
| DeepSeek-V4-Pro | 2,217 / 6,255 | 9,087 / 17,618 | fractions of a cent |
| Gemini 3.6 Flash | 2,310 / 457 | 9,396 / 1,762 | free tier |
| Gemini 2.5 Flash | 2,310 / 444 | 9,396 / 2,491 | free tier |

v2 cost **4.1× the prompt tokens** and 2.8–5.6× the completion tokens of v1. At
185 words that is free; at 52,000 spec lines it is the dominant cost, and the
comparison against v1's precision gain is not obviously favourable.

---

## 2. Deliverable 3 — results

**[`parameters.yaml`](parameters.yaml)** — flat shape, the four requested fields
plus provenance, ISA-visibility justification, and the rejected candidates.

**[`udb/CACHE_BLOCK_SIZE.yaml`](udb/CACHE_BLOCK_SIZE.yaml)** — UDB-native shape,
**validated against the real `param_schema.json`** with `$refs` resolved
(`scripts/validate_udb.py`). Not "shaped to look plausible" — checked.

Why two shapes: in UDB, `type` and `constraints` are **not** top-level fields.
They live inside `schema:` as ordinary JSON Schema. Mapping the challenge's
requested shape onto UDB is a translation step, and proposal item 4 is exporting
parameters in UDB YAML format.

### The parameter

| Field | Value |
|---|---|
| `name` | `CACHE_BLOCK_SIZE` |
| `type` | `integer` |
| `constraints` | power of two; uniform system-wide, **scoped to "the initial set of CMO extensions"** |
| `trigger` | `implementation-specific` |
| `isa_visible` | CMO instructions operate on a cache block, so software must know its size |

No numeric bound is asserted. The passage states none, and inventing one is the
constraint-invention failure this work set out to avoid.

### The rejected candidates carry most of the information

11 rejections against 1 parameter. Four reason codes: `NOT_ISA_VISIBLE`,
`FIXED_BY_ARCHITECTURE`, `CONSTRAINT_NOT_PARAMETER`, `NOT_STATED_IN_TEXT`.

The three that matter most:

| Candidate | Reason | Why |
|---|---|---|
| **Cache capacity / organization** | `NOT_ISA_VISIBLE` | Explicitly implementation-specific, so passes the trigger test — but no instruction's behaviour depends on it. **Corroborated: no such parameter exists among UDB's 227.** The maintainers drew the same line |
| **Uniformity of block size** | `CONSTRAINT_NOT_PARAMETER` | `shall` is a mandate; it removes freedom. A constraint on the parameter, not a parameter |
| **Which CSRs are implemented** | `NOT_STATED_IN_TEXT` | Genuinely implementation-dependent, and **the passage never says so.** Emitting it means answering from RISC-V knowledge rather than from the input |

That last one is the trap. It was recorded in `ground_truth.md` before any model
ran; **DeepSeek independently surfaced it and rejected it with the same reason
code in 3/3 runs.**

---

## 3. Deliverable 2 — prompt development

The part the challenge actually asks about. Git history is the evidence: one
commit per phase, and the ordering is load-bearing.

### 3.0 Ground truth first — before any model ran

`ground_truth.md` was committed at **`9d3a0cb`**, before any file in `results/`
existed. It contains the adjudication of all 12 candidates, a stated decision
rule, **7 falsifiable predictions**, and 3 conditions that would prove the
ground truth itself wrong.

This ordering is the difference between measuring the models and being persuaded
by them. It also makes every claim below checkable: compare commit timestamps.

### 3.1 The fact base, established mechanically

`scripts/scan_triggers.py`, no model involved:

```
brief-listed trigger phrases across all snippets: 1
```

| Snippet | Signal words | Other modals |
|---|---|---|
| 19.3.1 (96 w) | `implementation-specific` ×1 | `shall` ×1 |
| 2.1 (89 w) | **none** | `can`, `by convention`, `"Conventional"` |

Two consequences:

**`shall` is not `should`.** The challenge lists *should* — a recommendation.
19.3.1 contains *shall* — a mandate. Near-opposites: `shall` **removes**
implementation freedom. Any matcher doing stemming or synonym expansion treats it
as a hit and inverts the sentence's meaning.

**Snippet 2.1 is a negative control.** No signal words, so expected yield zero —
a precision test, and falsifiable.

### 3.2 A grounding test the scan revealed

The snippets say `CMO` but **never** name `Zicbom`/`Zicbop`/`Zicboz`. UDB's real
`CACHE_BLOCK_SIZE` is `definedBy: anyOf [Zicbom, Zicbop, Zicboz]`, and all three
models name those extensions correctly *unprompted*.

So any output naming them is **correct but ungrounded** — from training data, not
from the 96 words provided. *Correct ≠ grounded*, and mechanically detectable.
This is the whole argument for substring-checked excerpts.

### 3.3 v1 — the brief, competently followed

[`prompts/v1/`](prompts/v1/) · 135 words. Exactly what the challenge supplies:
the trigger list verbatim, the four output fields, minimal scaffolding.

**Deliberately no better.** It would be easy to cripple v1 and claim a large v2
improvement — and since the refinement narrative is what's being assessed, faking
it is the worst available move. The standard: *what a competent engineer writes
having read the brief and nothing else.* Which is, roughly, the submission most
applicants will send.

Nine omissions were documented **before** the run, each mapped to its predicted
consequence, so the analysis is a test rather than a rationalisation.

### 3.4 What v1 got wrong

Full detail: [`analysis/v1_failures.md`](analysis/v1_failures.md).

**The dominant failure — 9 of 9 runs, 3 models, 2 labs:**

| Model | Emitted from 19.3.1 | Precision |
|---|---|---|
| DeepSeek-V4-Pro | `CACHE_BLOCK_SIZE` + **`CACHE_CAPACITIES`** + **`CACHE_ORGANIZATIONS`** | 1/3 |
| Gemini 3.6 Flash | `CACHE_BLOCK_SIZE` + **`CACHE_CAPACITY`** + **`CACHE_ORGANIZATION`** | 1/3 |
| Gemini 2.5 Flash | same | 1/3 |

The models are not hallucinating — the snippet *does* call those
implementation-specific. They fail the second half of the rule:
**implementation-specific ≠ ISA-visible.** A failure this universal across
independent models is a property of the *prompt*.

**Three of seven predictions were refuted.** Reported as such:

- **P3 refuted.** All three models returned `parameters: []` for snippet 2.1 —
  0/9 over-extraction, with no negative examples and no permission to return
  empty. This refutes the common premise that LLMs are strongly biased toward
  producing output.
- **P5 was my error** — no model named the Zicbo\* extensions, but v1's schema
  had **no field where an extension name could go**. The prediction was
  untestable by construction.
- **P6 refuted** — all models correctly treated uniformity as a constraint.

**The negative control still did its job.** Because the same models decline
cleanly on 2.1, the 19.3.1 failure is provably *not* general eagerness — it is
specifically the ISA-visibility test. Those two findings only make sense
together, and neither is interpretable alone.

**Other findings:** DeepSeek produced *three incompatible data models* for cache
internals across three runs at `temperature=0` — while being perfectly stable on
`CACHE_BLOCK_SIZE`. Both Gemini models wrote `constraints: Implementation-specific.`,
a category error: the trigger phrase is *evidence a parameter exists*, not a
restriction on its value. And 15 of 18 outputs were markdown-fenced despite
"Output valid YAML only" — DeepSeek *intermittently*, which is worse than
consistently.

### 3.5 v2 — and the trap I had to avoid

[`prompts/v2/`](prompts/v2/) · 862 words · 11 changes, each traceable to a
specific v1 failure.

**The obvious fix would have been cheating.** v1's dominant failure was emitting
cache capacity, so the natural v2 fix is a negative example saying *"cache
capacity is not a parameter."* But **snippet 19.3.1 is an evaluation input** —
putting its answer in the prompt measures recitation, not reasoning.

This is precisely the error Part I made by injecting the 185 gold parameter names
into every prompt (§5.1). Having criticised it, repeating it would be
indefensible.

So v2 encodes the test as a **general principle** with **off-snippet examples
only** — pipeline depth, branch predictor size, WARL-with-fixed-legal-values, and
an `ASID_WIDTH` worked example verified against the real UDB file. A mechanical
check confirms no snippet-specific term (`cache`, `NAPOT`, `capacity`,
`CMO`, `Zicbo`, `csr[11`, …) appears anywhere in the v2 prompts.

**Cost of that discipline:** a smaller improvement than a leaked example would
have produced. That is the correct trade.

Main changes: **T1/T2/T3 applied in order** with "a signal word is evidence, not
proof" · a required **`isa_visible`** field so T3 must be *shown* · mandatory
**verbatim `excerpt`**, declared as mechanically checked · **structured
`constraints`** · an explicit **ban on signal words as constraint values** · a
**`rejected` list** with reason codes · **`defined_by` only if the passage names
it** · **`shall`/`must` excluded** from signal words.

**Deliberately not added: permission to return an empty list.** §3.4 shows all
three models already do so unprompted. Adding it would fix a problem we do not
have, and risks inducing over-declining where a real parameter exists. The
discipline being tested is *adding only what the evidence demands*.

### 3.6 Results — honest scorecard

Full detail: [`analysis/v2_delta.md`](analysis/v2_delta.md).

| | v1 | v2 |
|---|---|---|
| Over-extraction on 19.3.1 | 9/9 runs | **6/9** |
| Gold-set recall | 9/9 | 9/9 |
| Snippet 2.1 correctly empty | 9/9 | 9/9 |
| Markdown fenced | 15/18 | **6/18** |
| `constraints` category errors | many | **zero** |
| `rejected` populated on 2.1 | n/a | **9/9** |

**The entire precision improvement comes from one model of three.**
Gemini 3.6 Flash went from 3/3 over-extracting to 0/3, rejecting both candidates
as `NOT_ISA_VISIBLE`. DeepSeek and Gemini 2.5 Flash were unmoved.

So **"v2 is better than v1" is not established as a prompt-level claim** — it is
confounded with model identity. What *is* established: v2 exposed reasoning that
v1 hid.

**The biggest qualitative win is auditability.** On snippet 2.1, v1 gave:

```yaml
parameters: []
```

Correct and uninformative — no way to tell careful reasoning from noticing
nothing. v2 gave the same verdict with four reason-coded rejections. At spec
scale, that is the difference between output a maintainer can review and output
they must trust.

---

## 4. Deliverable 2 — hallucinations

The challenge asks how model hallucinations were dealt with. The short answer:
**not by instructing the model. By making claims checkable, and checking them.**

Five distinct failure modes were observed, and they need different treatments.

| # | Mode | Example observed | Treatment |
|---|---|---|---|
| 1 | **Fabricated quotation** | `"The ... size of a cache block…"` | ✅ mechanical substring check |
| 2 | **Ungrounded-but-correct** | "in bytes" — true, absent from passage | ✅ check + explicit rule |
| 3 | **Category error** | `constraints: Implementation-specific.` | ✅ validator check E2 |
| 4 | **Faithful-but-wrong reasoning** | the execution-environment argument | ❌ **not** solvable by checking |
| 5 | **Truncation as false negative** | empty content read as "no parameters" | ✅ `finish_reason` guard |

### 4.1 The fabricated quotation

`gemini-2.5-flash`, 19.3.1 run 2:

```yaml
excerpt: "The ... size of a cache block are both implementation-specific"
```

The passage says *"The **capacity and organization of a cache and the** size of a
cache block are both implementation-specific."* **Eleven words elided behind an
ellipsis, presented as verbatim.**

Why this is the most useful single result here:

1. **It survives human review.** The elided quote is semantically faithful and
   the ellipsis reads as scholarly care. I would have accepted it.
2. **It defeats the purpose of provenance** — an elided quote cannot be located
   by search, which is the entire point of the field.
3. **It was inconsistent within one response.** The same run quoted that *same
   sentence* correctly and in full for two other parameters. Not a capability
   limit — an unpredictable shortcut, which is worse, because it passes any
   single-run spot check.
4. **One `in` test caught it**, in milliseconds, with no model grading another
   model.

Prediction Q7 said all 18 excerpts would pass. It was flagged in advance as *the
one worth being wrong about*, and it was wrong.

### 4.2 Truncation masquerading as a correct empty result

All candidate models are reasoning models. One that exhausts its budget returns
**empty content**. Parsed naively that reads as *"the model found no
parameters"* — which is the **correct** answer for snippet 2.1. So truncation
would masquerade as exactly the behaviour being measured, and would have
*inflated* the precision score via a bug.

The runner therefore treats `finish_reason != "stop"` as a **run failure, never
an empty result**. It caught six cases on its first use — the `gemini-2.5-pro`
quota failures, a mode it was not even designed for. Cost: one `if`.

### 4.3 🏆 The mode checking cannot fix — and it found a hole in my own reasoning

Both models that still emitted `CACHE_CAPACITY` under v2 justified it
identically, with `confidence: high`, in **6 of 6 opportunities**:

> *"Software can discover the cache capacity through the means provided by the
> execution environment."*

**This is not a fabrication.** It is a coherent argument citing a real sentence
of the passage. Every mechanical check passes: the excerpt is genuine, the field
is populated, nothing is invented.

And it is wrong, for a reason **my prompt failed to state**: discoverability via
the execution environment is not ISA-visibility, because the execution
environment — device tree, configuration structure, SBI — is *outside the ISA*.

The uncomfortable part: **`ground_truth.md` already had this right**, listing the
discovery mechanism as `NON_ISA`. I knew the distinction and did not encode it
into T3. The models did not misread the prompt — they read it correctly and
exploited a real gap.

Worse, **the passage baits the loose reading**: the clause declaring capacity
implementation-specific and the clause promising a discovery mechanism are *the
same sentence, joined by "and"*.

**And Gemini 3.6 Flash did not fall for it**, rejecting both as
`NOT_ISA_VISIBLE` in 3/3 runs from the identical prompt. One underspecified gate,
three models, two opposite readings — cross-model disagreement that *localises a
specific defect* rather than just producing a low agreement coefficient.

**The v3 fix is one sentence** and fully specified by this evidence. It is
deliberately **not applied**: inventing v3 after seeing v2's results, in the same
breath as reporting them, is how a clean measurement becomes a fitted one. It is
recorded as the next experiment, and it is in the reusable skill so the lesson
is not lost.

**The transferable lesson:** structural checks catch fabrication. They cannot
catch *faithful reasoning from an underspecified rule*. For that, the defence is
requiring the model to state its justification — which did not prevent the error
but **explained** it. Diagnostic, not corrective, and worth more.

---

## 5. Reading the prior art

### 5.1 Part I's recall figures measure grounding, not discovery

On [issue #2053](https://github.com/riscv/riscv-unified-db/issues/2053),
**`titoatwork`** published measurements of the public Part I snapshot and then
posted a self-correction. I re-verified the load-bearing claim independently
rather than inherit it — fetched both files from the PR #1791 head:

```
injected list size : 185
gold set size      : 185
identical sets     : True
```

`extract.py:211` `build_user_message()` injects that list into **every** prompt —
no flag, no branch — with *"When a parameter you find matches one of these known
names, use the exact name."*

**So Part I's 69.7% is grounding recall, not discovery recall.** The model was
handed the answer names. `HANDOFF.md` §6 previously cited it as the bar to beat;
that is corrected. WARL recall of 12/24 likewise happens *with all 24 names in
the prompt* — so the failure is **identification, not vocabulary**, which is why
adding WARL prompt guidance made results *worse*.

Attribution, since it is easy to get wrong: the WARL evaluation, the ablation,
and the legal-value-set refinement are **`titoatwork`'s**. **`hjaat`** opened the
issue and raised the WARL problem conceptually, credited to a Slack exchange with
**Allen Baum**.

**Our runs supply no name list.** Our numbers are therefore *not comparable* to
Part I's — stated explicitly rather than left to imply a favourable comparison.

### 5.2 One principle, reached from two directions

`titoatwork`'s WARL refinement and our cache-capacity finding are the same rule:

| Case | Signal | Real choice? | Parameter? |
|---|---|---|:--:|
| cache block size | "implementation-specific" | yes, ISA-visible | ✅ |
| cache capacity *(ours)* | "implementation-specific" | yes, but **ISA-invisible** | ❌ |
| WARL, fixed legal set *(theirs)* | labelled "WARL" | **no choice exists** | ❌ |
| CSR address mapping | "By convention" | architecturally assigned | ❌ |

> A signal of implementation freedom is necessary but not sufficient. A parameter
> exists only where the implementation genuinely chooses, and that choice is
> ISA-visible.

Also relevant: `ishaan-arora-1` states on that issue that the current pipeline is
**internal and unpublished**, and PRs #1765–#1832 are the first version. They are
background, not current state.

---

## 6. Findings in `riscv-unified-db`

Found by reading the schema the output has to fit
([`reference/udb-schema-notes.md`](reference/udb-schema-notes.md), commit
`bd775a94`). Reported here because they affect this challenge's output; each
needs a maintainer's view before becoming a PR.

### 6.1 Two implementations of "power of two" that disagree

A cache block is a NAPOT range, so `CACHE_BLOCK_SIZE` is always a power of two.
Upstream's schema is `minimum: 1, maximum: 2^64-1` — admitting 3, 5, 7, 100.

`schema_defs.json` already defines `64bit_unsigned_pow2`, and `$ref`-ing it is
precedented (`CONFIG_PTR_ADDRESS`, `IMP_ID_VALUE`, `ARCH_ID_VALUE`). **But that
def cannot be adopted as-is:**

| Value | JSON-Schema enum | `z3.rb` (`x & (x-1)`) | Correct |
|---|:--:|:--:|---|
| **4096** = 2^12 | ❌ rejects | ✅ accepts | Z3 |
| **4095** | ✅ accepts | ❌ rejects | Z3 |

`4095` sits where `4096` belongs, at `schema_defs.json:866` and `:876`, in both
pow2 enums. It is the *only* non-power-of-two in either, and 4096 is absent from
both. Demonstrated, not asserted:

```
value     64 -> accepted
value   4095 -> accepted  <-- WRONG
value   4096 -> REJECTED  <-- WRONG
```

**Why it survived:** repo-wide grep over the full tree shows the pow2 defs
referenced in exactly three places — `z3.rb` and two test files. **No file under
`spec/` `$ref`s either def**, and `z3.rb` ignores the enum entirely. Dead data
does not fail.

**So the fix for the missing constraint is blocked by this defect** — that
ordering is worth more than either finding alone. Our emitted file spells the
enum inline instead, following the `MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE`
precedent.

*Deliberately not claimed:* that this breaks anything today. Whether a config
supplying `CACHE_BLOCK_SIZE: 4096` is rejected requires tracing the
value-validation path.

### 6.2 `long_name: TODO` in 163 of 227 files

**71.8%** carry the placeholder, including `CACHE_BLOCK_SIZE`. This reframes the
problem: the repo's unmet need is not *finding* parameters — the maintainers
found 227 — but **populating prose fields at scale**, which is slow for a human
and natural for an LLM. Directly on proposal item 4.

*Caveat:* usage is inconsistent upstream (`MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE`
inverts the convention), so `long_name` may be under deprecation. A SIG question,
not an assumption.

### 6.3 Open questions

1. Is `long_name` being deprecated, or should the 163 `TODO`s be filled?
2. Should `CACHE_BLOCK_SIZE` adopt `64bit_unsigned_pow2`, and is `4095` known?
3. Where does a **system-scoped** invariant like uniform block size belong, given
   parameters are largely per-hart?

---

## 7. Repository map

| Path | What |
|---|---|
| [`parameters.yaml`](parameters.yaml) | **Deliverable 3** — 1 parameter, 11 rejections, provenance |
| [`udb/CACHE_BLOCK_SIZE.yaml`](udb/) | UDB-native shape, schema-validated |
| [`ground_truth.md`](ground_truth.md) | Adjudication + 7 predictions, **committed before any run** |
| [`prompts/v1/`](prompts/v1/), [`prompts/v2/`](prompts/v2/) | Both prompts, each with design notes and contamination controls |
| [`results/`](results/) | **All 42 run records, raw and unedited** — 36 usable, 6 failures kept |
| [`analysis/`](analysis/) | v1 failures; v1→v2 delta |
| [`scripts/scan_triggers.py`](scripts/) | Mechanical trigger scan |
| [`scripts/run_extraction.py`](scripts/) | Multi-provider runner, `finish_reason` guard |
| [`scripts/validate.py`](scripts/) | 8 checks incl. excerpt grounding |
| [`scripts/validate_udb.py`](scripts/) | Validates against real `param_schema.json` |
| [`scripts/audit_claims.py`](scripts/) | **Re-derives all 51 numeric claims in this README from `results/`** |
| [`.claude/skills/param-extract/`](.claude/skills/) | **Reusable skill** — proposal item 3 |
| [`run.sh`](run.sh) | One-command reproduction |
| [`HANDOVER.md`](HANDOVER.md) | The instrument, packaged for reuse at corpus scale |
| [`reference/`](reference/) | Verified notes: UDB schema, models, prior art |

Git history is deliberate evidence: one commit per phase, and the **ordering**
of `ground_truth.md` (`9d3a0cb`) before `results/`, and `validate.py`
(`2c1badf`) before the v2 runs, is what makes the measurements meaningful.

---

## 8. Limitations

Stated plainly, because a submission that hides these is less trustworthy than
one that names them.

- **n = 2 snippets, 1 gold parameter, 36 usable runs.** Every figure is a count, not a
  rate. Nothing generalises to the full spec. No Jaccard coefficient is
  reported — at this n it would be meaningless.
- **"Precision 1/3 → 1/1"** describes three runs of one model, not a measured
  improvement in a general capability.
- **v2's gain is confounded with model identity.** Only one of three models
  improved.
- **Tier asymmetry.** DeepSeek-V4-Pro is Pro-tier; both Geminis are Flash-tier,
  because Pro is not free. This is not a model ranking.
- **Claude Opus 5 absent** — contamination (§1).
- **The gold set is mine.** DeepSeek's independent rejection of the
  `NOT_STATED_IN_TEXT` trap corroborates one judgement; the rest rests on my
  reading. Three falsification conditions were stated in advance; none were met.
- **v3 is specified but unrun.** The execution-environment fix is identified and
  deliberately not applied (§4.3).
