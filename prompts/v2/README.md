# Prompt v2 — design notes

Phase 5 of `PLAN.md`. Every change below is traceable to a specific v1 failure
in `analysis/v1_failures.md`. Nothing was changed on intuition.

Files: [`system.md`](system.md) · [`user_template.md`](user_template.md)

---

## 1. ⚠️ Contamination control — read this first

**The strongest available negative example is deliberately not used.**

v1's dominant failure was emitting cache capacity and cache organization as
parameters, in 9 of 9 runs. The obvious v2 fix is a negative example saying
*"cache capacity is not an architectural parameter."*

**That would have been cheating.** Snippet 19.3.1 is an evaluation input. Putting
its answer in the prompt guarantees an improvement that measures nothing — the
model would be reciting, not reasoning. Any v1→v2 delta obtained that way would
be worthless, and a reviewer comparing the two prompts would see it at once.

This is precisely the error Part I made by injecting the 185 gold parameter
names into every prompt (`reference/prior-art.md` §2). Having criticised it,
repeating it would be indefensible.

So v2 encodes the ISA-visibility test as a **general principle** and illustrates
it with **off-snippet** examples only:

| Used in v2 | Why it is safe |
|---|---|
| pipeline depth, branch predictor size | unambiguously microarchitectural; **absent from both snippets** |
| WARL fields with an architecturally fixed legal-value set | neither snippet mentions WARL |
| `ASID_WIDTH` worked example | real UDB parameter (verified); concerns address translation, unrelated to caches or CSR address mapping |

The worked example is **positive-only and off-topic by construction**. It never
tells the model that cache block size is a parameter, nor that cache capacity is
not. The model must derive both from T1–T3.

**Cost of this discipline:** v2 will probably fix the cache-capacity failure less
completely than a leaked example would. That is the correct trade. A smaller
honest delta is worth more than a large fake one.

## 2. What changed, and the evidence for each change

| # | Change | v1 failure it targets | Evidence |
|---|---|---|---|
| 1 | **T1/T2/T3 gate**, applied in order, with "a signal word is evidence, not proof" | `NON_ISA` over-extraction | 9/9 runs, `v1_failures.md` §3 |
| 2 | **`isa_visible` is a required field** — must name a concrete observable consequence, or the candidate is rejected | same | forces T3 to be *shown*, not just asserted |
| 3 | **Mandatory verbatim `excerpt`**, declared as mechanically substring-checked | ungrounded content | §4.3, §4.4 |
| 4 | **Structured `constraints`** (`minimum`/`maximum`/`power_of_two`/`enum`/`note`) | unparseable prose constraints | §4.2 — three shapes across runs |
| 5 | **Explicit ban: a signal word is never a constraint value** | `constraints: Implementation-specific.` | §4.3, the category error |
| 6 | **`rejected` list with 4 reason codes** | judgement invisible in v1 | `prompts/v1/README.md` §3 |
| 7 | **`defined_by` only if the passage names the extension** | P5 untestable in v1 | §4.5 |
| 8 | **"shall"/"must" explicitly excluded** from signal words, called out as constraint markers | `shall` is not `should` | `ground_truth.md` §1 |
| 9 | **`description` must not add units the passage omits** | "in bytes" ungrounded | §4.4 |
| 10 | **"no markdown code fence"** stated explicitly | 15/18 outputs fenced | §4.1 |
| 11 | **`long_name` added** | 163/227 UDB files say `long_name: TODO` | `reference/udb-schema-notes.md` §5 |

## 3. What was deliberately *not* changed

**No permission to return an empty list.** The obvious move after reading about
LLM output bias — and `v1_failures.md` §5 shows we do not need it. All three
models returned `parameters: []` on snippet 2.1 in 9/9 runs with no such
instruction. Adding it would fix a problem we do not have, and risks inducing
the opposite failure: a model that declines too readily on 19.3.1, where there
*is* a real parameter.

This is worth stating because it is the discipline the exercise is actually
testing. The temptation is to add every plausible instruction. v2 adds only what
the evidence demands.

**No taxonomy class labels.** Part I used `NORM_DIRECT` / `NORM_CSR_WARL` /
`NORM_CSR_RW` / `SW_RULE` / `NON_ISA`. We use four *reason codes* on rejections
instead, because with n=2 snippets a full 8-class taxonomy could not be
evaluated — most classes would have zero instances. Rejection reasons are what
these snippets can actually exercise.

**No chain-of-thought instruction.** All three models are reasoning models and
already produce internal reasoning. Asking for visible step-by-step output would
add tokens without adding measurable signal.

## 4. Known risks in v2

Stated in advance so §5's outcomes are not rationalised afterwards.

- **v2 is 6.4× longer than v1** (135 → 862 words). Longer prompts can degrade
  instruction-following. `prior-art.md` §4 is the cautionary case: adding
  structural WARL guidance *reduced* gold WARL recall from 12.5% to 8.3%. **More
  guidance is not monotonically better, and we have direct evidence of that.**
- **`isa_visible` may induce confabulation.** A required field is a field the
  model will fill. It may invent a plausible observable consequence for a
  candidate that has none — converting a clean false positive into a
  well-argued one. Watch for this specifically.
- **`rejected` may induce over-rejection**, moving the real parameter into the
  reject list to look rigorous.
- **The four reason codes may be misapplied**, e.g. `FIXED_BY_ARCHITECTURE`
  used where `NOT_ISA_VISIBLE` is correct. Category accuracy is measurable
  separately from accept/reject accuracy.

## 5. 🔒 Preregistered predictions for v2

Committed before any v2 run, same discipline as `ground_truth.md` §6.

| # | Prediction | Confidence |
|---|---|---|
| **Q1** | `CACHE_BLOCK_SIZE` still extracted from 19.3.1 in ≥8/9 runs | high |
| **Q2** | Cache capacity/organization appear as **parameters** in **fewer** runs than v1's 9/9 | medium-high |
| **Q3** | Cache capacity/organization appear in `rejected` with `NOT_ISA_VISIBLE` in ≥5/9 runs | medium |
| **Q4** | Snippet 2.1 still yields `parameters: []` in 9/9 runs — **no regression** | high |
| **Q5** | ≥1 model now populates `rejected` for 2.1, making its judgement visible where v1 showed nothing | medium-high |
| **Q6** | `defined_by` is `null` for cache block size in ≥7/9 runs, since the passage says "CMO" but never names Zicbom/Zicbop/Zicboz | medium |
| **Q7** | 100% of emitted `excerpt` values pass the substring check | medium — this is the one worth being wrong about |
| **Q8** | ≥1 model writes a confabulated `isa_visible` for a candidate that has none (§4) | medium |
| **Q9** | Fencing drops below v1's 15/18 | low-medium |

**Q7 is the load-bearing one.** If excerpts fail the substring check, the entire
grounding strategy needs rethinking — and that would be the most useful finding
in the submission, not the least.

**A regression on Q4 would be a real cost**, and would be reported as such. It
is the specific way v2 could be worse than v1 overall.

## 6. Scoring

Unchanged from v1 so the comparison is like-for-like: per-candidate
adjudication, no aggregate percentages, no Jaccard, no name list supplied.

Same models (`DeepSeek-V4-Pro`, `gemini-3.6-flash`, `gemini-2.5-flash`), same
`temperature=0`, same N=3, same `finish_reason` guard. `gemini-2.5-pro` remains
unavailable on the free tier and Claude Opus 5 remains excluded for
contamination reasons (`v1_failures.md` §1.1).
