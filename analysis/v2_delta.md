# v1 → v2 delta

Phase 7 of the build plan. Scored against `ground_truth.md` (`16ea944`) using
`scripts/validate.py`, committed at `f3e4858` — **before any v2 output existed**.

**Headline: v2 improved, unevenly, and for a diagnosable reason. The most
valuable result is a hole v2 opened in my own reasoning, not a number that went
up.**

---

## 1. The numbers

Snippet 19.3.1. Gold set: exactly one parameter, `CACHE_BLOCK_SIZE`.

| Model | v1 params emitted | v1 precision | v2 params emitted | v2 precision | Δ |
|---|---|---|---|---|---|
| **gemini-3.6-flash** | `BLOCK_SIZE`, `CAPACITY`, `ORGANIZATION` | 1/3 | **`BLOCK_SIZE` only** | **1/1** | ✅ **fixed, 3/3 runs** |
| gemini-2.5-flash | `CAPACITY`, `ORGANIZATION`, `BLOCK_SIZE` | 1/3 | *unchanged* | 1/3 | — no change |
| DeepSeek-V4-Pro | varied, 2–3 params | 1/3 – 1/2 | `CAPACITY`, `ORGANIZATION`, `BLOCK_SIZE` | 1/3 | — no change |

**Recall of the gold set: 9/9 in both versions.** `CACHE_BLOCK_SIZE` was never
missed, and v2's extra machinery did not cause it to be lost.

> ⚠️ **Later finding, added after `analysis/exp1_results.md`.** That 9/9 is
> true and misleading. Experiment 1 shows all runs justified the correct
> parameter with the *wrong* reason, citing execution-environment
> discoverability rather than the cache-management operations that actually
> make block size ISA-visible. Delete the one clause that supplied that wrong
> reason and recall falls to 2 of 6. Read this number alongside
> `exp1_results.md` §4, not on its own.

**Over-extraction: 9/9 runs in v1 → 6/9 in v2.** The entire improvement comes
from **one model out of three.**

Snippet 2.1: `parameters: []` in **9/9 runs, both versions.** No regression.

## 2. Preregistered predictions, scored

| # | Prediction | Outcome |
|---|---|---|
| Q1 | `CACHE_BLOCK_SIZE` in ≥8/9 runs | ✅ 9/9 |
| Q2 | capacity/org as parameters in fewer runs than 9/9 | ✅ 6/9 — **but from one model only** |
| Q3 | capacity/org rejected as `NOT_ISA_VISIBLE` in ≥5/9 | ❌ **3/9** — predicted too high |
| Q4 | 2.1 still `[]` in 9/9, no regression | ✅ 9/9 |
| Q5 | ≥1 model populates `rejected` for 2.1 | ✅ **all 3 models, 9/9 runs** |
| Q6 | `defined_by` null for block size in ≥7/9 | ✅ 8/9 |
| Q7 | 100% of excerpts pass the substring check | ❌ **17/18 — see §3** |
| Q8 | ≥1 model confabulates `isa_visible` | ✅ **6/6 opportunities — see §4** |
| Q9 | fencing below 15/18 | ✅ **6/18** |

Seven confirmed, two refuted. Both refutations are more useful than the
confirmations.

## 3. 🔴 The validator caught a fabricated quotation

`gemini-2.5-flash`, 19.3.1 run 2, on `CACHE_BLOCK_SIZE`:

```yaml
excerpt: "The ... size of a cache block are both implementation-specific"
```

The passage says:

> "The **capacity and organization of a cache and the** size of a cache block are
> both implementation-specific"

**The model elided eight words with an ellipsis and presented the result as a
verbatim quote.** Prediction Q7 said all excerpts would pass. It was wrong, and
I flagged it in advance as the one worth being wrong about.

Why this is the single best result in the submission:

1. **It is a hallucination that survives human review.** The elided quote is
   *semantically* faithful, and the ellipsis even reads as scholarly honesty. A
   reviewer skimming a table of extracted parameters would accept it without a
   second thought. I would have accepted it.
2. **It defeats the purpose of provenance.** The whole point of `excerpt` is that
   a reader can locate the claim in the source. An elided quote cannot be
   located by search.
3. **It was inconsistent within a single run.** The same response quoted the
   *same sentence* correctly and in full for `CACHE_CAPACITY` and
   `CACHE_ORGANIZATION`. So this is not a capability limit — it is an
   unpredictable shortcut, which is strictly worse, because it would pass any
   single-run spot check.
4. **A mechanical check found it in milliseconds, with no judgement involved.**
   One `in` test. No model grading another model.

This is the concrete answer to *"how did you deal with hallucinations."* Not
"I instructed the model not to" — **"I made the claim checkable, and the check
caught one in eighteen."**

## 4. 🏆 The headline finding: my own T3 gate had a hole, and the snippet baits it

v2's T3 asks whether a value is ISA-visible. Both models that still emitted
`CACHE_CAPACITY` justified it identically, with `confidence: high`, in **6 of 6
opportunities**:

> DeepSeek: *"Software can discover the cache capacity through the means provided
> by the execution environment."*
>
> gemini-2.5-flash: *"Software can discover this information through means
> provided by the execution environment."*

**This is not a fabrication. It is a coherent argument, grounded in a real
sentence of the passage** — *"the execution environment provides software a means
to discover information about the caches and cache blocks in a system."*

And it is **wrong**, for a reason my prompt failed to state:

> **Discoverability via the execution environment is not ISA-visibility.** The
> execution environment — device tree, configuration structure, SBI — is by
> definition *outside* the ISA. That a value is discoverable *somehow* says
> nothing about whether any instruction's defined behaviour depends on it.

The uncomfortable part: **`ground_truth.md` §3.2 already had this right.** It
lists the discovery mechanism as candidate C5, rejected as `NON_ISA`. I knew the
distinction and **failed to encode it into T3.** The models did not misread the
prompt; they read it correctly and exploited a genuine gap, then cited the
passage to support it.

Worse, the passage **actively baits the loose reading**: the sentence declaring
capacity implementation-specific and the sentence promising a discovery
mechanism are *the same sentence*, joined by "and". The text places the bait
adjacent to the hook.

**And gemini-3.6-flash did not fall for it** — rejecting capacity and
organization as `NOT_ISA_VISIBLE` in 3/3 runs, from the identical prompt. So the
same underspecified gate produces opposite readings depending on the model. That
is the cross-model disagreement result from `prior-art.md` §7, now with a
*mechanism* rather than just a coefficient.

**The v3 fix is one sentence**, and it is fully specified by this evidence:

> T3 does not count discoverability through the execution environment. The
> execution environment is outside the ISA. Ask instead whether an *instruction's
> defined behaviour* changes with this value.

I have deliberately **not** applied it. v3 would need its own runs and its own
preregistered predictions, and inventing a v3 after seeing v2's results — in the
same breath as reporting them — is how a clean measurement becomes a fitted one.
It is recorded as the next experiment, not folded in silently.

## 5. ✅ What v2 unambiguously fixed

### 5.1 Judgement is now visible — the biggest qualitative change

On snippet 2.1, v1 produced this, from every model:

```yaml
parameters: []
```

Correct, and completely uninformative. There was no way to distinguish a model
that reasoned carefully from one that noticed nothing.

v2, same snippet, `gemini-2.5-flash` (identical in 3/3 runs):

```yaml
parameters: []
rejected:
  - candidate: CSR address space width          reason: FIXED_BY_ARCHITECTURE
  - candidate: Use of csr[11:8] for accessibility encoding   reason: FIXED_BY_ARCHITECTURE
  - candidate: Meaning of csr[11:10] for R/W status          reason: FIXED_BY_ARCHITECTURE
  - candidate: Meaning of csr[9:8] for privilege level       reason: FIXED_BY_ARCHITECTURE
```

The same empty result, now **auditable**. This is what makes an extraction
reviewable at spec scale: a maintainer can check the *reasoning*, not just the
output. It directly addresses the gap identified in `prompts/v1/README.md` §3.

### 5.2 DeepSeek independently found our trap candidate — with the right reason

`ground_truth.md` §4.2 named candidate **D5, "which CSRs are implemented"**, as
the most informative rejection: genuinely implementation-dependent, but *not
stated in this passage*, so extracting it is fabrication from model priors.

DeepSeek rejected exactly that, in **3/3 runs**, with reason
`NOT_STATED_IN_TEXT`:

```yaml
- candidate: Number of implemented CSRs
  reason: NOT_STATED_IN_TEXT
```

It found the trap, and labelled it with the one correct code out of four. This
is independent corroboration of a ground-truth judgement made before any model
ran — the strongest kind of agreement available here, since neither could have
influenced the other.

Note the models split on *which* candidates they surfaced: DeepSeek found D5
(the out-of-text trap); both Geminis found D1–D4 (the fixed conventions). Both
sets are correct rejections. Neither model found all of them.

### 5.3 Grounding held where it was tested

- `defined_by` was `null` in 8/9 runs. The one exception, DeepSeek run 1, wrote
  `"CMO extensions"` — which **is** in the passage. **No model wrote
  `Zicbom`/`Zicbop`/`Zicboz`**, despite all of them knowing those names
  unprompted (`reference/models.md` §2). Rule 3 held. This is the P5 test that
  v1 could not run.
- `constraints` category errors: **zero** in v2. v1's `constraints:
  Implementation-specific.` did not recur in any of 18 runs.
- Fencing: 15/18 → **6/18**.

## 6. Costs and regressions

Honest accounting of what v2 made worse.

| Cost | Detail |
|---|---|
| **Token cost** | DeepSeek 6,255 → **17,618** completion tokens (**2.8×**). Prompt tokens 2,217 → 9,087 (**4.1×**). At spec scale this is the dominant cost |
| **Latency** | DeepSeek up to **118 s** on a single run, vs ~44 s max in v1 |
| **Reason-code accuracy is imperfect** | `gemini-2.5-flash` labelled cache-block uniformity `FIXED_BY_ARCHITECTURE` in runs 1 and 3, but `CONSTRAINT_NOT_PARAMETER` in run 2. Ground truth says the latter. **1/3 correct, and unstable within one model** |
| **Q3 missed** | Only 3/9 runs produced the `NOT_ISA_VISIBLE` rejection, against a predicted ≥5/9 |
| **No precision gain for 2 of 3 models** | §4 explains why, but it remains a real limitation |

No regression on the two things that mattered most: gold-set recall stayed 9/9,
and snippet 2.1 stayed empty in 9/9.

## 7. What this says about prompt engineering

Three transferable conclusions, each supported by evidence above.

1. **A structural check beats an instruction.** v2 *told* models to quote
   verbatim; one did not. The instruction did not prevent the failure — the
   validator detected it. Prompts request; programs verify.
2. **Requiring a justification field surfaces reasoning errors that would
   otherwise be invisible.** Had v2 not demanded `isa_visible`, DeepSeek and
   gemini-2.5-flash would have emitted `CACHE_CAPACITY` with no indication *why*,
   and the execution-environment loophole would never have been found. **The
   field's value was diagnostic, not corrective** — it did not stop the error, it
   explained it. That is worth more.
3. **Underspecified criteria fail model-dependently.** One gate, one prompt,
   three models, two opposite readings. Cross-model disagreement is not noise to
   average away; here it localised a specific defect in my own definition.

## 8. Threats to validity

- **n = 2 snippets, 18 runs, 1 gold parameter.** Every number here is a count,
  not a rate. Nothing generalises to the spec. No Jaccard
  (`prior-art.md` §7).
- **A single gold parameter** means "precision 1/3 → 1/1" describes three
  runs of one model, not a measured improvement in a general capability.
- **Tier asymmetry** persists: DeepSeek-V4-Pro is Pro-tier, both Geminis are
  Flash-tier. Not a model ranking.
- **Claude Opus 5 still absent** — contamination (`v1_failures.md` §1.1).
- **The gold set is mine.** §5.2 is genuine independent corroboration of one
  judgement; the rest rests on my reading. The three falsification conditions in
  `ground_truth.md` §6 stand, and none were met.
- **v2's improvement is confounded with model identity.** Because only one of
  three models improved, "v2 is better than v1" is not established as a
  prompt-level claim. What *is* established: v2 exposed reasoning that v1 hid.
