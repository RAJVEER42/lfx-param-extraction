# v1 failure analysis

Phase 4 of the build plan. Scored against `ground_truth.md`, which was committed
(`16ea944`) **before** any run in `results/` existed.

18 runs attempted · 18 recorded · 12 usable extractions from 3 models.

---

## 1. What ran

| Model | Provider | Runs | Status | Prompt tok | Completion tok |
|---|---|:--:|---|---:|---:|
| `deepseek-ai/DeepSeek-V4-Pro` | HF Inference | 6 | ok | 2,217 | 6,255 |
| `gemini-3.6-flash` | Google free tier | 6 | ok | 2,310 | 457 |
| `gemini-2.5-flash` | Google free tier | 6 | ok | 2,310 | 444 |
| `gemini-2.5-pro` | Google free tier | 6 | **error** | — | — |

### 1.1 Two absences that must be stated, not glossed

**`gemini-2.5-pro` is not available on the free tier.** Every call returned
`429 RESOURCE_EXHAUSTED` immediately — quota is zero, not exhausted. The six
failures are committed with `status: "error"` rather than deleted.

**Claude Opus 5 was deliberately not run.** The session driving this work has
read `ground_truth.md`; anything it produced would not be an independent
extraction. Substituting it silently would have inflated the strongest number in
the submission. This is a real limitation of the submission, and the honest fix
is a clean-context or API-key run, not a footnote.

### 1.2 🔑 The truncation guard earned its place on day one

The six `gemini-2.5-pro` failures returned **no content**. A harness that parsed
response text without checking `finish_reason` and error state would have read
them as *six runs that correctly found no parameters* — and snippet 2.1's
correct answer **is** "no parameters".

So the guard from `reference/models.md` §3 prevented six fabricated successes on
its first outing, against a failure mode (quota, not truncation) it was not even
designed for. Cost of the guard: one `if`. This is the single most concrete
answer available to *"how did you deal with hallucinations"* — the best defence
was structural, not a prompt instruction.

## 2. Scoring against the preregistered predictions

| # | Prediction | Outcome |
|---|---|---|
| **P1** | Both models extract `CACHE_BLOCK_SIZE` from 19.3.1 | ✅ **CONFIRMED** — 9/9 runs, all 3 models |
| **P2** | ≥1 model emits cache capacity/organization | ✅ **CONFIRMED — and far stronger than predicted: 9/9 runs, all 3 models** |
| **P3** | ≥1 model emits ≥1 parameter from 2.1 | ❌ **REFUTED — 0/9. Every model returned `parameters: []`** |
| **P4** | ≥1 model invents a numeric bound | ⚠️ **PARTIAL** — no fabricated numerics; a weaker ungrounded-unit failure instead (§4.3) |
| **P5** | ≥1 model names `Zicbom`/`Zicbop`/`Zicboz` | ❌ **REFUTED — 0/9. But the prediction was mis-specified** (§4.4) |
| **P6** | ≥1 model emits a uniformity parameter | ❌ **REFUTED — 0/9. All models correctly treated it as a constraint** |
| **P7** | The models disagree on ≥1 candidate | ✅ CONFIRMED, though not where expected (§5) |

**Three of seven refuted. One partial.** Reported as-is; that is what
preregistration is for. Two of the refutations are more interesting than the
confirmations.

## 3. 🔴 The dominant failure: universal `NON_ISA` over-extraction

Every run on 19.3.1, from every model:

| Model | run 1 | run 2 | run 3 |
|---|---|---|---|
| DeepSeek-V4-Pro | `CACHE_BLOCK_SIZE`, **`CACHE_CAPACITIES`**, **`CACHE_ORGANIZATIONS`** | **`CACHE_CAPACITY`**, **`CACHE_ORGANIZATION`**, `CACHE_BLOCK_SIZE` | `CACHE_BLOCK_SIZE`, **`CACHE_CONFIGURATIONS`** |
| gemini-3.6-flash | `CACHE_BLOCK_SIZE`, **`CACHE_CAPACITY`**, **`CACHE_ORGANIZATION`** | same | **`CACHE_CAPACITY`**, **`CACHE_ORGANIZATION`**, `CACHE_BLOCK_SIZE` |
| gemini-2.5-flash | **`CACHE_CAPACITY`**, **`CACHE_ORGANIZATION`**, `CACHE_BLOCK_SIZE` | same | same |

**Precision on 19.3.1: 1/3 in 8 of 9 runs, 1/2 in the ninth. Recall of the gold
set: 1/1 in all 9.**

Bold entries have **no parameter file among UDB's 227** (verified, phase 0).
The models are not hallucinating — the snippet really does call cache capacity
and organization "implementation-specific". They are failing the *second* half
of the rule: **implementation-specific ≠ ISA-visible.**

This is exactly the gap v1 was built to expose, and it reproduces perfectly:
**9/9 runs, 3 models, 2 labs, 2 architectures.** A universal failure across
independent models is strong evidence the fault is in the *prompt*, not the
model — which is the best possible motivation for v2.

### 3.1 The models cannot agree what kind of thing it even is

Within DeepSeek's three runs, cache internals were modelled as:

- run 1 — **two arrays**, one element per cache in the system
- run 2 — **two scalars**, `integer` + `string`
- run 3 — **one merged array** of objects, `CACHE_CONFIGURATIONS`

Same model, same prompt, same input, `temperature=0`. This is not a wording
difference; it is three incompatible data models. Any downstream consumer
would need three different parsers.

The instability is itself diagnostic: **the model is unstable precisely where
the ground truth says there is no parameter at all.** Confident, stable output
on `CACHE_BLOCK_SIZE`; incoherent output on the two rejects. Run-to-run
structural disagreement may be a usable *signal* for false positives — worth
noting for Part II, out of scope to develop here.

## 4. The other failure modes

### 4.1 Markdown fences, despite an explicit instruction

v1 says *"Output valid YAML only."*

| Model | Fenced in ` ```yaml ` |
|---|---|
| gemini-2.5-flash | 6/6 |
| gemini-3.6-flash | 6/6 |
| DeepSeek-V4-Pro | **3/6 — inconsistent with itself** |

Both Gemini models ignore the instruction *consistently*; DeepSeek ignores it
*intermittently*, including differently across runs of the same snippet. A
strict `yaml.safe_load` would fail on 15 of 18 outputs.

**Lesson:** an instruction is not a guarantee. Output format needs either
schema-constrained decoding or a tolerant parser. Prompting alone did not
achieve it, and the *intermittent* case is worse than the consistent one — it
would pass a single-run smoke test and fail in production.

### 4.2 `constraints` shape is unusable as-is

Predicted in `prompts/v1/README.md` §4, and confirmed. Across runs it appeared as
a YAML list of strings, a bare string, and a double-quoted string. No two models
agreed, and DeepSeek disagreed with itself.

### 4.3 The category error — "Implementation-specific." *as a constraint*

Both Gemini models emitted, on `CACHE_CAPACITY` and `CACHE_ORGANIZATION`:

```yaml
constraints: Implementation-specific.
```

and gemini-2.5-flash did it on `CACHE_BLOCK_SIZE` too. This is a **category
error**: "implementation-specific" is the *evidence that a parameter exists*. It
is not a restriction on the value. The model has copied the trigger phrase from
the input into the output slot labelled `constraints` because it had nothing else
to put there.

Diagnostic value: it shows the model pattern-matching on the trigger word rather
than reasoning about the value domain. That is the concrete, quotable form of
"trigger-word matching is not understanding."

### 4.4 The ungrounded unit — a weaker P4 than predicted

No model fabricated a numeric bound (no invented `minimum: 4`). But:

- DeepSeek and gemini-3.6-flash both wrote *"The size of a cache block **in
  bytes**."*
- The snippet **never says bytes.** UDB does. So this is *correct but
  ungrounded* — the same class as §4.5, in a subtler form.
- gemini-2.5-flash wrote *"The size of a cache block."* — **more grounded, and
  less useful.**

That tension is real and worth stating: the most grounded output was the least
informative. It is an argument for separating *what the text says* from *what
the parameter is*, with provenance on the former — which is what v2's `excerpt`
field does.

### 4.5 P5 was mis-specified, and that is a lesson about preregistration

No run named `Zicbom`/`Zicbop`/`Zicboz`. But **v1's output schema has no field
where an extension name could go** — no `definedBy`, no source field. The
prediction was untestable by construction.

It is not evidence the models stayed grounded; it is evidence I wrote a
prediction that the experiment could not falsify. Recorded rather than quietly
dropped. v2 adds `definedBy`, making P5 genuinely testable — and given both
models named those extensions correctly and unprompted
(`reference/models.md` §2), the risk is live.

## 5. 🟢 The refutation that matters most: snippet 2.1

**All three models, all nine runs, returned `parameters: []`.**

```
deepseek-v4-pro   parameters: []
gemini-3.6-flash  ```yaml\nparameters: []\n```
gemini-2.5-flash  ```yaml\nparameters: []\n```
```

Prediction P3 said at least one model would over-extract here. **Wrong, and
decisively.** What this does and does not mean:

**What it refutes.** The premise that LLMs have a strong bias toward producing
output — that they will find *something* rather than return empty. v1 offered no
negative examples and no explicit permission to return an empty list, and all
three models still returned empty, unanimously. On this task shape that bias is
weaker than commonly assumed. That is a genuine, mildly surprising result.

**What it does not refute.** The negative control still did its job. It
established that these models can correctly decline, which is precisely what
makes the §3 result interpretable: the 9/9 over-extraction on 19.3.1 is **not**
a general eagerness to emit parameters. The same models decline cleanly when
there is no trigger word. So the 19.3.1 failure is specifically about the
**ISA-visibility test**, not about output bias.

Those two findings only make sense together. A negative control that everyone
passes is still load-bearing — it isolates the variable.

**Honest consequence for the submission.** The rejected-candidates table for 2.1
documents *our* reasoning about five candidates the models never proposed. That
is still worth including — it is the audit trail for why zero is correct — but it
must be presented as **analysis, not as a caught error**. Claiming we prevented
a false positive that no model made would be a fabrication.

## 6. Determinism: `temperature=0` is not determinism — for two models out of three

Distinct outputs across 3 runs, by SHA-256 of raw bytes:

| Model | 19.3.1 | 2.1 |
|---|:--:|:--:|
| DeepSeek-V4-Pro | **3 distinct** | **2 distinct** |
| gemini-3.6-flash | **3 distinct** | 1 — identical |
| gemini-2.5-flash | 1 — identical | 1 — identical |

DeepSeek's completion tokens on 19.3.1: **1,920 / 807 / 2,595** — a 3.2× spread
on identical input.

The blanket claim "temperature 0 is not deterministic" is **too strong**.
`gemini-2.5-flash` was byte-identical across all 6 runs. It is
**model- and provider-dependent**, and cannot be assumed either way.

This retroactively justifies N=3 on empirical rather than theoretical grounds:
**at N=1 we could not have known which models were stable**, and DeepSeek's
run-2 output (2 params, merged model) would have been recorded as "its answer"
with no indication that its other two runs disagreed.

### 6.1 The churn is mostly absorbed before it reaches the answer

Byte-instability is not the same as answer-instability. Comparing the SHA-256 of
each raw response against the **set of parameter names** extracted, over all **25
cells with N>=2** (every model, prompt version and snippet, not just the three
above):

| | cells |
|---|:--:|
| byte-identical **and** answer-identical | 5 |
| byte-different but answer-identical | **13** |
| parameter set differs | 6 |
| excluded, a run in the cell was unparseable | 1 |

So of the **19** decidable cells where the bytes move, **13 still produce exactly
the same extracted parameters**. The prose churns; the answer usually does not.

⚠️ **The definition matters, so it is stated rather than assumed.** "Answer" here
means the *set* of parameter names. Comparing ordered lists instead, so that a name
emitted twice counts as different, moves one cell from the middle row to the bottom
and gives 5 / 13 / 7. Set comparison is the right definition for this claim, since a
duplicated name inside one response is a separate defect and not answer
instability. An earlier draft of this section reported 5 / 13 / 5 on 23 cells,
which was wrong on three counts: it predated the experiment runs, the audit said to
verify it silently skipped six files, and the parameter-name helper returned an
empty list both for "no parameters" and for "response did not parse". That last one
mislabelled one cell as answer-identical when one of its runs produced no parseable
answer at all: the same conflation the `finish_reason` guard exists to prevent,
found in our own metric. The helper now raises, and that cell is excluded as
undecidable rather than assumed identical.

Two consequences. First, N=3 is justified but the thing it protects against is
narrower than "the model is unstable" — it is the **6 of 24 decidable** cells where
the extraction disagrees with itself. Second, **DeepSeek accounts for 3 of those 6**,
and it is also the model with the 3.2x completion-token spread. Volume churn and
answer churn co-occur there, which is a different regime from a model whose output
is merely reworded.

Checked by `scripts/audit_claims.py`, which now also asserts that **no results
file was skipped** while computing this.

### 6.2 Metadata churn on name-identical cells

`titoatwork` asked on [#2053](https://github.com/riscv/riscv-unified-db/issues/2053)
whether any residual movement appears on the name-identical cells from §6.1 when
something other than recall is scored. His mechanism, from Part I's
`param_extraction/scripts/analyze.py`: recall cannot move on a name-identical pair,
because `deduplicate` emits in `sorted(by_name.items())` order and the fuzzy pass
breaks ties with a strict `>`, so the matched set is fixed by the name set. But
classification accuracy reads `class` off whichever instance survived
`deduplicate`, which picks by `(conf, in_content, -_start_line)`. Two runs with an
identical name set can therefore carry a different class.

We have no `classification` field, but we have three model-authored fields that sit
in the same position. Measured across the **13** byte-different, name-identical
cells:

| Field | Cells where it moves |
|---|:--:|
| `confidence` | 1 of 13 |
| rejection `reason` codes | 8 of 13 |
| `isa_visible` class, by the committed classifier | 1 of 13 |

**The 8 needs decomposing, and doing so weakens it.** Splitting the reason-code
movement by cause:

| Cause | Cells |
|---|:--:|
| the **same candidate** receives a **different code** | **1** |
| the set of **rejected candidates itself differs** | 9 |

So the channel he predicted does exist in our data, but it is rare: **1 of 13**
cells, not 8. The rest is candidates appearing and disappearing from the reject
list, which is a different phenomenon and would not touch a classification metric
keyed on a fixed name set.

The single genuine case is `gemini-2.5-flash`, v2, 19.3.1, on the candidate
*"uniformity of cache block size"*:

```
CONSTRAINT_NOT_PARAMETER   in some runs
FIXED_BY_ARCHITECTURE      in others
```

Our ground truth says the former. This is the same instability already reported in
`v2_delta.md` §6, where that model's reason-code accuracy on this candidate was
1 of 3 and unstable within one model. Reaching it a second time by a different
route is corroboration rather than a new finding.

**The answer to his question, stated plainly:** yes, but the effect is small, it is
confined to the categorical field rather than the scalar `confidence`, and it lands
on a candidate our own analysis had already flagged as the ambiguous one. A metric
keyed on name sets is close to invariant here; a metric that reads a category off a
selected instance is not, and the exposure is roughly one cell in thirteen.

Checked by `scripts/audit_claims.py`.

## 7. Cost

| Model | Prompt tok | Completion tok | Cost |
|---|---:|---:|---|
| DeepSeek-V4-Pro | 2,217 | 6,255 | fractions of a cent |
| gemini-3.6-flash | 2,310 | 457 | free tier |
| gemini-2.5-flash | 2,310 | 444 | free tier |

DeepSeek spent **14× more completion tokens than either Gemini** for output of
comparable length — it is a heavy reasoner. Relevant only at spec scale, where
it would dominate cost.

## 8. What v2 must fix — ranked by evidence

| Priority | Intervention | Evidence |
|---|---|---|
| **1** | **The ISA-visibility test**, as an explicit gate with the cache-capacity case as a negative example | 9/9 runs, 3 models, §3 |
| **2** | **Mandatory verbatim `excerpt`**, substring-checkable | §4.3, §4.4 — no way to catch ungrounded content today |
| **3** | **Structured `constraints`**, typed not prose; and forbid the trigger phrase as a constraint value | §4.2, §4.3 |
| **4** | **A `rejected` list** with reasons, so judgement becomes visible and measurable | `prompts/v1/README.md` §3 |
| **5** | Tolerant parsing / strip fences; do not rely on "output YAML only" | §4.1, 15/18 outputs |
| **6** | Add `definedBy`, making P5 testable | §4.5 |
| **7** | Distinguish *what the text states* from *what the parameter is* | §4.4 |

Note what is **not** on this list: anything about output bias or empty results.
§5 says v1 already handles that, so adding "you may return an empty list" to v2
would be fixing a problem we do not have — and would risk the opposite failure.

## 9. Threats to validity

- **n = 2 snippets, 12 usable runs.** No percentage here generalises to the
  spec. No Jaccard coefficient is reported (`prior-art.md` §7).
- **Tier asymmetry.** DeepSeek-V4-Pro is a Pro-tier model; both Geminis are
  Flash-tier, because Pro is not on the free tier. The comparison is confounded
  by tier and is **not** a like-for-like model ranking. It is only used to show
  that a failure reproduces across independent models.
- **No Claude Opus 5** (§1.1).
- **Our own gold set is human-authored** by one person and could be wrong. The
  three falsification conditions in `ground_truth.md` §6 stand; none were met.
