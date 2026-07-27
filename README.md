# Extracting architectural parameters from RISC-V specifications

Coding challenge submission for LFX Mentorship Fall 2026, RISC-V International
([`riscv/riscv-unified-db`](https://github.com/riscv/riscv-unified-db)).

Rajveer Bishnoi ([@RAJVEER42](https://github.com/RAJVEER42))

Two snippets of the Privileged spec, 185 words. Result: **1 parameter, 11 rejected
candidates.**

```bash
./run.sh              # offline checks, no credentials, no spend
./run.sh --udb <path> # also validate against a riscv-unified-db checkout
```

The offline stages re-derive all 51 numbers in this file from the raw output in
`results/` and fail if any disagree. Nothing here is asserted without a check.

## What the two snippets are for

Snippet 19.3.1 has one trigger phrase, "implementation-specific". Snippet 2.1 has
none of the challenge's trigger words at all. Its only modals are "can", "by
convention", and a scare-quoted "Conventional". So its correct yield is zero, and
it works as a precision test rather than a recall test.

That is measured, not read: `scripts/scan_triggers.py` reports **one** trigger
phrase across both snippets.

One consequence worth stating. 19.3.1 contains "shall", which the challenge does
not list. "Shall" is a mandate and removes implementation freedom, so it marks a
constraint, not a parameter. A matcher doing stemming or synonym expansion treats
it as a hit and inverts the meaning of the sentence.

## 1. Models

| | DeepSeek-V4-Pro | Gemini 3.6 Flash | Gemini 2.5 Flash |
|---|---|---|---|
| ID | `deepseek-ai/DeepSeek-V4-Pro` | `gemini-3.6-flash` | `gemini-2.5-flash` |
| Input context | 1,048,576 | 1,048,576 | 1,048,576 |
| Weights | open, MIT | proprietary | proprietary |
| Access | HF Inference Providers | AI Studio free tier | AI Studio free tier |

Context lengths come from each model's `config.json` or API metadata. DeepSeek
reaches 1,048,576 by YaRN scaling (`factor: 16`) from a native 65,536, which is
worth stating precisely because quality at full extension is not guaranteed.

Run parameters: `temperature=0`, `max_tokens` 8,000 to 16,000 recorded per run,
N=3 per model per snippet per prompt version, `finish_reason` asserted. No
parameter-name list supplied (see §5).

Two absences. `gemini-2.5-pro` is not on the free tier; all six calls returned
`429`, and the failures are committed rather than deleted. Claude Opus 5 is
excluded because the session that produced this work had already read
`ground_truth.md`, so its output would not be an independent extraction. That is a
real limitation of the submission.

Cost, completion tokens: DeepSeek 6,255 for v1 and 17,618 for v2. Both Gemini
models ran inside the free tier. v2 costs 4.1x the prompt tokens of v1, which is
free at 185 words and dominant at 52,000 spec lines.

## 2. Results

[`parameters.yaml`](parameters.yaml) has the four requested fields plus
provenance, an ISA-visibility justification, and the rejected candidates.

[`udb/CACHE_BLOCK_SIZE.yaml`](udb/CACHE_BLOCK_SIZE.yaml) is the same parameter in
UDB's own shape, validated against the real `param_schema.json` with its `$refs`
resolved. In UDB, `type` and `constraints` are not top-level fields; they sit
inside `schema:` as JSON Schema. Emitting both shapes is deliberate, since
proposal item 4 is exporting parameters in UDB YAML form.

`CACHE_BLOCK_SIZE`, integer, constrained to a power of two and uniform across the
system. The uniformity is scoped to "the initial set of CMO extensions", which the
spec states explicitly, so it must not be encoded as a permanent invariant. No
numeric bound is given, because the passage gives none.

### The rejections carry most of the information

Eleven rejections against one parameter. The three that matter:

**Cache capacity and organization** are called implementation-specific by the
spec, so they pass the trigger test. They fail on ISA visibility: no instruction's
defined behaviour depends on them. This is corroborated rather than argued. Among
UDB's 227 parameter files there is no cache-capacity parameter, so the maintainers
drew the same line.

**Uniformity of block size** is introduced by "shall", so it is a constraint on
the parameter rather than a parameter.

**Which CSRs are implemented** is genuinely implementation-dependent, and the
passage never says so. It describes how CSR addresses encode accessibility, not
which CSRs exist. Extracting it means answering from knowledge of RISC-V instead
of from the input. This was recorded in `ground_truth.md` before any model ran,
and DeepSeek independently rejected it with the same reason code in 3 of 3 runs.

## 3. Prompt development

Git history is the evidence here. `ground_truth.md` was committed at `9d3a0cb`,
before any file in `results/` existed, and `scripts/validate.py` at `2c1badf`,
before any v2 output existed. Both orderings are checkable from commit timestamps.
The ground truth contains the adjudication of all 12 candidates, 7 falsifiable
predictions, and 3 conditions that would prove it wrong.

### v1

[`prompts/v1/`](prompts/v1/), 135 words: the trigger list verbatim, the four
requested fields, and enough scaffolding to get parseable output.

It is deliberately no better than that. Crippling v1 to claim a large improvement
would be easy and worthless, and the refinement narrative is what the challenge
actually assesses. The standard v1 is held to is what a competent engineer writes
having read the brief and nothing else, which is roughly what most submissions
will contain. Nine omissions are documented in `prompts/v1/README.md`, written
before the run.

### What v1 got wrong

Every one of 9 runs on 19.3.1, across all three models, emitted cache capacity or
organization as a parameter. Precision 1 in 3. Recall of the gold set was 9 of 9.

The models are not hallucinating. The snippet does call those things
implementation-specific. They fail the second half of the rule: being
implementation-specific is not the same as being ISA-visible. A failure that
reproduces across three models from two labs is a property of the prompt, not of
any model.

Three of seven predictions were wrong, and the refutations were more useful than
the confirmations:

* All three models returned `parameters: []` for snippet 2.1, 0 of 9. That refutes
  the common claim that LLMs are strongly biased toward producing output, since v1
  offered no negative examples and no permission to return empty.
* No model named the Zicbo\* extensions, but v1's schema had no field where an
  extension name could go. The prediction was untestable by construction, which
  was my error in designing it.
* All models correctly treated uniformity as a constraint.

The negative control still did its job. Because the same models decline cleanly on
2.1, the 19.3.1 failure is specifically about ISA visibility rather than general
eagerness to emit output. Neither result is interpretable without the other.

Two more findings. DeepSeek produced three incompatible data models for cache
internals across three runs at `temperature=0`, while staying stable on
`CACHE_BLOCK_SIZE`. Both Gemini models wrote `constraints:
Implementation-specific.`, which is a category error: the trigger phrase is
evidence a parameter exists, not a limit on its value.

### v2, and the trap in building it

[`prompts/v2/`](prompts/v2/), 862 words, 11 changes each traceable to a v1 failure.

The obvious fix would have been cheating. v1's main failure was emitting cache
capacity, so the natural move is a negative example saying cache capacity is not a
parameter. But 19.3.1 is an evaluation input, so putting its answer in the prompt
measures recitation. It is also the error Part I made by injecting the 185 gold
parameter names (§5), and having pointed that out, repeating it would be
indefensible.

So v2 states the rule as a principle and illustrates it with off-snippet examples
only: pipeline depth, branch predictor size, WARL fields with architecturally
fixed legal values, and an `ASID_WIDTH` worked example checked against the real UDB
file. A mechanical check confirms no snippet-specific term appears anywhere in the
v2 prompts. The cost is a smaller improvement than cheating would produce.

Main changes: T1/T2/T3 applied in order, with "a signal word is evidence, not
proof"; a required `isa_visible` field so the test has to be shown; a mandatory
verbatim `excerpt`, declared as mechanically checked; structured `constraints`; a
ban on signal words as constraint values; a `rejected` list with reason codes;
`defined_by` only when the passage names the extension; and "shall" and "must"
excluded from signal words.

One thing was deliberately not added: permission to return an empty list. All
three models already do so unprompted, so it would fix a problem that does not
exist and risks inducing over-declining where a real parameter is present.

### Where v2 landed

| | v1 | v2 |
|---|---|---|
| Over-extraction on 19.3.1 | 9 of 9 runs | 6 of 9 |
| Gold-set recall | 9 of 9 | 9 of 9 |
| Snippet 2.1 correctly empty | 9 of 9 | 9 of 9 |
| Markdown fenced | 15 of 18 | 6 of 18 |
| `constraints` category errors | several | none |
| `rejected` populated on 2.1 | n/a | 9 of 9 |

The whole precision improvement comes from one model. Gemini 3.6 Flash went from
3 of 3 over-extracting to 0 of 3, rejecting both candidates as `NOT_ISA_VISIBLE`.
DeepSeek and Gemini 2.5 Flash did not move. So "v2 is better than v1" is not
established as a claim about the prompt; it is confounded with model identity.
What is established is that v2 exposed reasoning v1 hid.

The clearest qualitative gain is auditability. On snippet 2.1, v1 gave
`parameters: []`, which is correct and tells you nothing. v2 gave the same verdict
with four reason-coded rejections. At spec scale that is the difference between
output a maintainer can review and output they have to trust.

## 4. Hallucinations

Not handled by instructing the model. Handled by making claims checkable.

Five failure modes turned up, and they need different treatments.

**A fabricated quotation.** Gemini 2.5 Flash wrote:

```yaml
excerpt: "The ... size of a cache block are both implementation-specific"
```

The passage reads "The capacity and organization of a cache and the size of a cache
block are both implementation-specific". Eleven words elided behind an ellipsis and
presented as verbatim.

This is the most useful single result here. The quote is semantically faithful and
the ellipsis reads as careful, so a reviewer would accept it; I would have. It also
defeats the point of provenance, since an elided quote cannot be found by search.
And it was inconsistent inside one response: the same run quoted that same sentence
correctly and in full for two other parameters. That is worse than a capability
limit, because it passes any single-run spot check. One substring test caught it.
Prediction Q7 said all 18 would pass, and it was flagged in advance as the one
worth being wrong about.

**Truncation reading as a correct empty result.** These are all reasoning models. One
that exhausts its budget returns empty content, which parses as "found no
parameters", which is the right answer for snippet 2.1. So truncation would imitate
the behaviour being measured and inflate the score through a bug. The runner treats
any `finish_reason` other than `stop` as a run failure. It caught six cases on first
use, from a quota error it was not designed for.

**Ungrounded but correct content**, like adding "in bytes" when the passage never
says bytes, and **category errors** like a trigger phrase in a constraint field. Both
are caught by `scripts/validate.py`.

**Faithful reasoning from an underspecified rule.** This one checking cannot catch,
and it found a hole in my own gate. Both models that still emitted `CACHE_CAPACITY`
under v2 justified it the same way, at high confidence, in 6 of 6 opportunities:

> Software can discover the cache capacity through the means provided by the
> execution environment.

That is not a fabrication. It quotes a real sentence of the passage, and the excerpt
passes the substring check cleanly. It is wrong because discoverability through the
execution environment is not ISA visibility: the execution environment is outside
the ISA. My prompt never said so, though `ground_truth.md` had already classified
the discovery mechanism as `NON_ISA`. The models read T3 correctly and used a gap I
left.

The passage also baits the reading. The clause calling capacity
implementation-specific and the clause promising a discovery mechanism are the same
sentence, joined by "and".

Gemini 3.6 Flash did not fall for it, rejecting both candidates in 3 of 3 runs from
the identical prompt. One underspecified gate, three models, two opposite readings.

The fix is one sentence and I have not applied it. Writing v3 in the same breath as
reporting v2 turns a measurement into a fitted result. It is recorded as the next
experiment and included in the reusable skill so it is not lost.

The transferable point: structural checks catch fabrication but not faithful
reasoning from a bad rule. For that, requiring the model to state its justification
did not prevent the error, it explained it, which is worth more.

## 5. Reading the prior art

On [issue #2053](https://github.com/riscv/riscv-unified-db/issues/2053),
`titoatwork` published measurements of the public Part I snapshot and then corrected
himself. I re-verified the load-bearing claim from the source rather than taking it
on trust, fetching both files from PR #1791's head:

```
injected list size : 185
gold set size      : 185
identical sets     : True
```

`extract.py:211` injects that list into every prompt, unconditionally, with "when a
parameter you find matches one of these known names, use the exact name". So Part
I's 69.7% is grounding recall, not discovery recall. `HANDOFF.md` §6 previously
cited it as the bar and is corrected. WARL recall of 12 of 24 likewise happens with
all 24 names already in the prompt, so that failure is identification rather than
vocabulary, which explains why adding WARL guidance made results worse.

Attribution, since it is easy to get wrong: the WARL evaluation, the ablation and
the legal-value-set refinement are `titoatwork`'s. `hjaat` opened the issue and
raised the WARL problem, crediting a Slack exchange with Allen Baum.
`ishaan-arora-1` notes that the current pipeline is internal, so PRs #1765 to #1832
are background rather than current state.

Our runs supply no name list, so our numbers are not comparable to Part I's.

The WARL refinement and our cache-capacity finding turn out to be one rule reached
from two directions. A signal of implementation freedom is necessary but not
sufficient; a parameter exists only where the implementation genuinely chooses and
that choice is ISA-visible. Cache capacity fails on visibility. A WARL field with an
architecturally fixed legal set fails on choice.

## 6. Two findings in riscv-unified-db

Both came from reading the schema the output has to fit
([`reference/udb-schema-notes.md`](reference/udb-schema-notes.md), commit
`bd775a94`). Each needs a maintainer's view before becoming a PR.

**Two implementations of "power of two" that disagree.** A cache block is a NAPOT
range, so `CACHE_BLOCK_SIZE` is always a power of two, but upstream's schema is
`minimum: 1, maximum: 2^64-1`. `schema_defs.json` already defines
`64bit_unsigned_pow2`, and `$ref`-ing it is precedented. That def cannot be adopted
as-is: its enum contains `4095` where `4096` belongs, while `z3.rb` implements the
same rule with the `x & (x-1)` trick. The two disagree on exactly those values, and
4096 is the most common cache block size in the architecture. So the fix for the
missing constraint is blocked by the defect, which is the part worth knowing.

The defect survives because the enum has no live data consumer. A repo-wide grep
finds the pow2 defs referenced in three places, all tooling, and `z3.rb` never reads
the enum. I am not claiming this breaks anything today; that needs the
value-validation path traced.

**`long_name: TODO` in 163 of 227 files**, 71.8%, including `CACHE_BLOCK_SIZE`. That
reframes the problem. The unmet need is not finding parameters, since the
maintainers found 227, but filling prose fields at scale. Usage is inconsistent
upstream, so `long_name` may be under deprecation, which makes it a question for the
SIG rather than an assumption.

## 7. Repository

| Path | Contents |
|---|---|
| `parameters.yaml`, `udb/` | the results, in both shapes |
| `ground_truth.md` | adjudication and predictions, committed before any run |
| `prompts/v1/`, `prompts/v2/` | both prompts, with design notes |
| `results/` | all 42 run records, raw and unedited, including 6 failures |
| `analysis/` | v1 failures, and the v1 to v2 delta |
| `scripts/` | trigger scan, runner, validator, schema check, claim audit |
| `.claude/skills/param-extract/` | reusable skill, proposal item 3 |
| `HANDOVER.md` | the instrument packaged for reuse at corpus scale |
| `reference/` | verified notes on the UDB schema, the models, and prior art |

## 8. Limitations

* Two snippets, one gold parameter, 36 usable runs. Every figure is a count, not a
  rate, and nothing generalises to the full spec. No Jaccard coefficient, because at
  this n it would be meaningless.
* "Precision 1 in 3 to 1 in 1" describes three runs of one model.
* v2's gain is confounded with model identity, since only one model improved.
* DeepSeek-V4-Pro is a Pro-tier model and both Gemini models are Flash-tier, because
  Gemini Pro is not on the free tier. This is not a model ranking.
* Claude Opus 5 is absent, for the reason in §1.
* The gold set is mine. DeepSeek's independent rejection of the
  `NOT_STATED_IN_TEXT` trap corroborates one judgement; the rest rests on my reading.
  Three falsification conditions were stated in advance and none were met.
* v3 is specified but unrun.
* UDB file count is 227 at `bd775a94`, while `titoatwork` reports 223 real
  parameters. The four-file difference is unresolved.
