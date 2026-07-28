# Experiment 1 — preregistration

**Committed before any run in `results/*/exp1/` exists.** Check the commit
timestamp against those files. Same discipline as `ground_truth.md`.

---

## The question

`analysis/v2_delta.md` §4 reports that two of three models defended cache capacity
as a parameter with this argument, at `confidence: high`, in 6 of 6 opportunities:

> Software can discover the cache capacity through the means provided by the
> execution environment.

It quotes a real sentence of the passage and passes every mechanical check. It is
wrong, because the execution environment is outside the ISA.

What that result **cannot** tell us is *why* the models produced it, because
snippet 19.3.1 joins the two relevant clauses into one sentence with "and":

> The capacity and organization of a cache and the size of a cache block are both
> implementation-specific**, and the execution environment provides software a
> means to discover information about the caches and cache blocks in a system.**

Two competing explanations, with different consequences:

| Explanation | Meaning | Consequence |
|---|---|---|
| **Prompt gap** | The passage baits it. Our T3 wording failed to exclude execution-environment discoverability, and the adjacent clause supplied the excuse | Fixable by one sentence of prompt |
| **Model prior** | The models believe cache properties are discoverable regardless of what the passage says | Not fixable by prompting. Worse |

`v2_delta.md` §4 and `HANDOVER.md` §4 both state this is unanswerable with the
snippet as given, and hand it to anyone running a larger corpus.

## The design

A **minimal-edit pair**. Delete exactly one clause, change nothing else, run both.

- **Arm A**, `snippets/priv_19_3_1.txt` — the unedited passage, 96 words.
- **Arm B**, `snippets/priv_19_3_1_nodiscovery.txt` — identical except the clause
  *", and the execution environment provides software a means to discover
  information about the caches and cache blocks in a system"* is removed and the
  sentence closed with a full stop. 76 words.

Everything else is held fixed: same v2 prompt byte-for-byte, same three models,
same `temperature=0`, same N=3, same `finish_reason` guard, and **the same
`Source:` label**, so the label is not the variable that differs.

Verified before running: the strings `execution environment`, `discover`, and the
deleted clause appear nowhere in what Arm B sends, and `implementation-specific`,
`power-of-two`, `NAPOT`, `shall be uniform` and `CMO` are all preserved. The
`CACHE_BLOCK_SIZE` parameter, its constraints, and the correct answer are
unchanged between arms.

⚠️ **Arm B is not specification text.** It is a derived artifact for this
experiment and its file header says so. It must never be quoted as spec.

## Predictions, committed in advance

| # | Prediction | Confidence |
|---|---|---|
| **X1** | `CACHE_BLOCK_SIZE` extracted in ≥8/9 Arm B runs. Removing the clause must not break the real answer | high |
| **X2** | The execution-environment justification appears in **0 of 9** Arm B runs, since the words it quotes are gone | high |
| **X3** | Cache capacity is still emitted as a parameter in ≥3/9 Arm B runs, i.e. over-extraction **persists** with a *different* justification | medium |
| **X4** | DeepSeek and gemini-2.5-flash still over-extract in Arm B; gemini-3.6-flash still does not. Model identity dominates | medium-high |
| **X5** | ≥1 Arm B run invents a **substitute** justification for capacity that is not grounded in the passage, e.g. asserting software discoverability with no supporting clause | medium |
| **X6** | All Arm B excerpts pass the substring check | medium |

## How the result will be read

The prediction that carries the finding is **X3**, not X2. X2 is nearly
tautological: delete the words and the quote of those words disappears.

- **X3 false**, capacity over-extraction drops to near zero → the adjacent clause
  was doing the work. **Prompt gap.** Our T3 wording is the fault and the
  one-sentence fix should work.
- **X3 true**, capacity still over-extracted with a substitute justification →
  the clause was an *excuse*, not a cause. **Model prior.** Prompt repair will
  not fix it, and the finding is more serious than `v2_delta.md` claims.
- **X3 true and X5 true** is the strongest version: the model wanted the
  conclusion and reached for whatever support was available.

## Stated limits, in advance

- **n is tiny.** 9 runs per arm, one gold parameter. Results are counts, not
  rates, and nothing generalises to the spec.
- **Confounded by length.** Arm B is 20 words shorter. A change could in principle
  come from length or from the missing sentence boundary rather than from the
  clause's content. A minimal edit cannot fully separate these; only naturally
  occurring matched pairs could, and I am not claiming otherwise.
- **Arm B is synthetic.** For a *prompt gap* claim that is fine. For a *model
  prior* claim it is weaker evidence than real text would be, because a model may
  behave differently on text that reads as edited.
- **This does not supersede** the 60-chunk stratification registered by
  `titoatwork` on issue #2053. It is the cheap within-passage version, and it is
  reported as such.
- A **null result is a result** and will be reported with the same prominence as a
  positive one.
