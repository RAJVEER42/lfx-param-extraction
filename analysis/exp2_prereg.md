# Experiment 2 — preregistration

**Committed before any file in `results/*/exp2a/` or `results/*/exp2b/` exists.**
Check the timestamps.

Two parts, sharing one design. Both follow directly from
[`exp1_results.md`](exp1_results.md).

---

## Part A — does the justification predict the answer, prospectively?

`exp1_results.md` §4a reports an exact correlation across the three models in the
main study: the one citing the cache-management operations rejected cache capacity,
and the two citing execution-environment discoverability over-extracted.

**That is post-hoc on n=3.** Three points, examined after the fact, is a pattern
noticed rather than a claim tested. This part tests it on **four models never used
in this project**.

Models, all via HF Inference Providers, none previously run here:

- `zai-org/GLM-5.2`
- `moonshotai/Kimi-K2-Instruct-0905`
- `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16`
- `inclusionAI/Ling-2.6-1T`

Held fixed: v2 prompt byte-for-byte, snippet 19.3.1 unedited, `temperature=0`,
N=3, `finish_reason` asserted, no name catalogue.

### The prediction, stated as a rule applied per run

> **Y1.** For each run, classify the `isa_visible` justification given for
> `CACHE_BLOCK_SIZE` as either **OPERATIONS** (cites cache-management operations,
> CBO, or an instruction depending on the value) or **DISCOVERY** (cites the
> execution environment, discoverability, or querying).
>
> **OPERATIONS runs do not emit cache capacity or organization. DISCOVERY runs
> do.**

Scored as a 2×2 table over all 12 runs. The claim is the association, not the
marginal rates.

| # | Prediction | Confidence |
|---|---|---|
| **Y1** | The association holds in **≥10 of 12** runs | medium |
| Y2 | ≥1 of the 4 models is OPERATIONS-type, so the table is not degenerate | medium |
| Y3 | ≥1 of the 4 models is DISCOVERY-type | high |
| Y4 | `CACHE_BLOCK_SIZE` extracted in ≥10 of 12 runs regardless of type | medium-high |
| Y5 | ≥1 new model produces an elided-quote E1 failure, continuing the pattern now seen in 3 labs | medium |

**Y1 is the load-bearing one.** If the association fails, §4a is a coincidence of
three points and must be downgraded in `exp1_results.md`, not defended.

**Y2 matters for interpretability.** If all four models are DISCOVERY-type the
table has an empty row and the association is untestable, which is a null result
about the design rather than about the claim. It would be reported as such.

## Part B — does the two-part fix work?

`exp1_results.md` §7 argues the v3 fix must do two things, because Arm B showed
that removing the wrong reason without supplying the right one destroys the true
positive:

1. **Exclude** execution-environment discoverability from T3.
2. **Supply** the correct test, that some instruction's defined behaviour depends
   on the value.

v3 is a **minimal diff from v2**: only the T3 section changes. Everything else,
including the worked example and all other rules, is byte-identical, so the
comparison has one variable.

Run on the same 4 models as Part A plus `deepseek-ai/DeepSeek-V4-Pro` and
`openai/gpt-oss-120b`, snippet 19.3.1, N=3.

| # | Prediction | Confidence |
|---|---|---|
| **Z1** | Cache capacity or organization emitted in **≤2 of 18** v3 runs, against 5 of 6 in exp1 Arm A | medium-high |
| **Z2** | `CACHE_BLOCK_SIZE` still extracted in **≥15 of 18** runs, i.e. the fix does not repeat Arm B's collapse | medium-high |
| **Z3** | Justifications shift to OPERATIONS-type in ≥12 of 18 runs | medium |
| **Z4** | Snippet 2.1 still yields `parameters: []` in 6 of 6 v3 runs on 2 models, no regression | high |
| Z5 | ≥1 run still over-extracts, so the fix is an improvement rather than a solution | medium |

**Z2 is the one that would embarrass a naive fix.** A prompt that only forbids the
wrong reason should reproduce Arm B's failure. If Z1 holds but Z2 fails, the fix
traded false positives for false negatives and must be reported as a failure.

## Stated limits, in advance

- **Counts, not rates.** 1 gold parameter, 3 runs per cell.
- **Y1 is an association on 12 runs.** No significance test will be reported; at
  this n it would be theatre.
- **The OPERATIONS/DISCOVERY classification is mine**, applied by keyword match on
  the `isa_visible` text. The classifier is written and committed as part of this
  file's commit, before the runs, so it cannot be tuned to the outcome. Keywords:
  OPERATIONS = `cbo`, `cache management`, `cache-management`, `management
  operation`, `instruction`; DISCOVERY = `execution environment`, `discover`,
  `discovery`, `query`. A run matching both is classified OPERATIONS only if it
  does not also cite discovery, and is otherwise recorded as MIXED and excluded
  from the 2×2 with the exclusion stated.
- **Six new models are being added to a project that argued against adding
  models.** The distinction: in the main study extra models would have been
  decoration, whereas here cross-model variation *is* the unit of analysis for
  Part A. Part B needs them only for breadth.
- **v3 is not part of the v1 → v2 comparison** and its results will not be merged
  into `v2_delta.md`. It is a separate follow-up, run after v2 was reported.
- A null on either part is a result and gets equal prominence.
