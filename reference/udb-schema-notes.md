# UDB parameter schema — verified notes

Phase 0 of `PLAN.md`. Purpose: know the real target schema before generating
anything, so no field name in our output is guessed.

**Everything here was read from the source, not recalled.**

Repo: <https://github.com/riscv/riscv-unified-db>
Commit inspected: `bd775a94d8cd7db94a9202397d055e880456245a` (2026-07-27T05:29:16Z,
*"Port Pages schema and GitHub pages publishing to Python (#1973)"*)

---

## 1. Where parameters live

| Path | Contents |
|---|---|
| `spec/std/isa/param/<NAME>.yaml` | One file per parameter. **227 files** at this commit |
| `spec/schemas/param_schema.json` | The validating schema (JSON Schema draft-07) |
| `spec/schemas/schema_defs.json` | Shared `$defs` referenced by the above |

Note: Part I (#1765) cataloged **185** parameters. There are **227** now — the
DB has grown ~23% since. Any recall figure quoted against Part I's ground truth
is measured against a smaller denominator than exists today.

## 2. `param_schema.json` — the actual contract

Required fields: `$schema`, `kind`, `description`, `long_name`, `definedBy`,
`schema`. `additionalProperties: false`.

| Field | Type / constraint |
|---|---|
| `$schema` | `const: "param_schema.json#"` |
| `kind` | `const: "parameter"` |
| `name` | `$ref schema_defs.json#/$defs/param_name` → `pattern: ^[A-Z][A-Z_0-9]*$` |
| `long_name` | string, described in-schema as *"Short description of the parameter"* |
| `description` | `$ref .../spec_text` (Asciidoctor source, or array of conditional text). Described as *"Parameter description, **including list of valid values**"* |
| `definedBy` | `$ref .../condition` — extension requirement gating existence |
| `schema` | `$ref json-schema-draft-07.json#` — the parameter's own value domain |
| `requirements` | optional `$ref .../condition` — cross-parameter constraints |
| `$source` | optional, source file |

Two things worth internalising:

- **`name` is not required by the schema.** It is present in every file, but
  formally optional — presumably derived from the filename.
- **`type` and `constraints`, the two fields the challenge asks for, are not
  top-level fields.** They live *inside* `schema:` as ordinary JSON Schema
  (`type`, `minimum`, `maximum`, `enum`). Mapping the challenge's requested
  shape onto this is a real translation step, not a rename.

## 3. `CACHE_BLOCK_SIZE` already exists

Verbatim, `spec/std/isa/param/CACHE_BLOCK_SIZE.yaml`:

```yaml
$schema: param_schema.json#
kind: parameter
name: CACHE_BLOCK_SIZE
description: "The observable size of a cache block, in bytes

  "
long_name: TODO
schema:
  type: integer
  minimum: 1
  maximum: 18446744073709551615
definedBy:
  extension:
    anyOf:
      - name: Zicbom
      - name: Zicbop
      - name: Zicboz
```

This is the ground truth for snippet 19.3.1, and it confirms the phase-1
hypothesis: **of the three implementation-specific things in that sentence
(cache capacity, cache organization, cache block size), only block size is
modelled as a parameter.** Cache capacity and organization have no parameter
file anywhere in the 227. The `NON_ISA` judgement is not our invention — it is
what the maintainers actually did.

`definedBy` uses `anyOf` over Zicbom / Zicbop / Zicboz: the parameter exists if
*any* CMO extension is implemented. Note the snippet's phrase *"the initial set
of CMO extensions"* corresponds exactly to these three.

Related: `FORCE_UPGRADE_CBO_INVAL_TO_FLUSH` (boolean, `definedBy: Zicbom`) —
the only other CMO parameter.

## 4. Three gaps in the current file (verified, actionable)

### 4.1 The power-of-two constraint is not encoded

The snippet states a cache block is a *"contiguous, naturally aligned
power-of-two (or NAPOT) range"*. The schema is `minimum: 1, maximum: 2^64-1`,
which admits `3`, `5`, `7`, `100` — values the spec forbids.

`schema_defs.json` **already defines** `$defs/64bit_unsigned_pow2` and
`$defs/32bit_unsigned_pow2` for exactly this.

And `$ref` into `schema_defs.json` from a param file is **precedented** —
`CONFIG_PTR_ADDRESS.yaml`, `IMP_ID_VALUE.yaml` and `ARCH_ID_VALUE.yaml` all do
`$ref: schema_defs.json#/$defs/uint64`. So the fix is idiomatic:

```yaml
schema:
  $ref: schema_defs.json#/$defs/64bit_unsigned_pow2
```

`MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE.yaml` is the alternative precedent — it
spells the enum out inline (`enum: [0, 2, 4, ... 4096]`) with a comment
justifying the upper bound.

### 4.2 UDB contains two implementations of "power of two", and they disagree

This is the most substantive finding in phase 0.

**Implementation A — the JSON-Schema enum.** `spec/schemas/schema_defs.json`,
lines **866** and **876**:

```
1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4095, 8192, 16384, ...
```

`4095` is not a power of two. Verified programmatically: it is the **only**
non-power-of-two in either enum, and `4096` (2^12) is **absent from both**.
`32bit_unsigned_pow2` has 32 entries covering 2^0..2^31 with 2^12 missing;
`64bit_unsigned_pow2` has the same hole.

**Implementation B — the Z3 solver.** UDB feeds parameter schemas to a Z3 SMT
solver to check constraint satisfiability. `tools/ruby-gems/udb/lib/udb/z3.rb`
special-cases the same two `$ref`s (lines 414–419) and **ignores the enum
entirely**, using the standard bit trick instead:

```ruby
elsif schema_hsh.fetch("$ref").split("/").last == "64bit_unsigned_pow2"
  assertions << ((term == 0) | (0 == (term & (term - 1))))
  assertions << ((term.unsigned_gt(0)) & (term.unsigned_le(2**64 - 1)))
```

`x & (x-1) == 0` is mathematically correct for powers of two.

**So the two disagree on exactly two values:**

| Value | JSON-Schema enum | Z3 solver | Correct? |
|---|---|---|---|
| **4096** (2^12) | **rejects** | accepts | Z3 is right |
| **4095** | **accepts** | rejects | Z3 is right |

4096 is the most common page and cache-block size in the architecture. A
parameter constrained by these defs would satisfy constraint solving and fail
schema validation, or vice versa, for that one value.

This is the same *shape* of bug as #2152 (the CI outage): two code paths
implementing one rule, differing on an edge case, with neither obviously wrong
in isolation.

Minor, secondary: the `(term == 0)` disjunct on the first assertion line is dead
code — the very next assertion requires `term > 0`, contradicting it. Harmless,
but it suggests the two lines were written at different times.

### 4.3 Why the bug is latent, and why that matters to us

Repo-wide grep (full tree, 143 MB checkout at the commit above) — the pow2 defs
are referenced in exactly **three** places, all tooling, **no data**:

- `tools/ruby-gems/udb/lib/udb/z3.rb` (the solver translation above)
- `tools/ruby-gems/udb/test/test_z3_parameter_constraints.rb` (tests)
- `tools/ruby-gems/udb/test/test_conditions.rb` (tests)

**No parameter file, and no file under `spec/`, `$ref`s either def.** The enum
therefore has no live data consumer today, which is why the `4095` typo has
survived — the tests exercise the Z3 path, which never reads the enum.

The consequence is a neat narrative for the submission: the idiomatic fix for
§4.1 is to have `CACHE_BLOCK_SIZE` adopt `64bit_unsigned_pow2` — and doing so
would make `CACHE_BLOCK_SIZE = 4096` fail validation. **The fix in §4.1 is
blocked on the bug in §4.2.** Finding that ordering is worth more than either
finding alone.

Remaining unknown, do not assert either way: exactly when the enum is evaluated
against a concrete config value (i.e. whether a `config` supplying
`CACHE_BLOCK_SIZE: 4096` would actually be rejected today). `param_schema.json`
validates that `schema:` *is a valid JSON Schema*; the value-validation path
needs separate tracing before any bug report claims user-visible impact.

## 5. `long_name: TODO` — 163 of 227 files

**71.8%** of parameter files have the literal placeholder `long_name: TODO`,
including `CACHE_BLOCK_SIZE` and `FORCE_UPGRADE_CBO_INVAL_TO_FLUSH`.

This reframes the submission. The repo's unmet need is not *finding*
parameters — the maintainers found 227. It is **populating the prose fields at
scale**, which is precisely what an LLM is good at and a human is slow at. Our
output should therefore supply a real `long_name` and a `description` that
actually *"includ[es] list of valid values"* as the schema asks, rather than
reproducing `TODO`.

Caveat before claiming this too loudly: check whether `long_name` is being
deliberately deprecated. `MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE` inverts the
convention — it puts the *long* sentence in `long_name` and the detailed prose
in `description` — so usage is inconsistent across the repo. Ask in the SIG
rather than asserting.

## 6. Beyond `type` + `constraints` — two mechanisms the challenge doesn't mention

Worth knowing because they show the schema is richer than "name/type/constraint".

**`definedBy` can depend on other parameters, with a stated reason.** From
`MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE.yaml`:

```yaml
definedBy:
  allOf:
    - extension: {name: Sm}
    - param:
        name: MISALIGNED_LDST
        equal: true
        reason: Granule size is only relevant when misaligned load/stores might execute without an exception.
```

**`requirements` uses IDL, UDB's own constraint language.** From
`GSTAGE_MODE_BARE.yaml`:

```yaml
requirements:
  idl(): |
    $array_includes?(SXLEN, 32) && !SV32X4_TRANSLATION -> GSTAGE_MODE_BARE;
```

Implication for us: the snippet's *"shall be uniform throughout the system"* is
a **system-level invariant**, and UDB's parameters are largely **per-hart**.
There may be no clean place to express it in a single param file. Flag it as an
open question rather than inventing a field for it.

## 6a. Incidental finding — duplicate index in `HPM_EVENTS.yaml`

Found while verifying a public claim about `definedBy` complexity, not while
working on the snippets. Recorded because it is verified and small.

`spec/std/isa/param/HPM_EVENTS.yaml` gates on `allOf` over extension `Sm` plus a
`param.anyOf` across `HPM_COUNTER_EN` indices. The `anyOf` has **30 entries but
only 29 distinct indices** — index **4 appears twice**:

```
indices : [3, 4, 4, 5, 6, 7, ... 31]
duplicate: {4: 2}
distinct : 29
```

29 distinct is the correct count (`mhpmcounter3`..`mhpmcounter31`), so the
intended semantics are right and an `anyOf` containing a duplicate is redundant
rather than wrong. It is a tidy-up, not a defect with behaviour.

Same family as the already-merged #2118, which corrected inverted `type()` logic
across 29 `scountovf` fields.

### Verified composition of `definedBy` across all 227 parameters

Useful context for how much a model would have to infer to propose this field:

| Shape | Count | Share |
|---|---:|---:|
| single bare extension reference | 173 | 76.2% |
| `extension:` containing `anyOf`/`allOf` | 31 | 13.7% |
| top-level boolean combinator | 18 | 7.9% |
| param-gated only | 5 | 2.2% |
| **not a single bare extension** | **54** | **23.8%** |
| **gated on another parameter's value** | **23** | **10.1%** |

## 7. Open questions for the SIG

1. Is `long_name` being deprecated, or should the 163 `TODO`s be filled?
2. Should `CACHE_BLOCK_SIZE` adopt `64bit_unsigned_pow2`, and is the `4095`
   entry a known typo?
3. Where does a *system-scoped* invariant like uniform cache block size belong,
   given parameters are per-hart?
