# Experiment 1 — results

Scored against [`exp1_prereg.md`](exp1_prereg.md), committed at `cfd3fd6` before
any file in `results/*/exp1/` existed.

12 runs, 2 models, 2 arms, N=3. All 12 completed.

**Four of six predictions refuted. The headline result is not the one the
experiment was designed to find.**

---

## 1. The numbers

| | Arm A, unedited | Arm B, clause deleted |
|---|---|---|
| `CACHE_BLOCK_SIZE` extracted, the correct answer | **6 of 6** | **2 of 6** |
| Cache capacity or organization emitted, false positive | **5 of 6** | **0 of 6** |
| Justification citing the execution environment or discovery | **6 of 6** | **0 of 6** |

One clause was deleted. Nothing else changed.

## 2. Predictions, scored

| # | Prediction | Outcome |
|---|---|---|
| X1 | `CACHE_BLOCK_SIZE` in ≥8/9 Arm B runs | ❌ **REFUTED — 2 of 6** |
| X2 | Execution-environment justification 0/9 in Arm B | ✅ confirmed, 0 of 6 |
| X3 | Capacity still emitted in ≥3/9 Arm B runs | ❌ **REFUTED — 0 of 6** |
| X4 | Model identity dominates the arm | ❌ **REFUTED — the arm dominated** |
| X5 | ≥1 run invents a substitute justification | ❌ REFUTED — none did |
| X6 | All Arm A and B excerpts pass the substring check | ❌ **REFUTED — 10/12 runs clean, 4 errors** |

## 3. The question it was built to answer: prompt gap, not model prior

X3 was the load-bearing prediction, and it is refuted decisively. Removing one
clause took capacity over-extraction from **5 of 6 to 0 of 6**, and no model
invented a substitute justification.

So the adjacent clause was **the cause, not an excuse.** The failure documented in
`v2_delta.md` §4 is a **prompt gap**, specifically our T3 wording, not a model
prior about caches. That is the better of the two outcomes: it is fixable by one
sentence, and the fix already exists in
`.claude/skills/param-extract/SKILL.md`.

This is the question `v2_delta.md` §4 and `HANDOVER.md` §4 both describe as
unanswerable with the snippet as given. A minimal-edit pair answered it for the
cost of 12 runs.

## 4. 🔴 The finding that matters more: the correct answer rested on invalid reasoning

**In all 6 Arm A runs, `CACHE_BLOCK_SIZE` was extracted with the wrong
justification. Zero of 6 cited the actual reason.**

The real reason block size is ISA-visible is that the cache-management operations
act on a cache block, so software issuing them must know the size. That is what
`ground_truth.md` §3.2 says, and it is what UDB's `definedBy: anyOf [Zicbom,
Zicbop, Zicboz]` encodes.

No run said that. Every one said some variant of:

> Software can discover the cache block size via the discovery mechanism provided
> by the execution environment.

Which is the same wrong argument the models used for cache capacity. **They were
running one undifferentiated argument across all three candidates.** It happens to
land on the right answer for block size and the wrong answer for capacity, so it
looked like discrimination and was not.

Deleting the clause proves it. With the wrong reasoning unavailable, the correct
answer went too. Four of six Arm B runs emitted nothing and explicitly rejected
the real parameter:

```
deepseek run3  REJECTED 'Cache block size'   NOT_ISA_VISIBLE
  "The passage does not describe any ISA mechanism to observe cache block size."

gpt-oss run1/2/3  REJECTED 'CACHE_BLOCK_SIZE'  NOT_ISA_VISIBLE
  "Although the block size is implementation-specific, the passage provides no
   ISA-visible way to detect it."
```

### Why this reframes the main result

`analysis/v2_delta.md` reports gold-set recall of 9 of 9 in both prompt versions
and treats that as the stable, uninteresting part of the result. It is neither.

**The 9 of 9 was right-answer-wrong-reason.** The models never had the argument
that separates block size from capacity, so recall was carried by a coincidence
that a single deleted clause removes. A precision metric would not have caught
this. A recall metric actively concealed it.

The only reason it is visible at all is that v2 made `isa_visible` a **required
field**. Without it, the output would have shown 9/9 recall with no indication the
reasoning was invalid. That is the second time this field has been diagnostic
rather than corrective, and it is the strongest argument in the submission for
requiring models to state their justification.

⚠️ **Correction to `v2_delta.md` §1**, which reads: *"Recall of the gold set: 9 of
9 in both versions. `CACHE_BLOCK_SIZE` was never missed."* True as stated, and
misleading. It should be read alongside this section.

## 4a. The reasoning predicts the answer, and this needs no new runs

Re-reading the committed v2 output settles the mechanism, from data that already
existed before this experiment.

`gemini-3.6-flash` is the one model that rejected cache capacity in 3 of 3 v2
runs. It is also the **only** model of the three that gave the correct
ISA-visibility argument:

| Model | `isa_visible` for `CACHE_BLOCK_SIZE` | Over-extracted capacity |
|---|---|---|
| **gemini-3.6-flash** | *"Cache block management instructions operate on memory aligned to and sized by the cache block size."* Cites the operations. Correct | **no, 0 of 3** |
| DeepSeek-V4-Pro | *"Software can discover the cache block size through the means provided by the execution environment."* | yes |
| gemini-2.5-flash | *"Software can discover this information through means provided by the execution environment."* | yes |

Two of the three `gemini-3.6-flash` runs cite the operations and **never mention
discovery at all**.

The correlation across the three models is exact: **the model holding the correct
argument is precisely the model producing the correct answer set.** Over-extraction
is downstream of using the wrong ISA-visibility test, not an independent defect.

That upgrades what `isa_visible` is for. It does not merely explain a false
positive after the fact, it **predicts which model will produce one**. A reviewer
can read the justification and anticipate the error before checking the answer.

> ⚠️ **Qualified by `exp2_results.md` §B.2.** This association was confirmed
> prospectively on unseen models, 15 of 15 under v2, including a within-model
> flip. But it holds because the justification is *unprompted*. When v3 required
> the correct form of justification, one model produced OPERATIONS-class
> reasoning and kept over-extracting, and the association fell to 6 of 9. A
> justification field is a good instrument only while you are not optimising
> against it.

### A falsifiable prediction, deliberately left unrun

If the mechanism above is right, then `gemini-3.6-flash` should **keep**
`CACHE_BLOCK_SIZE` in Arm B, because its reasoning does not depend on the deleted
clause. That is the opposite of what DeepSeek and `gpt-oss-120b` did, and it is a
clean test.

It is unrun because no working Gemini key was available (§6). Recording it as a
prediction rather than quietly dropping it: **`gemini-3.6-flash` extracts
`CACHE_BLOCK_SIZE` in ≥2 of 3 Arm B runs.** Anyone with a key can falsify it in
about two minutes, and a failure would mean the clause matters even to a model that
was not visibly relying on it.

## 5. A second, independent instance of the elided quote

X6 refuted: 10 of 12 runs clean, 4 errors, all E1. Two are new instances of the
fabricated-quotation failure, and one is from a **model not in the original
study**:

```
gpt-oss-120b   excerpt: "The capacity and organization of a cache ... are both implementation-specific"
deepseek       excerpt: "The capacity and organization of a cache ... are both implementation-specific"
```

The real sentence is *"The capacity and organization of a cache **and the size of a
cache block** are both implementation-specific"*.

`v2_delta.md` §3 reported one such elision, by `gemini-2.5-flash`. It now
reproduces in **two more models from two more labs, on the same sentence, with the
same eight elided words.** So it is not a quirk of one model. It looks like a
systematic behaviour on long enumerated sentences: models shorten the quote to the
part that supports their claim.

That materially strengthens the case for the substring check. One instance is an
anecdote; three across three labs is a failure mode.

Note also that DeepSeek's two errors are on **`rejected` entries**, not parameters.
The check covers those too, which is why they surfaced.

## 6. What this does not show

- **2 models, not 3.** Gemini could not run: the working API key was deleted during
  a credential rotation and the remaining key's Google Cloud project is blocked.
  So X4 could not be tested as written, and `gemini-3.6-flash`, the one model that
  resisted in v2, is absent from both arms here. Its behaviour under Arm B is
  unmeasured.
- **`gpt-oss-120b` is new to the study.** It has its own Arm A baseline here, so
  the within-experiment comparison is valid, but it is not comparable to the v2
  results.
- **12 runs, 1 gold parameter.** Counts, not rates.
- **Length is a confound.** Arm B is 76 words against 96. A minimal edit cannot
  separate the clause's content from the loss of 20 words and a sentence boundary.
  Only naturally occurring matched pairs could, and this does not claim otherwise.
- **Arm B is synthetic.** Adequate for a prompt-gap conclusion, weaker for the
  model-prior claim it rules out.
- **This does not supersede** the 60-chunk stratification `titoatwork` registered
  on issue #2053. It is the cheap within-passage version and is reported as such.

## 7. What follows

1. **The v3 fix is now motivated by evidence, not intuition.** T3 must exclude
   execution-environment discoverability *and* must supply the correct
   ISA-visibility test, because removing the wrong reason without giving the right
   one loses the true positive. That is a two-part fix, and this experiment is why.
2. **Do not report recall without reporting the justification.** On this passage,
   recall was carried by invalid reasoning in 6 of 6 runs.
3. Whoever runs the 60-chunk corpus should expect the baiting clause to matter,
   and should check whether correct extractions there are also carried by
   execution-environment reasoning.
