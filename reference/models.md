# Models — verified details

Challenge deliverable 1 asks for *"name, version, context length etc."* for each
LLM used. Everything here was read from the model's own `config.json` or from a
live API response, not recalled.

Verified 2026-07-27.

---

## 1. Selected pair

The comparison axis is deliberate: **frontier proprietary vs frontier
open-weights**.

| | Model A | Model B |
|---|---|---|
| **Name** | Claude Opus 5 | DeepSeek-V4-Pro |
| **Exact model ID** | `claude-opus-5[1m]` | `deepseek-ai/DeepSeek-V4-Pro` |
| **Context length** | 1,000,000 | **1,048,576** (`max_position_embeddings`) |
| **Weights** | proprietary | open, **MIT** |
| **Access** | Claude Code | HF Inference Providers (novita / together / fireworks-ai) |
| **Architecture** | not disclosed | `DeepseekV4ForCausalLM`, bfloat16, MoE |
| **Reasoning model** | yes | yes — `reasoning_content` separate from `content` |

Why this pair rather than two proprietary models:

- **Reproducibility.** MIT weights mean anyone can rerun the extraction without
  a proprietary API key. For an *open* ISA, an open-weights model in the loop is
  a substantive argument, not a cosmetic one.
- **True independence.** Different labs, different training data, different
  tokenizers. Agreement between them is meaningful evidence; agreement between
  two models from one lab is much weaker.
- **Comparable context.** Both ~1M, so context length is not a confounding
  variable when we compare outputs.

DeepSeek-V4-Pro's context is reached via **YaRN** RoPE scaling
(`factor: 16`) from a native `original_max_position_embeddings` of **65,536**.
Worth stating precisely rather than quoting "1M" flatly — the effective quality
at full extension is not guaranteed. Irrelevant for our snippets (a few hundred
tokens), relevant if the pipeline is ever pointed at the whole spec.

## 2. Candidates evaluated and rejected

All smoke-tested live before choosing.

| Model | Context | License | Result |
|---|---|---|---|
| `zai-org/GLM-5.2` | 1,048,576 | MIT | Works, but `content` came back **empty** with `finish_reason: length` — spends heavily on reasoning. Viable third model if time allows |
| `openai/gpt-oss-120b` | 131,072 | Apache-2.0 | Works, correct answer. Rejected only because 131k context is the odd one out; strong backup |
| `moonshotai/Kimi-K2-Instruct-0905` | — | other | License is `other`, which weakens the open-reproducibility argument |

Domain sanity check — asked each to name the three CMO extensions:
`Zicbom, Zicbop, Zicboz`. Both DeepSeek-V4-Pro and gpt-oss-120b answered
correctly, unprompted.

> ⚠️ **This cuts both ways.** The models already know RISC-V. That is a *risk*,
> not a reassurance: it means a correct-looking answer may come from training
> data rather than from the snippet. It is exactly why the v2 prompt must force
> a verbatim `excerpt` and why the validator checks it is a real substring.
> See `notes/phase-0.md` and the 2.1 "which CSRs exist" trap.

## 3. ⚠️ Methodology trap found during setup

**All three open models are reasoning models, and a naive `max_tokens` silently
produces a false negative.**

GLM-5.2 at `max_tokens=30`, then at `250`:

```
content         : ''
finish_reason   : length
usage           : prompt=28  completion=250
```

The model burned its entire budget on `reasoning_content` and returned an **empty
`content`**. An extraction harness that parses that empty string concludes
*"the model found no parameters in this snippet."*

That is indistinguishable, at the parse layer, from a correct empty result — and
we specifically **want** correct empty results on snippet 2.1. So truncation
would masquerade as the exact behaviour we are trying to measure.

**Mitigations, to be built into the phase-3 runner:**

1. Assert `finish_reason == "stop"`. Treat `"length"` as a **run failure**, never
   as an empty result.
2. Set `max_tokens` generously and record it as a run parameter.
3. Log `reasoning_content` length and `completion_tokens` separately per run, so
   reasoning spend is visible in the cost table.
4. Distinguish three outcomes in the results schema: `parameters: []`
   (a real, correct empty extraction) vs `truncated` vs `parse_error`.

This is a genuine engineering finding and belongs in the README — it is the
difference between running an API and understanding one.

## 4. Run parameters to pin (phase 3)

| Parameter | Value | Reason |
|---|---|---|
| `temperature` | `0` | Extraction is not a creative task; we want the mode |
| `max_tokens` | generous, recorded | see §3 |
| runs per (model, snippet, prompt) | **N = 3** | temperature 0 is *not* determinism — provider batching and MoE routing vary. Report agreement, don't assume it |
| `seed` | set if the provider honours it | most Inference Providers do not; do not claim determinism we cannot show |

## 5. Credentials

Token lives in HF's own store (`~/.cache/huggingface/token`, mode 600) and is
read automatically by `huggingface_hub`. **No token appears in any file in this
repo**, hardcoded or otherwise — this repo is the submission artifact, and a
secret committed once persists in git history even after deletion.

Account: `Krishna3451112` · token scope `write` (inference needs only `read`) ·
billing period ends 2026-08-01.

## 6. Reproducing the model runs — operational notes

The committed output in `results/` is the record. Re-running is optional, and
`./run.sh` without `--with-models` verifies everything checkable offline.

If you do re-run, expect these:

| Symptom | Cause | Action |
|---|---|---|
| `429 RESOURCE_EXHAUSTED` on Gemini | Free-tier daily quota. 18 runs of two models plus smoke tests is enough to exhaust it | Wait for the daily reset (~midnight US Pacific), or use a paid key |
| `403 PERMISSION_DENIED`, *"Your project has been denied access"* | The API key belongs to a Google Cloud project without access — typically a fresh project lacking the Generative Language API, not an account-level block | Create the key under a project already known to work; check the project selector in AI Studio |
| `429` on `gemini-2.5-pro` specifically | Not on the free tier at all — quota is zero, not exhausted | Use a Flash model, or a paid key |
| Empty `content` with `finish_reason: length` | Reasoning model exhausted its budget | Raise `--max-tokens`. The runner already records this as a failure, not an empty result |

Both Gemini failure modes above were encountered during this work and are
recorded here rather than omitted — the free tier is genuinely rate-limited, and
a reviewer hitting a `429` should know it is expected rather than a defect in the
harness.
