# Extracting architectural parameters from RISC-V specifications

LFX Mentorship Fall 2026 coding challenge. RISC-V International,
[`riscv/riscv-unified-db`](https://github.com/riscv/riscv-unified-db).

Rajveer Bishnoi, [@RAJVEER42](https://github.com/RAJVEER42)

**Input:** 2 spec snippets, 185 words.
**Output:** 1 parameter, 11 rejected candidates.
**Runs:** 3 models from 2 labs, 36 usable runs, 2 prompt versions.

---

## The six things worth your time

**1. Snippet 2.1 is a precision test, and the right answer is zero.**
It contains none of the challenge's trigger words. Counted, not read:
`scripts/scan_triggers.py` finds exactly **one** trigger phrase across both
snippets. Anything extracted from 2.1 is a false positive.

**2. All 3 models failed the same way, in 9 of 9 runs.**
Every model called cache capacity a parameter. It is implementation-specific, so
it passes a trigger scan, but no instruction's behaviour depends on it. UDB has no
cache-capacity parameter among its 227 files, so the maintainers already drew this
line. A failure reproducing across 3 models from 2 labs is a property of the
prompt, not the model.

**3. A program caught a fabricated quotation I would have accepted.**
One model wrote `excerpt: "The ... size of a cache block are both
implementation-specific"`, eliding 11 words behind an ellipsis and presenting it as
verbatim. One substring test found it. That is the answer to "how did you deal with
hallucinations": not by instructing the model, by making claims checkable.

**4. The models found a hole in my own rule.**
Two of them defended cache capacity with "software can discover it through the
execution environment", at high confidence, in 6 of 6 chances. That quotes a real
sentence of the passage and passes every mechanical check. It is wrong because the
execution environment sits outside the ISA, and my prompt never said so. I have not
patched it, because writing v3 while reporting v2 turns a measurement into a fitted
result.

**5. I found two real defects in `riscv-unified-db` and filed neither.**
Both are now fixed upstream, by someone else, and on one of them I was not even
first. §7 is the write-up, kept because what happened to those findings is more
useful than the findings were.

**6. Two preregistered experiments, and my own fix did not work.**
[`analysis/exp1_results.md`](analysis/exp1_results.md) deletes one clause from the
passage and shows the failure in 4 is a prompt gap, not a model prior. It also
shows the correct answer was reached by invalid reasoning in 6 of 6 runs, so the
9-of-9 recall reported below was carried by a coincidence.
[`analysis/exp2_results.md`](analysis/exp2_results.md) confirms the mechanism on
four unseen models, then finds that the repaired prompt removed the wrong
justification while one model kept the wrong answer. Eight predictions were
refuted across the two.

## The three requested deliverables

| Asked for | Where |
|---|---|
| **1.** LLM details: name, version, context length | [§1](#1-models) |
| **2.** Prompts, how refined, hallucination handling | [§3](#3-prompt-development), [§4](#4-hallucinations) |
| **3.** Results as YAML: name, description, type, constraints | [`parameters.yaml`](parameters.yaml), plus [`udb/CACHE_BLOCK_SIZE.yaml`](udb/CACHE_BLOCK_SIZE.yaml) in UDB's shape |

## Check it without trusting me

```bash
./run.sh                 # no credentials, no spend, seconds
./run.sh --udb <path>    # also checks the UDB claims
```

That re-derives **all 51 numbers in this file** from the raw output in `results/`
and fails if any disagree. It also re-runs the validator over committed output and
confirms every quotation in `parameters.yaml` is a real substring of its source.

### What was done, and in what order

The order is the evidence. Two commits had to land before the work they judge, and
both are checkable from git timestamps.

Solid arrows are data flow. Dotted arrows are **commit order only**: the green boxes
never fed into the runs, they simply existed first, which is the whole point. Both
prompts take the snippets as input; that edge is left out to keep the shape legible.

```mermaid
flowchart TD
    S["2 snippets · 185 words"] --> T["scan_triggers.py<br/>1 trigger phrase<br/>snippet 2.1 has none"]
    T --> G["<b>ground_truth.md</b> · 16ea944<br/>1 parameter, 11 rejections<br/>7 predictions"]
    P1["v1 prompt · 135 words<br/>the brief, followed"] --> R1["v1 runs<br/>3 models x N=3"]
    G -. "existed first" .-> R1
    R1 --> A1["9 of 9 over-extract<br/>3 of 7 predictions refuted"]
    A1 --> P2["v2 prompt · 862 words<br/>11 changes<br/>no leaked answers"]
    A1 --> V["<b>validate.py</b> · f3e4858<br/>8 checks, E1 = substring"]
    P2 --> R2["v2 runs<br/>3 models x N=3"]
    V -. "existed first" .-> R2
    R2 --> A2["17 of 18 pass<br/>1 fabricated quote caught"]
    A2 --> D["parameters.yaml<br/>udb/CACHE_BLOCK_SIZE.yaml"]

    style G fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#000
    style V fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#000
    style A2 fill:#fef9c3,stroke:#ca8a04,color:#000
```

**Gate 1.** `ground_truth.md` was committed before anything in `results/` existed. So
the adjudication and the 7 predictions could not have been shaped by model output.
The models were measured, not believed.

**Gate 2.** `validate.py` was committed before any v2 output existed. So its checks
could not have been tuned to flatter the results they went on to judge.

---

## 1. Models

| | DeepSeek-V4-Pro | Gemini 3.6 Flash | Gemini 2.5 Flash |
|---|---|---|---|
| Model ID | `deepseek-ai/DeepSeek-V4-Pro` | `gemini-3.6-flash` | `gemini-2.5-flash` |
| Input context | 1,048,576 | 1,048,576 | 1,048,576 |
| Weights | open, MIT | proprietary | proprietary |
| Via | HF Inference Providers | AI Studio free tier | AI Studio free tier |

Context lengths come from each model's `config.json` or API metadata, not from
memory. DeepSeek reaches 1,048,576 by YaRN scaling (`factor: 16`) from a native
65,536, worth stating precisely because quality at full extension is not
guaranteed. All three are reasoning models, which matters for §4.

`temperature=0`, `max_tokens` recorded per run, **N=3** per model per snippet per
version, `finish_reason` asserted. **No parameter-name list supplied**, unlike
Part I (§5).

**Two models are missing on purpose.** `gemini-2.5-pro` is not on the free tier;
all 6 calls returned `429`, and those failures are committed rather than deleted.
**Claude Opus 5 is excluded** because the session that produced this work had
already read `ground_truth.md`, so its output would not be an independent
extraction. A real limitation, not a footnote.

Completion tokens: DeepSeek 6,255 for v1 and 17,618 for v2; both Gemini models
stayed inside the free tier. v2 costs 4.1x the prompt tokens of v1, free at 185
words and dominant at 52,000 spec lines.

## 2. Results

**`CACHE_BLOCK_SIZE`**, integer, a power of two, uniform across the system.

The uniformity is scoped: the spec says "in the initial set of CMO extensions",
reserving the right to relax it, so it must not become a permanent invariant. No
numeric bound is given because the passage gives none.

Two shapes, because they differ in substance. [`parameters.yaml`](parameters.yaml)
uses the challenge's four fields plus verbatim provenance, an ISA-visibility
justification, and the rejections. [`udb/CACHE_BLOCK_SIZE.yaml`](udb/CACHE_BLOCK_SIZE.yaml)
uses UDB's shape, where `type` and `constraints` are **not** top-level fields but
live inside `schema:` as JSON Schema. Validated against the real
`param_schema.json` with `$refs` resolved.

**The 11 rejections carry most of the information.** Three matter most:

| Rejected | Reason | Why |
|---|---|---|
| Cache capacity, cache organization | `NOT_ISA_VISIBLE` | Implementation-specific, so passes a trigger test, but not observable through the ISA. UDB has no parameter for either |
| Uniformity of block size | `CONSTRAINT_NOT_PARAMETER` | "Shall" is a mandate. It constrains the parameter instead of being one |
| Which CSRs are implemented | `NOT_STATED_IN_TEXT` | Genuinely implementation-dependent, but the passage never says it. Extracting it means answering from RISC-V knowledge, not the input |

That last one was recorded in `ground_truth.md` before any run, and DeepSeek
independently rejected it with the same code in 3 of 3 runs.

## 3. Prompt development

Full detail in [`analysis/v1_failures.md`](analysis/v1_failures.md) and
[`analysis/v2_delta.md`](analysis/v2_delta.md).

**v1** ([`prompts/v1/`](prompts/v1/), 135 words) is the brief followed competently:
the trigger list verbatim, the four fields, enough structure to parse. Deliberately
no better. Crippling v1 to claim a big improvement would be easy and worthless, and
the refinement story is what this deliverable assesses. Its nine omissions are
listed in `prompts/v1/README.md`, written before the run.

**v1 failed** in 9 of 9 runs on 19.3.1, precision 1 in 3, with gold-set recall 9 of
9. Finding the real parameter was never the hard part. Three of seven predictions
were wrong, and the refutations were the useful part. All 3 models returned
`parameters: []` for snippet 2.1, 0 of 9, which refutes the common claim that LLMs
are strongly biased toward producing output. One prediction was untestable by
construction, which was my design error.

**v2** ([`prompts/v2/`](prompts/v2/), 862 words) makes 11 changes, each traceable to
a v1 failure: a three-part test applied in order, a required `isa_visible` field so
the test must be shown, a mandatory verbatim `excerpt` declared as mechanically
checked, structured `constraints`, a ban on signal words as constraint values, a
`rejected` list with reason codes, and "shall" excluded from signal words.

**The obvious fix would have been cheating.** The natural move is a negative example
saying cache capacity is not a parameter. But 19.3.1 is an evaluation input, so
putting its answer in the prompt measures recitation. It is also the error Part I
made by injecting the 185 gold names (§5), and having pointed that out, repeating it
would be indefensible. So v2 states the rule as a principle with off-snippet
examples only, and a mechanical check confirms no snippet-specific term appears in
the v2 prompts.

Deliberately **not** added: permission to return an empty list. All three models
already did so unprompted.

| | v1 | v2 |
|---|---|---|
| Over-extraction on 19.3.1 | 9 of 9 | **6 of 9** |
| Gold-set recall | 9 of 9 | 9 of 9 |
| Snippet 2.1 correctly empty | 9 of 9 | 9 of 9 |
| Markdown fences | 15 of 18 | **6 of 18** |
| `constraints` category errors | several | **none** |
| `rejected` populated on 2.1 | n/a | **9 of 9** |

**The whole precision gain comes from one model.** Gemini 3.6 Flash went 3 of 3 to
0 of 3; the other two did not move. So "v2 is better than v1" is **not** established
as a claim about the prompt. It is confounded with model identity. What is
established is that v2 exposed reasoning v1 hid: on 2.1, v1 gave a bare
`parameters: []`, while v2 gave the same verdict with four reason-coded rejections.

## 4. Hallucinations

Five modes, needing different treatments, and one that checking cannot fix.

| Mode | Seen | Caught by |
|---|---|---|
| Fabricated quotation | `"The ... size of a cache block"` | substring check, E1 |
| Ungrounded but true | "in bytes", absent from the passage | validator, E4 |
| Category error | `constraints: Implementation-specific.` | validator, E2 |
| Truncation as a false empty | empty content read as "no parameters" | `finish_reason` guard |
| **Faithful reasoning from a bad rule** | the execution-environment argument | **nothing mechanical** |

**Why the fabricated quote matters.** A reviewer would accept it: the quote is
semantically faithful and an ellipsis reads as careful. It defeats provenance,
because an elided quote cannot be found by searching the source. And it was
inconsistent inside one response, which quoted that same sentence correctly and in
full for two other parameters. That is worse than a capability limit, because it
passes any single-run spot check.

**Truncation is the subtle one.** A reasoning model that exhausts its budget returns
empty content, which parses as "found no parameters". For snippet 2.1 that is the
correct answer, so truncation imitates the behaviour being measured and would
inflate the score through a bug. The runner treats any `finish_reason` other than
`stop` as a run failure. It caught 6 cases on first use, from a quota error it was
not designed for.

**The mode checking cannot fix** is item 4 above. Two models justified cache
capacity with a real sentence of the passage, and every mechanical check passed.
Gemini 3.6 Flash rejected the same candidate in 3 of 3 runs from the identical
prompt: one underspecified rule, three models, two opposite readings. Structural
checks catch fabrication but not faithful reasoning from a bad rule. Requiring the
model to state its justification did not prevent that error, it explained it, which
is worth more.

## 5. Reading Part I honestly

On [issue #2053](https://github.com/riscv/riscv-unified-db/issues/2053),
`titoatwork` published measurements of the public Part I snapshot and then corrected
himself. I re-verified the load-bearing claim from source rather than inherit it,
fetching both files from PR #1791's head:

```
injected list size : 185
gold set size      : 185
identical sets     : True
```

`extract.py:211` injects that list into every prompt, unconditionally, with "when a
parameter you find matches one of these known names, use the exact name".

**So Part I's 69.7% is grounding recall, not discovery recall.** WARL recall of 12
of 24 happens with all 24 names already in the prompt, so that failure is
identification rather than vocabulary, which explains why adding WARL guidance made
results worse. **Our runs supply no name list, so our numbers are not comparable to
Part I's.**

Attribution, because it is easy to get wrong: the WARL evaluation, the ablation and
the legal-value-set refinement are `titoatwork`'s. `hjaat` opened the issue and
raised the WARL problem, crediting a Slack exchange with Allen Baum.
`ishaan-arora-1` notes the current pipeline is internal, so PRs #1765 to #1832 are
background rather than current state.

That refinement and our cache-capacity finding are one rule reached from two
directions:

> A signal of implementation freedom is necessary but not sufficient. A parameter
> exists only where the implementation genuinely chooses, and that choice is
> ISA-visible.

Cache capacity fails on visibility. A WARL field with an architecturally fixed legal
set fails on choice.

## 6. The challenge document mislabels one snippet

The brief presents the cache passage as "Privileged Spec 19.3.1". It is not in the
Privileged manual. The text is in the **Unprivileged** manual's CMO chapter,
`src/unpriv/cmo.adoc` lines 86-92 at `riscv-isa-manual` `b2e69ab`, the revision
`riscv-unified-db` pins.

Worth stating because the label was inherited rather than checked, here and
presumably elsewhere. The sentence also already carries an upstream
`[#norm:cache_block_size]` tag, and that tag spans three clauses at once: the block
size, the capacity and organization, and the discovery mechanism. So upstream has
already marked this passage as normatively interesting without separating the parts,
which is exactly the separation §2 and the experiments are about.

## 7. Two findings in riscv-unified-db, and what happened to them

Both came from reading the schema the output has to fit, recorded in
[`reference/udb-schema-notes.md`](reference/udb-schema-notes.md) at commit
`fee7302`, 2026-07-27. **Both are now fixed upstream, and neither fix is mine.**
The section is kept because what happened to them is more useful than the findings
were.

**The finding.** `CACHE_BLOCK_SIZE` was `minimum: 1, maximum: 2^64-1`, which admits
3, 5 and 100, while the specification says a cache block is a naturally aligned
power-of-two range. `schema_defs.json` already defined `64bit_unsigned_pow2` for
exactly this, but its enum contained `4095` where `4096` belongs, in both the 32-
and 64-bit lists, so adopting it would have rejected the most likely legal value in
the architecture. The fix was blocked by the defect.

**What happened.** `titoatwork` filed the enum typo as
[#2137](https://github.com/riscv/riscv-unified-db/issues/2137) at 11:32 UTC on 27
July. I recorded the same thing in this repository at 16:32 UTC the same day, five
hours later, having never checked whether it was already reported. He then filed
[#2188](https://github.com/riscv/riscv-unified-db/issues/2188) and merged
[#2189](https://github.com/riscv/riscv-unified-db/pull/2189) on 29 July, which
constrains `CACHE_BLOCK_SIZE` to a power-of-two enum. He also found a third blocker
I had not: `Idl::Type.from_json_schema_scalar_type` resolves only `uint32` and
`uint64` and raises on anything else, so no parameter can reference those `$defs` at
all, filed as [#2199](https://github.com/riscv/riscv-unified-db/issues/2199).
Separately `Hiteshsai007` filed the dead zero-disjunct in `z3.rb` as
[#2176](https://github.com/riscv/riscv-unified-db/issues/2176), which I had noted
as a minor aside and not reported either.

**The lesson, which is the part worth keeping.** I found two real defects and filed
neither. I held them for a SIG discussion that had not happened yet, and treated
"still broken in `main`" as "nobody is working on it". Those are different things.
On one of them I was not even first, and one search would have told me. Unfixed code
and unclaimed work are not the same, and the cost of assuming otherwise is that
somebody else does the work and is right to.

What survives is narrower and I would rather state it than dress it up: reading the
target schema before generating output found real problems, and that part of the
method worked. Acting on them did not.

**Still open, and still mine to check:** `long_name` was a placeholder in 163 of 227
parameter files at `bd775a94`. At `4eae422` it is 159 of 227, and
`CACHE_BLOCK_SIZE`'s is now filled in. The underlying observation stands, that the
repository's unmet need is prose at scale rather than parameter discovery, but the
number moves and any figure quoted from it needs a commit attached.

## 8. How this maps to the Part II proposal

| Item | What is here |
|---|---|
| **1.** Continue finding parameters with LLMs | The extraction, plus what makes it measurable: ground truth committed first, a negative control, no name list |
| **2.** Extend the classification scheme | A second axis in `parameters.yaml`. Reason codes say why something is not a parameter; `udb_absence` says why UDB lacks it, as `real_gap`, `udb_derives`, or `out_of_scope`, all checkable against the repo. `IALIGN` is the `udb_derives` case, verified at `globals.isa:797` |
| **3.** Agents and skills for reproducible runs | [`.claude/skills/param-extract/`](.claude/skills/param-extract/), plus `run.sh` and four scripts. [`HANDOVER.md`](HANDOVER.md) packages the instrument for someone else to run at corpus scale |
| **4.** Export in UDB YAML format | [`udb/CACHE_BLOCK_SIZE.yaml`](udb/CACHE_BLOCK_SIZE.yaml), schema-validated |
| **5.** Open a PR for reviewed parameter files | The two §7 findings are PR-ready, held for SIG discussion first |

## 9. Limitations

* **2 snippets, 1 gold parameter, 36 usable runs.** Every figure is a count, not a
  rate. Nothing generalises to the full spec, and no Jaccard coefficient is
  reported because at this n it would be meaningless.
* "Precision 1 in 3 to 1 in 1" describes 3 runs of 1 model.
* **v2's gain is confounded with model identity**, since only 1 of 3 improved.
* **Tier-confounded:** DeepSeek-V4-Pro is Pro-tier, both Gemini models Flash-tier,
  because Gemini Pro is not free. This is not a model ranking.
* **Claude Opus 5 absent**, for the reason in §1.
* **The gold set is mine.** DeepSeek's independent rejection of the
  `NOT_STATED_IN_TEXT` trap corroborates one judgement; the rest rests on my
  reading. Three falsification conditions were set in advance and none were met.
* **v3 was run** (`analysis/exp2_results.md`) and is **not** recommended: it removed the
  wrong justification while one model kept the wrong answer, and it introduced a new
  failure on the negative control. Reported rather than shipped.
* 227 parameter files at `bd775a94` versus `titoatwork`'s 223 real parameters. The
  4-file difference is unresolved.

## 10. Repository

| Path | Contents |
|---|---|
| `parameters.yaml`, `udb/` | The results, both shapes |
| `ground_truth.md` | Adjudication and 7 predictions, committed before any run |
| `prompts/v1/`, `prompts/v2/` | Both prompts, each with design notes |
| `results/` | All 42 run records, raw and unedited, including 6 failures |
| `analysis/` | v1 failures, v1 to v2 delta, and two preregistered experiments with their results |
| `scripts/` | Trigger scan, runner, validator, UDB schema check, claim audit |
| `.claude/skills/param-extract/` | Reusable skill |
| `HANDOVER.md` | The instrument, packaged for reuse at corpus scale |
| `reference/` | Verified notes on the UDB schema, the models, and prior art |
