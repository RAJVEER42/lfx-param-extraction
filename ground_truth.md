# Ground truth — written before any model was run

> **This file is the measurement baseline.** It is committed *before* any LLM
> output exists, so that the models are **measured** rather than trusted. The
> git commit timestamp is the evidence for that ordering; check it against the
> timestamps on anything in `results/`.
>
> Phase 1 of `PLAN.md`. No API calls were made in producing this file.

**Method.** Mechanical trigger scan (`scripts/scan_triggers.py` logic, output
reproduced in §1) → enumerate every candidate a reasonable extractor could
propose → adjudicate each against a stated decision rule → record the expected
result *and* the predicted failure modes.

---

## 1. Mechanical trigger scan — the fact base

The challenge names these as parameter signals: *"may/might/should",
"optional/optionally", "implementation defined"/"implementation specific"*.

Across **both snippets — 185 words total — exactly one brief-listed trigger
phrase occurs.**

| Snippet | Brief-listed triggers | Other modal/hedge words present |
|---|---|---|
| `priv_19_3_1.txt` (96 w) | **`implementation-specific`** ×1 | `shall` ×1 |
| `priv_2_1.txt` (89 w) | **none** | `can` ×1, `by convention` ×1, `"Conventional"` ×1 |

Two consequences, both load-bearing:

1. **`shall` is not `should`.** The brief lists *should* (a recommendation);
   19.3.1 contains *shall* (a mandate). These are near-opposites in
   specification language — `shall` **removes** implementation freedom. A
   trigger-matcher doing loose stemming or synonym expansion will treat
   `shall` as a hit and invert the meaning of the sentence.
2. **Snippet 2.1 contains no brief-listed trigger at all.** Its expected yield
   is therefore **zero parameters**. It is a **negative control** — a precision
   test, not a recall test. This is the load-bearing claim of the whole
   submission and it is falsifiable: any real parameter correctly extracted
   from 2.1 refutes it.

### 1.1 🔑 A clean grounding test, found in the scan

The snippets mention **`CMO`** but **never name `Zicbom`, `Zicbop` or
`Zicboz`** — verified, all three absent from both files.

But UDB's real `CACHE_BLOCK_SIZE` is `definedBy: anyOf [Zicbom, Zicbop, Zicboz]`,
and we confirmed in `reference/models.md` that both candidate models name those
three extensions **correctly and unprompted**.

So if a model outputs those names, the output is **correct but ungrounded** —
sourced from training data, not from the 96 words it was given. That is a
mechanically detectable case of *correct ≠ grounded*, and it is the sharpest
available justification for requiring a verbatim `excerpt` and substring-checking
it. We should expect this and must not score it as a win.

## 2. The decision rule

Derived in phase 0 from cache capacity, and independently corroborated by
`titoatwork`'s WARL finding on issue #2053 (see `reference/prior-art.md` §5):

> **A word signalling implementation freedom is necessary but not sufficient.**
> A parameter exists only where **(a)** the implementation genuinely chooses,
> **and (b)** that choice is **ISA-visible** — some defined instruction or CSR
> behaviour depends on it, or software can observe it through the ISA.

Applied as a three-question test to every candidate:

| # | Question | If no |
|---|---|---|
| Q1 | Is a trigger/signal actually present in **this text**? | not a candidate — fabrication risk |
| Q2 | Does the implementation genuinely **choose**, or is the value architecturally fixed? | reject: fixed convention |
| Q3 | Is the choice **ISA-visible**? | reject: `NON_ISA` |

A candidate must pass all three. Failing Q2 or Q3 makes it a **rejected
candidate with a reason**, which is a result, not a gap.

## 3. Snippet 19.3.1 — adjudication

Full text under consideration:

> Caches organize copies of data into cache blocks, each of which represents a
> contiguous, naturally aligned power-of-two (or NAPOT) range of memory
> locations. A cache block is identified by any of the physical addresses
> corresponding to the underlying memory locations. **The capacity and
> organization of a cache and the size of a cache block are both
> implementation-specific,** and the execution environment provides software a
> means to discover information about the caches and cache blocks in a system.
> In the initial set of CMO extensions, the size of a cache block **shall** be
> uniform throughout the system.

### 3.1 Close reading: the spec's own "both" does the grouping for us

> "The capacity and organization of a cache **and** the size of a cache block
> are **both** implementation-specific"

`both` = **two** groups, not three items. The sentence separates:

- **(a)** "the capacity and organization of a cache" — properties *of the cache*
- **(b)** "the size of a cache block" — a property *of the block*

The spec itself groups cache-internals apart from block size. Our accept/reject
split follows the text's own structure rather than being imposed on it. This is
worth stating: it turns a judgement call into a reading.

### 3.2 Candidates

| ID | Candidate | Q1 signal | Q2 choice? | Q3 ISA-visible? | Verdict |
|---|---|:--:|:--:|:--:|---|
| **C1** | size of a cache block | ✅ `implementation-specific` | ✅ | ✅ CBO ops act on a block; software must know its size | ✅ **PARAMETER** |
| C2 | capacity of a cache | ✅ same phrase | ✅ | ❌ no defined ISA behaviour depends on it | ❌ `NON_ISA` |
| C3 | organization of a cache | ✅ same phrase | ✅ | ❌ same | ❌ `NON_ISA` |
| C4 | block size uniform across system | ⚠️ `shall` (mandate) | ❌ mandated, not chosen | — | ❌ **constraint on C1** |
| C5 | means to discover cache info | ❌ none | ✅ but unspecified | ❌ execution-environment concern | ❌ `NON_ISA` |
| C6 | NAPOT / power-of-two range | ❌ none | ❌ architecturally required | — | ❌ **constraint on C1** |
| C7 | cache block identified by any constituent physical address | ❌ none | ❌ architectural statement | — | ❌ not a candidate |

**Expected yield: 1 parameter, 6 rejected candidates.**

### 3.3 C1 in detail

| Field | Value | Grounded in |
|---|---|---|
| name | `CACHE_BLOCK_SIZE` | UDB (exists — verified, phase 0) |
| description | The observable size of a cache block, in bytes | snippet + UDB |
| type | `integer` | UDB `schema.type` |
| constraint: power of two | from *"naturally aligned power-of-two (or NAPOT)"* | **snippet** |
| constraint: uniform system-wide | from *"shall be uniform throughout the system"*, scoped to *"the initial set of CMO extensions"* | **snippet** |
| constraint: `minimum` | **the snippet states no numeric bound** | ⚠️ UDB says `minimum: 1`; that is UDB's modelling, **not** in this text |
| `definedBy` | `anyOf [Zicbom, Zicbop, Zicboz]` | ⚠️ **UDB only — these names are absent from the snippet.** See §1.1 |

The two ⚠️ rows are the honest boundary of what these 96 words support. Anything
numeric beyond "power of two" is **constraint invention**. Anything naming the
three extensions is **ungrounded**, even though it is correct.

### 3.4 The uniformity constraint deserves care

*"In the initial set of CMO extensions, the size of a cache block shall be
uniform throughout the system."*

Three separate observations:

1. **It is a constraint, not a parameter** — it removes freedom rather than
   granting it.
2. **It is temporally scoped.** "In the initial set of CMO extensions" is the
   spec explicitly reserving the right to relax this later. Encoding it as an
   unconditional invariant would be wrong.
3. **It is system-scoped, while UDB parameters are largely per-hart** (phase 0).
   There may be no clean place to express it. Record as prose + an open question
   for the SIG; **do not invent a schema field.**

## 4. Snippet 2.1 — adjudication

> "Conventional" R/W accessibility of CSRs according to address mapping
>
> The standard RISC-V ISA sets aside a 12-bit encoding space (csr[11:0]) for up
> to 4,096 CSRs. By convention, the upper 4 bits of the CSR address (csr[11:8])
> are used to encode the read and write accessibility of the CSRs according to
> privilege level as shown in Table 1. The top two bits (csr[11:10]) indicate
> whether the register is read/write (00,01, or 10) or read-only (11). The next
> two bits (csr[9:8]) encode the lowest privilege level that can access the CSR.

### 4.1 Candidates — all rejected

| ID | Candidate | Why it lures | Why it fails |
|---|---|---|---|
| **D1** | number of CSRs / 4,096 | *"up to 4,096"* reads like an upper bound | Fixed size of the **encoding space**. Not an implementation choice. Fails Q2 |
| **D2** | CSR address width = 12 | a width looks parameterisable | Architecturally fixed at 12. Fails Q2 |
| **D3** | R/W-vs-read-only encoding, `csr[11:10]` | *"By convention"* hedges | Fixed architectural encoding, uniform across implementations. Fails Q2 |
| **D4** | lowest privilege level per CSR, `csr[9:8]` | *"can access"* is a modal | Determined by the CSR's **address**, which is architecturally assigned. Fails Q2 |
| **D5** | **which CSRs are implemented** | genuinely *is* implementation/extension-dependent | ⚠️ **Not stated in this snippet.** Extracting it is fabrication from model priors. Fails **Q1** |

**Expected yield: 0 parameters, 5 rejected candidates.**

### 4.2 D5 is the trap, and it is the most informative single candidate

D5 is the only candidate here that names something *genuinely* implementation-
dependent — real UDB parameters of that flavour exist. But **this text does not
say it.** The snippet describes how CSR addresses *encode* accessibility; it
never discusses which CSRs exist.

So D5 separates two kinds of model:

- one that reads **the snippet** → does not produce D5
- one that reads **"RISC-V CSRs"** and answers from training data → produces D5

A model that emits D5 is right about RISC-V and wrong about the task. Since we
verified both candidate models know RISC-V well, this is a live risk, not a
hypothetical.

### 4.3 On `"Conventional"` in scare quotes

The heading's quotation marks are the strongest lure in the snippet — they
signal the author knows the convention has exceptions. But an **exception to a
convention is an architectural exception, not an implementation parameter**, and
crucially the snippet **names none**. Extracting a parameter from the scare
quotes alone would be inferring un-stated content from punctuation.

## 5. Expected result — the gold set for these two snippets

```yaml
# 19.3.1
parameters:
  - CACHE_BLOCK_SIZE      # integer, power-of-two, uniform system-wide (initial CMO set)
# 2.1
parameters: []            # correct, and expected
```

**1 parameter. 11 rejected candidates. Both snippets combined.**

## 6. 🔒 Preregistered predictions

Stated now, before any run, so the analysis in phase 4 cannot be fitted after
the fact. Each is falsifiable.

| # | Prediction | Confidence |
|---|---|---|
| **P1** | Both models extract `CACHE_BLOCK_SIZE` from 19.3.1 | high |
| **P2** | ≥1 model emits cache capacity and/or organization as parameter(s) — the primary over-extraction | high |
| **P3** | ≥1 model emits ≥1 parameter from 2.1 despite zero brief-listed triggers — most likely D1, D2 or D5 | high |
| **P4** | ≥1 model invents a numeric bound absent from the text (e.g. `minimum: 4`, `maximum: 512`, "typically 64 bytes") — **constraint invention** | medium-high |
| **P5** | ≥1 model names `Zicbom`/`Zicbop`/`Zicboz`, which appear nowhere in the snippets — **correct but ungrounded** (§1.1) | high |
| **P6** | ≥1 model treats `shall be uniform` as a trigger and emits a uniformity parameter | medium |
| **P7** | The two models **disagree** on at least one candidate | medium-high |

### How these will be scored

- **Per-candidate adjudication, not aggregate rates.** n = 2 snippets and 12
  candidates. Percentages would imply precision the sample cannot support, and
  no Jaccard coefficient will be reported (`prior-art.md` §7).
- **Any recall figure states whether names were supplied.** Ours are supplied
  **no** name list — unlike Part I (`prior-art.md` §2). Not comparable; will be
  said explicitly rather than left implied.
- **P5 is scored mechanically**, by substring-checking every `excerpt` against
  the source snippet. That check is phase 6's validator.

### What would falsify this ground truth

Stated so it can be held to:

1. A **real** parameter correctly extracted from 2.1 → the negative-control
   claim is wrong.
2. Evidence that UDB models cache capacity or organization → the `NON_ISA`
   judgement is wrong. *(Checked: no such param file among 227.)*
3. A defensible numeric bound on block size derivable from the snippet alone →
   the constraint-invention line is drawn too tightly.

## 7. Deliberately unresolved

- The **227 vs 223** parameter-count discrepancy (`prior-art.md` §3).
- Whether UDB's `minimum: 1` on `CACHE_BLOCK_SIZE` is deliberate or a
  placeholder. A cache block of 1 byte is not physically meaningful, but the
  snippet gives no bound, so we will not propose one.
- Where a **system-scoped** invariant belongs given per-hart parameters (§3.4).
