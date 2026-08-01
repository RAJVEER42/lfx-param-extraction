# Coding challenge submission

**AI-assisted extraction of architectural parameters from RISC-V specifications**
LFX Mentorship Fall 2026, RISC-V International

Rajveer Bishnoi, [@RAJVEER42](https://github.com/RAJVEER42)

Everything referenced here is at
**https://github.com/RAJVEER42/lfx-param-extraction**, including every raw model
response and both prompts.

---

## 1. LLMs used

| | DeepSeek-V4-Pro | Gemini 3.6 Flash | Gemini 2.5 Flash |
|---|---|---|---|
| Model ID | `deepseek-ai/DeepSeek-V4-Pro` | `gemini-3.6-flash` | `gemini-2.5-flash` |
| Input context | 1,048,576 | 1,048,576 | 1,048,576 |
| Weights | open, MIT | proprietary | proprietary |
| Accessed via | HF Inference Providers | AI Studio free tier | AI Studio free tier |

DeepSeek's figure is `max_position_embeddings` from its `config.json`, reached by
YaRN scaling from a native 65,536; quality at full extension is not guaranteed.
Gemini publishes no `config.json`, so both Gemini figures are `input_token_limit`
from the AI Studio model listing.

Settings: `temperature=0`, N=3 per model per snippet per prompt version,
`finish_reason` asserted, no parameter-name catalogue supplied. Five further models
were used in the follow-up experiments.

`gemini-2.5-pro` is not on the free tier and all six calls returned 429. Claude
Opus 5 is excluded because the session that produced this work had already read the
ground truth, so its output would not have been an independent extraction. Both
sets of failures are committed.

## 2. Prompts, and how they were refined

Both are in `prompts/v1/` and `prompts/v2/` with design notes. v3 exists and is
discussed in §3.

Before running anything I committed the expected answer and seven predictions, so
the git timestamps show what I expected before I saw any output. v1 is the brief
followed competently and nothing more; a crippled baseline would have manufactured
the improvement being assessed.

v1 over-extracted in **9 of 9 runs across all three models**. Every model treated
cache capacity or organization as a parameter. Both are implementation-specific, so
they pass a trigger-word scan, but no instruction's behaviour depends on either,
and `riscv-unified-db` has no parameter for either among its 227 files. A failure
reproducing across three models from two labs is a property of the prompt, not the
model.

v2 adds a three-part test applied in order, a required field naming the
software-observable consequence, a mandatory verbatim excerpt, and a list of
rejected candidates with reason codes. One thing was not added: permission to
return an empty list. All three models already did so unprompted, so it would have
fixed a problem that did not exist.

The natural v2 fix was a negative example saying cache capacity is not a parameter.
That snippet is an evaluation input, so putting its answer in the prompt measures
recitation. v2 states the rule as a principle with off-snippet examples only, and
`scripts/audit_claims.py` checks that no snippet-specific term appears in either v2
prompt file.

Over-extraction fell from 9 of 9 runs to 6 of 9, markdown-fence violations from 15
of 18 to 6 of 18, and category errors to zero. The entire precision gain came from
one model of three, so "v2 is better than v1" is not established as a claim about
the prompt.

## 3. Handling hallucinations

Every claim the model makes is checked by a program.

**A fabricated quotation.** One model wrote
`excerpt: "The ... size of a cache block are both implementation-specific"`,
eliding eight words behind an ellipsis, in a response that quoted the same sentence
correctly and in full for two other parameters. A single substring test found it.
Across every committed run it appears in three models from three labs.

**Empty content that parses as a correct answer.** These are reasoning models. One
that exhausts its budget returns empty content. That parses as "found no
parameters", which is the correct answer for one of the two snippets, so the
failure would have scored as a success. The runner therefore treats any
`finish_reason` other than `stop` as a run failure. In practice it caught six
`gemini-2.5-pro` quota errors, a mode it was not designed for; no run in the
repository has ever been truncated.

**The mode checking cannot catch.** Two models defended cache capacity with
"software can discover it through the execution environment", at high confidence,
in 6 of 6 opportunities. That quotes a real sentence of the passage and passes
every mechanical check. It is wrong because the execution environment sits outside
the ISA, and my prompt never said so.

I ran an experiment to find out whether the fault was my prompt or the models,
deleting exactly one clause from the passage. It was my prompt. I wrote the
repaired version, ran it, and it removed the wrong justification while one model
kept the wrong answer. Eight of the fifteen predictions across the two experiments
were refuted.

## 4. Results

[`parameters.yaml`](https://github.com/RAJVEER42/lfx-param-extraction/blob/main/parameters.yaml)
carries `name`, `description`, `type` and `constraints`, plus verbatim provenance
and the rejected candidates.

One parameter, `CACHE_BLOCK_SIZE`, integer, constrained to a power of two and
uniform across the system, with that uniformity scoped as the specification scopes
it. Eleven rejected candidates, each with a reason code. The second snippet
contains none of the challenge's trigger words and its correct yield is zero.

[`udb/CACHE_BLOCK_SIZE.yaml`](https://github.com/RAJVEER42/lfx-param-extraction/blob/main/udb/CACHE_BLOCK_SIZE.yaml)
gives the same parameter in `riscv-unified-db`'s shape, where `type` and
`constraints` live inside `schema:` as JSON Schema. It validates against
`param_schema.json` as of commit `bd775a94`.

## 5. One thing about the challenge input

The challenge document presents the cache passage as "Privileged Spec 19.3.1". It
is not in the Privileged manual. The text is in the Unprivileged manual's CMO
chapter, `src/unpriv/cmo.adoc` lines 86 to 92 at `riscv-isa-manual` `b2e69ab`. That
sentence already carries an upstream `[#norm:cache_block_size]` tag which spans the
block size, the capacity and organization, and the discovery mechanism together, so
upstream has marked the passage as normatively interesting without separating the
parts this submission is about.

## 6. Verifying it

```
git clone https://github.com/RAJVEER42/lfx-param-extraction
cd lfx-param-extraction && ./run.sh
```

No credentials, no spend, no third-party Python packages needed for the grounding
check. With PyYAML installed it re-derives 54 numbers from the raw output in
`results/` and exits non-zero if any disagree. Passing `--udb <checkout>` adds the
schema validation in §4.

Four numbers in an earlier draft of this document were wrong: the elided-word
count, the number of models showing that failure, the count of further models, and
the description of the six caught runs as truncations. All four are now pinned by
checks in `scripts/audit_claims.py` so they cannot drift again.
