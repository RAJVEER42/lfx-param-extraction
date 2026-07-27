# Handover — the instrument, for reuse at corpus scale

Written to discharge an offer made publicly on
[riscv-unified-db#2053](https://github.com/riscv/riscv-unified-db/issues/2053):
to hand over the prompt, the **exact** T1/T2/T3 gate wording, and the substring
validator, so a larger run uses *the same instrument* rather than a
reimplementation.

Everything here is MIT-usable, self-contained, and needs nothing from this repo's
directory layout.

---

## ⚠️ Read this first: use the gate wording verbatim

**To reproduce the capacity finding you need the *flawed* T3 wording, not a
corrected one.**

The result being reproduced is that models defeat T3 by arguing *"software can
discover the cache capacity through the means provided by the execution
environment"* — grounded in the passage, high confidence, and wrong. That
happens **because** the shipped T3 does not say that execution-environment
discoverability is out of scope.

So:

- Use [`prompts/v2/system.md`](prompts/v2/system.md) **byte-for-byte**. A
  paraphrase, a tightening, or an obvious improvement will silently remove the
  hole and the finding will not reproduce.
- The corrected wording exists, deliberately **not** in the prompt. It lives in
  [`.claude/skills/param-extract/SKILL.md`](.claude/skills/param-extract/SKILL.md)
  and reads: *"Discoverability through the execution environment does NOT count.
  The execution environment — device tree, configuration structure, SBI — is
  outside the ISA."*
- If you want to measure the **fix** rather than the failure, run both wordings as
  separate arms. Do not conflate them.

Why v2 was not fixed in place: applying the fix after observing the result, in
the same version, converts a measurement into a fitted one. See
[`analysis/v2_delta.md`](analysis/v2_delta.md) §4.

## 1. What is being handed over

| Artifact | Path | Dependencies |
|---|---|---|
| **v2 system prompt** | `prompts/v2/system.md` | none — plain markdown, 862 words |
| **v2 user template** | `prompts/v2/user_template.md` | `{source}` and `{snippet}` placeholders |
| **The gate** | `prompts/v2/system.md`, sections *"What counts as an architectural parameter"* and *"Signal words"* | none |
| **Substring validator** | `scripts/validate.py` | `pyyaml` only |
| **Design rationale** | `prompts/v2/README.md` | — |

## 2. The validator, standalone

It now runs on **any** corpus. No record format, no directory layout:

```bash
python3 scripts/validate.py --source chunk_042.txt --extraction model_out.yaml
```

```
source     : chunk_042.txt
extraction : model_out.yaml
grounded excerpts: 0 passed

  ERROR E1 [ASID_WIDTH]: excerpt NOT found in source: 'The number of ... ASID bits is implementation-defined.'
  ERROR E2 [ASID_WIDTH]: signal word 'implementation-defined' used as a constraint value
  warn  E4 [ASID_WIDTH]: description introduces unit 'bytes', absent from the passage

FAIL -- 2 error(s)
```

Batch mode over your own runs, either by pointing at your passages:

```bash
python3 scripts/validate.py --snippets-dir /path/to/chunks results/*/v2
```

or by adding a `source_text` field to each record, which takes precedence and
removes any layout coupling.

⚠️ **This was genuinely broken until now.** Until commit `0ce8ee1` the validator
hardcoded `REPO/snippets/<key>.txt` and crashed with `FileNotFoundError` on any
foreign corpus. The offer on #2053 was made before that was checked. It is fixed
and tested against a synthetic foreign corpus, but the honest note is that the
portability was asserted before it was true.

### The eight checks

| Code | Checks | Severity |
|---|---|---|
| **E1** | `excerpt` is an exact substring of the source (whitespace-normalised) | error |
| E2 | no signal word used as a `constraints` value | error |
| E3 | `defined_by` names nothing absent from the passage | error |
| E4 | `description` introduces no unit absent from the passage | warn |
| E5 | name matches UDB's `^[A-Z][A-Z_0-9]*$` | error |
| E6 | `type` in the permitted set | error |
| E7 | rejection reason codes are known | error |
| E8 | required fields present | error |

**E1 is the load-bearing one.** Whitespace is normalised deliberately: a model
that re-wraps a long quoted line has still copied it; one that paraphrases or
elides has not, and still fails. Provenance is the target, not whitespace
fidelity.

E1 caught `gemini-2.5-flash` writing `"The ... size of a cache block are both
implementation-specific"` — eleven words elided behind an ellipsis, presented as
verbatim, in a response that quoted the same sentence correctly and in full
elsewhere. 17/18 v2 runs passed.

## 3. Reproducing our runs exactly

```bash
python3 scripts/run_extraction.py --prompt v2 --model <id> \
        --provider hf|gemini --runs 3 --max-tokens 16000
```

Parameters we used, for arm comparability:

| Setting | Value |
|---|---|
| `temperature` | `0` |
| `max_tokens` | 8,000 (DeepSeek) / 16,000 (Gemini) |
| runs per model × snippet | **3** |
| name list supplied | **no** — see `reference/prior-art.md` §2 |
| `finish_reason` | asserted; anything but `stop` is a run failure, never an empty result |

Two things worth carrying into a larger run:

- **`temperature=0` is not reliably deterministic, and it is model-dependent.**
  `gemini-2.5-flash` was byte-identical across 6 runs; DeepSeek-V4-Pro produced 3
  distinct outputs on one snippet with a 3.2× spread in completion tokens. N=1
  cannot tell you which you have.
- **Truncation masquerades as a correct empty result.** A reasoning model that
  exhausts its budget returns empty content, which parses as "no parameters
  found" — the correct answer for some passages. Our guard caught six such cases
  on first use. If your harness lacks this check, some of your empty results may
  be truncations.

## 4. What our result does and does not support

Stated so it is not over-cited.

**Supported.** Under this exact prompt, on a passage that places an
implementation-specific clause and an execution-environment discovery clause in
the same sentence, two of three models extracted cache capacity as a parameter
and justified it via execution-environment discoverability, at high confidence,
in 6 of 6 opportunities. The third model rejected it in 3/3 from the identical
prompt.

**Not supported.** Any rate, any distributional claim, any model ranking. n = 2
snippets, 1 gold parameter, 18 usable v2 runs. The tier comparison is confounded
— DeepSeek-V4-Pro is Pro-tier, both Geminis Flash-tier, because Gemini Pro is not
on the free tier.

**The open question we cannot answer and you can.** Does the
execution-environment argument appear when the two clauses are *not* adjacent?

- only when baited → a prompt gap, i.e. our T3 wording
- regardless → a model prior, which is a different and worse problem

Snippet 19.3.1 cannot separate these; it joins both clauses with "and". A
60-chunk corpus can. This is the measurement we would most like to see, and we
cannot make it.

## 5. Reciprocal note

One finding from the other direction, verified here against
`riscv-unified-db@bd775a94` rather than taken on trust:

**`IALIGN` is derived by UDB, not a parameter it lacks.**
`spec/std/isa/isa/globals.isa:797`:

```
function ialign {
  returns Bits<6>
  body {
    if (implemented?(ExtensionName::C) && (CSR[misa].C == 0x1)) {
      return 16;
    } else {
      return 32;
    }
  }
}
```

It is a function of the `C` extension and `misa.C`. So a candidate that two
models independently proposed at high confidence is not a gap in UDB — meaning
**dual-model agreement produced a false positive.** That is a sharper and more
checkable claim than "agreement selects the easy cases."

Verified for `IALIGN` only. `FLEN` and `ILEN` produced no hits in `globals.isa`
and were not chased — **do not assert a category for those.**

## 6. Licence and citation

Code and prose here are freely reusable. If the capacity result is cited, the
useful pointers are `analysis/v2_delta.md` §4 for the finding and
`ground_truth.md` §6 for the predictions it was scored against — the latter
committed at `9d3a0cb`, before any model output existed.
