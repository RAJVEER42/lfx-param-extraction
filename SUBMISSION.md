# Architectural parameters from RISC-V specifications

LFX Mentorship Fall 2026, RISC-V International.
Rajveer Bishnoi, [@RAJVEER42](https://github.com/RAJVEER42)

**The expected answer was committed before any model ran.** `ground_truth.md` at
`16ea944` fixes one parameter, eleven rejected candidates and seven predictions.
The first run records land fifteen minutes later at `cf5b32b`. The validator,
`f3e4858`, predates the v2 output it judges. One `git log` checks both orderings.

**The challenge document mislabels its own input.** The cache passage is given as
Privileged Spec 19.3.1. It is in the Unprivileged manual, `src/unpriv/cmo.adoc`
lines 86 to 92 at `riscv-isa-manual` `b2e69ab`.

**All three models failed the same way in 9 of 9 runs**, and section 2 explains why.

```
git clone https://github.com/RAJVEER42/lfx-param-extraction && ./run.sh
```

No credentials, no spend. It re-derives 57 figures from the raw output in
`results/` and exits non-zero if any disagree.

---

## 1. LLMs used

| | DeepSeek-V4-Pro | Gemini 3.6 Flash | Gemini 2.5 Flash |
|---|---|---|---|
| Model ID | `deepseek-ai/DeepSeek-V4-Pro` | `gemini-3.6-flash` | `gemini-2.5-flash` |
| Context length | 1,048,576 | 1,048,576 | 1,048,576 |
| Figure read from | `config.json` `max_position_embeddings` | AI Studio `input_token_limit` | AI Studio `input_token_limit` |
| Weights | open, MIT | proprietary | proprietary |
| `max_tokens` | 8,000 | 16,000 | 16,000 |

Read from each model's own metadata on 2026-07-27, not recalled. DeepSeek reaches
its figure by YaRN scaling from a native 65,536, so quality at full extension is
not guaranteed; our prompts are about 1,500 tokens. Two labs, one open-weights and
one proprietary, so agreement between them is evidence rather than a shared prior.

`temperature=0`, N=3 per model per snippet per prompt version, no parameter-name
catalogue supplied. The experiments in section 3 add five models, all via HF
Inference Providers: `openai/gpt-oss-120b`, `zai-org/GLM-5.2`,
`moonshotai/Kimi-K2-Instruct-0905`, `inclusionAI/Ling-2.6-1T` and
`nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16`.

Claude Opus 5 is excluded because the session that produced this work had already
read the ground truth, so its output would not have been an independent extraction.
`gemini-2.5-pro` is not on the free tier and all six calls returned 429. Both sets
of failures are committed.

## 2. Prompts, and how they were refined

v1 is the challenge brief followed competently and nothing more, since a crippled
baseline would manufacture the improvement being assessed. It over-extracted in 9
of 9 runs on the cache passage, always cache capacity or cache organization, for
which `riscv-unified-db` has no parameter file. v1 could not show why: its schema
had a slot for the answer and none for the reasoning.

v2 added a three-part test applied in order, a mandatory verbatim excerpt, reason
codes on rejections, and a required `isa_visible` field naming a software-observable
consequence. DeepSeek then ran one argument across all three candidates:

```
CACHE_CAPACITY      Software can discover the cache capacity through the means provided by the execution environment.
CACHE_ORGANIZATION  Software can discover the cache organization through the means provided by the execution environment.
CACHE_BLOCK_SIZE    Software can discover the cache block size through the means provided by the execution environment.
```

The argument quotes the passage, which puts the discovery clause inside the trigger
sentence. It is wrong because the execution environment is outside the ISA, and
v2's own T3 asked about "any instruction's defined behaviour, or any
software-readable state", which reads as covering it. gemini-3.6-flash instead
wrote "Cache block management instructions operate on memory aligned to and sized
by the cache block size", and is the one model of three that stopped over-extracting.

Over-extraction fell to 6 of 9, markdown fences from 15 of 18 to 6 of 18, category
errors to zero. One model produced the entire precision gain, so "v2 is better than
v1" is not established as a claim about the prompt. What generalised is the field:
the justification tracks the answer in 15 of 15 scored v2 runs, including a
`temperature=0` flip inside one model where the reasoning changed between runs and
the answer changed with it.

Two changes were rejected. Permission to return an empty list, because all three
models already returned `parameters: []` on the second snippet in 9 of 9 runs,
refuting a prediction I had filed at high confidence. And a negative example naming
cache capacity, because that snippet is an evaluation input and putting its answer
in the prompt measures recitation.

## 3. Handling hallucinations

Four kinds appeared, each needing a different defence.

**Ungrounded text.** Every `excerpt` must be an exact substring of the passage
shown. `gemini-2.5-flash` wrote `excerpt: "The ... size of a cache block are both
implementation-specific"`, in a response that quoted the same sentence in full for
two other parameters. `DeepSeek` and `gpt-oss-120b` elide the opposite half of the
same sentence. Each keeps the part that supports the candidate it is arguing for,
so the elision is directed rather than careless. Three of the seven models tested
do this.

**Knowledge the passage does not contain.** `defined_by` is checked against the
passage. The snippet says "CMO extensions" and never names `Zicbom`, `Zicbop` or
`Zicboz`; two models name all three unprompted when asked directly, and no run
emitted them.

**A failed run that reads as a correct answer.** Empty content parses as "no
parameters", which is the correct answer for the second snippet, so a failure would
score as a success. Any run not marked `ok` is therefore excluded before parsing.
Nine were: six `gemini-2.5-pro` quota 429s and three `GLM-5.2` gateway 504s. No
committed run has ever been truncated.

**A correct answer resting on invalid reasoning.** Nothing mechanical catches this.
In all 6 unedited runs of experiment 1, `CACHE_BLOCK_SIZE` was extracted for the
wrong reason. Deleting the single clause that supplied that reason took recall from
6 of 6 to 2 of 6, so the correct answer had been resting on the same argument that
produced the false positives. v3 then removed every discovery-style justification,
and `Ling-2.6-1T` gave the correct argument while over-extracting in 3 of 3 runs.
Requiring the right justification changed what models said, not what they did, so
v3 is reported and not recommended.

Eight of the sixteen predictions registered across the two experiments were refuted.

## 4. Results

One parameter across the two snippets, and eleven rejected candidates.
[`parameters.yaml`](https://github.com/RAJVEER42/lfx-param-extraction/blob/main/parameters.yaml)
is the deliverable, abridged here:

```yaml
- name: CACHE_BLOCK_SIZE
  description: >-
    The size of a cache block. A cache block is the unit that the RISC-V
    cache-management operations act upon, so software performing those
    operations must know this value.
  type: integer
  constraints:
    power_of_two: true
    uniform_across_system: true
    uniform_scope: >-
      Applies to "the initial set of CMO extensions", which the specification
      scopes explicitly rather than stating unconditionally.
  source:       # file, spec location, trigger word, three verbatim excerpts
  isa_visible:  # the software-observable consequence
```

No numeric bound is recorded, because the passage states none. The eleven
rejections split six on the cache passage and five on the CSR passage, each with a
reason code: `NOT_ISA_VISIBLE` for cache capacity, organization and the discovery
mechanism, `CONSTRAINT_NOT_PARAMETER` for block-size uniformity and NAPOT,
`FIXED_BY_ARCHITECTURE` for the CSR encoding facts, and `NOT_STATED_IN_TEXT` for
which CSRs an implementation implements. The CSR passage contains none of the
challenge's trigger words, so its five entries record why zero is the right answer
rather than errors that were caught.

[`udb/CACHE_BLOCK_SIZE.yaml`](https://github.com/RAJVEER42/lfx-param-extraction/blob/main/udb/CACHE_BLOCK_SIZE.yaml)
gives the same parameter in `riscv-unified-db`'s shape, where `type` and
`constraints` are not top-level fields but live inside `schema:` as JSON Schema.
The parameter already exists upstream, so that file is a check on the pipeline
rather than a proposed addition.

## 5. Part I's published recall is not discovery recall

`titoatwork` reported this on issue #2053 and then corrected himself. I verified it
from source rather than inherit it. `extract.py:211` injects 185 parameter names
into every prompt, unconditionally, and that list is set-identical to the 185-name
gold set the output is scored against. Checked against both files at PR #1791's
head. So the published 69.7% measures grounding, not discovery.

No run here supplied a name list, so these numbers are not comparable to Part I's,
and this document does not compare them.

## 6. What the checks caught in my own drafts

Six numbers in earlier versions of this document were wrong: the elided-word count,
the claim that three models elided the same words, the number of models showing the
failure, the count of further models, the prediction denominator, and a description
of the nine excluded runs as truncations. All six are now assertions in
`scripts/audit_claims.py` and fail the run rather than drift.

`./run.sh --udb <checkout>` adds the UDB-side claims: the schema validation in
section 4, the 227-file parameter count, and the absence of any cache-capacity
parameter.
