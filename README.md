# AI-assisted extraction of architectural parameters from RISC-V specifications

Coding challenge submission — LFX Mentorship, Fall 2026
RISC-V International / `riscv/riscv-unified-db`

Author: Rajveer Bishnoi ([@RAJVEER42](https://github.com/RAJVEER42))

---

> **Status: scaffold.** Sections below are placeholders to be filled in as the
> work is done. Nothing here is a result yet.

## 1. Task

Develop prompts that extract architectural parameters from snippets of the
RISC-V ISA Manual. Per the challenge brief, the following usually signal a
parameter:

- "may / might / should"
- "optional / optionally"
- "implementation defined" / "implementation specific"

Deliverables requested:

1. Details about the LLM(s) used — name, version, context length.
2. The prompts, and how they were developed and refined, including how model
   hallucinations were dealt with.
3. Results as a YAML file with fields for name, description, type, constraints.

## 2. Input snippets

| File | Source |
|---|---|
| `snippets/priv_19_3_1.txt` | Privileged spec 19.3.1 — cache blocks |
| `snippets/priv_2_1.txt` | Privileged spec 2.1 — CSR address mapping |

Both stored verbatim as given in the challenge document.

## 3. Models used

<!-- name, version, context length, access method, date run -->

| Model | Version | Context | Notes |
|---|---|---|---|
| _TBD_ | | | |

## 4. Prompt development

<!--
Narrative, not a summary. For each iteration:
  - what the prompt asked for
  - what it got wrong (verbatim examples)
  - what changed in response, and why
Commit history in this repo is the primary evidence — one commit per iteration.
-->

### v1

### What went wrong

### v2

## 5. Handling hallucinations and false positives

<!--
Two distinct failure modes to keep separate:
  - fabrication: parameter asserted that has no basis in the snippet text
  - over-triggering: real trigger word ("should", "may") that is guidance,
    not an implementation-defined parameter
Record rejected candidates and the reason. Judgement shown here is worth as
much as recall.
-->

| Candidate | Snippet | Verdict | Reason |
|---|---|---|---|

## 6. Results

Final output: [`parameters.yaml`](parameters.yaml)

<!-- summary table of extracted parameters -->

## 7. Reproducing

```bash
# TBD
```

## 8. Notes on UDB alignment

<!--
The proposal's item 4 is exporting to UDB YAML format. Parameter files in
riscv-unified-db live at spec/std/isa/param/<NAME>.yaml and are validated
against spec/schemas/param_schema.json. Shaping output toward that schema
rather than an ad-hoc one is deliberate.
-->
