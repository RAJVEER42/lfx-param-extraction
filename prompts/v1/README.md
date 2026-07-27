# Prompt v1 — design notes

Phase 2 of `PLAN.md`. Written after `ground_truth.md` and committed before any
run.

Files: [`system.md`](system.md) · [`user_template.md`](user_template.md)
(placeholders `{source}`, `{snippet}`)

---

## 1. What v1 is

**v1 is the challenge brief, competently followed. Nothing more.**

It contains exactly what the brief supplies — the trigger-word list verbatim,
and the four requested output fields (`name`, `description`, `type`,
`constraints`) — plus the minimum scaffolding needed to get parseable output:
a role, a one-sentence definition of "architectural parameter", and an
instruction to emit YAML only.

## 2. Why it is deliberately not better than that

**The integrity of the v1 → v2 comparison depends on v1 being a fair baseline.**

It would be easy to write a v1 that fails badly — omit the output schema, invite
prose, forbid nothing — and then claim a large improvement in v2. That
improvement would be manufactured, and a reviewer who reads both prompts would
see it immediately. The refinement narrative is the thing being assessed
(challenge deliverable 2), so faking it is the single worst available move.

So the standard v1 is held to is: **what a competent engineer would produce on a
first attempt, having read the brief and nothing else.** It is a realistic
baseline, not a punching bag.

There is a second reason this matters. v1 is, essentially, *the submission most
applicants will send*. Measuring it honestly is what makes the case that reading
the target schema and the prior art changes the result.

## 3. What v1 deliberately omits

Each omission corresponds to something we learned in phases 0–1, and each is a
planned v2 intervention. Listing them now — before the run — is what makes
phase 4's analysis a test rather than a rationalisation.

| Omitted from v1 | Learned in | Predicted consequence |
|---|---|---|
| Any test for whether the choice is **ISA-visible** | phase 0 (cache capacity has no param file) | over-extraction of `NON_ISA` things: cache capacity, organization |
| The distinction between a trigger word and a **genuine implementation choice** | `prior-art.md` §5 (WARL) | fixed conventions extracted as parameters |
| **Negative examples** | Part I used 4; v1 uses none | no signal about what *not* to extract |
| Explicit permission to return an **empty list** | phase 1 (2.1 should yield zero) | LLMs are biased toward producing output; expect spurious extraction from 2.1 |
| A mandatory **verbatim `excerpt`** field | phase 1 §1.1 | output cannot be mechanically grounded — no substring check is possible |
| An instruction **not to use outside knowledge** | phase 1 §4.2 (candidate D5) | correct-but-ungrounded output, e.g. naming `Zicbom`/`Zicbop`/`Zicboz` |
| Any **taxonomy / class labels** | Part I's 8 classes | no way to distinguish a rejected candidate from an unnoticed one |
| Warning that `shall` is a **mandate, not a trigger** | phase 1 §1 | uniformity constraint mis-read as a parameter |
| A place to record **rejected** candidates | — | rejections are invisible; we see only what survived |

The last row is worth drawing out. Under v1, a model that *considered* cache
capacity and correctly rejected it is indistinguishable from one that never
noticed it. v1 therefore cannot measure judgement at all — only output. That is
itself a finding about the brief's implied output format.

## 4. Known weaknesses we are choosing to keep

Not everything imperfect about v1 is an intentional ablation. These are real
flaws that a stricter first draft would have avoided, kept because fixing them
now would blur what v2 is testing:

- **"chooses" is doing unexamined work.** The definition says a parameter is
  something an implementation "chooses" without saying how to tell. That is
  precisely the ambiguity phase 0 resolved, and leaving it lets us see whether
  a model resolves it unaided.
- **`type` is an enumerated list of five options** but the mapping onto UDB's
  JSON-Schema `schema:` block is unstated, so `type` will be shaped by the
  model's assumptions rather than by UDB.
- **`constraints` is unstructured.** No format is specified, so output shape
  will vary between models and between runs. Expect this to complicate
  comparison, and expect v2 to have to fix it.
- **No output-length guidance**, so a reasoning model may or may not stop
  cleanly. Interacts with the `finish_reason` trap in `reference/models.md` §3.

## 5. Run configuration

Recorded so the run is reproducible. Rationale in `reference/models.md` §4.

| Setting | Value |
|---|---|
| Models | `claude-opus-5[1m]`, `deepseek-ai/DeepSeek-V4-Pro` |
| `temperature` | `0` |
| `max_tokens` | generous; `finish_reason != "stop"` is a **run failure**, not an empty result |
| Runs per (model × snippet) | **N = 3** — temperature 0 is not determinism |
| Name list supplied | **No.** Unlike Part I (`prior-art.md` §2). Our figures are therefore not comparable to theirs, and this will be stated wherever a number appears |

Exact prompt token counts will be taken from each API response's `usage` field
at run time rather than estimated here — the API's count is exact and
tokeniser-specific, and an estimate would be a claim we cannot support.

## 6. Success criterion for v1

**v1 is not expected to succeed.** Its job is to produce the specific, quotable
failures that motivate v2. A v1 that happened to be perfect would leave nothing
to demonstrate and would make the seven preregistered predictions in
`ground_truth.md` §6 all resolve as false — which is a legitimate possible
outcome, and would be reported as such.
