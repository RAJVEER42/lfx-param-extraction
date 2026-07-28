# Prior art — issue #2053 and the public Part I measurements

Source: <https://github.com/riscv/riscv-unified-db/issues/2053>
*"Question: scope of parameter extraction already completed (Spring 2026
mentorship term)"* — opened by `hjaat`, 2026-07-21. Read 2026-07-27, 8 comments.

Every load-bearing claim below was **independently re-verified against source**,
not taken from the thread. Verification commands and results are recorded inline.

---

## 1. Attribution — get this right

The thread is easy to misattribute, and misattributing it publicly would be
worse than not citing it at all.

| Person | Contribution |
|---|---|
| **`hjaat`** | Opened the issue. Raised the CSR-field/WARL misclassification and duplication problem *conceptually*, credited to a Slack exchange with **Allen Baum**. Wrote a [gist](https://gist.github.com/hjaat/7ab4f66dcda775fe089b28cb4d47e6bb) on an extraction approach. The evaluation itself was run by `titoatwork`, below. |
| **`titoatwork`** | Ran the actual measurement: regenerated ground truth, per-class recall, the WARL prompt ablation, cross-model agreement. Posted the "legal-value set must be implementation-chosen" refinement. Then posted a **public self-correction** invalidating his own headline framing |
| **`Maanvi212006`** | Pointed `hjaat` to PRs #1831 / #1832 |
| **`ishaan-arora-1`** | Part I mentee. **Stated the current pipeline is internal and unpublished** |

> ⚠️ The WARL numbers, the ablation and the legal-value-set refinement are
> **`titoatwork`'s**, not `hjaat`'s. `hjaat` raised the problem; `titoatwork`
> measured it, and `hjaat` then acknowledged the refinement was "sharper than
> I'd understood it."

## 2. 🔴 The finding that changes our plan: Part I recall measures grounding

`titoatwork`'s second comment corrects his own first one. This is the single most
consequential item in the thread, and it was **verified independently here**.

### The claim

Every Part I prompt has the 185 ground-truth parameter **names injected into it**,
so the published recall figures measure *grounding* — locate which of these known
names apply to this passage — not *discovery*.

### Independent verification

Files fetched from the PR head (`ishaan-arora-1:lfx-phase4-llm-extraction`, PR #1791):

```
injected list size : 185
gold set size      : 185
identical sets     : True
in list not gold   : none
in gold not list   : none
```

`param_extraction/scripts/extract.py:211`, no conditional, no flag:

```python
def build_user_message(chunk_text: str, chunk_meta: dict) -> str:
    examples = load_examples()
    param_names = load_udb_param_names()
    parts = [
        format_examples_section(examples),
        format_param_names_section(param_names),   # <-- always
        _format_chunk(chunk_text, chunk_meta),
    ]
```

And the exact instruction, `run_prompt.py:116`:

```
## Known UDB Parameter Names

When a parameter you find matches one of these known names, use the exact name.
For new parameters not in this list, suggest a descriptive UPPER_SNAKE_CASE name.
```

**Verdict: confirmed.** The name list is unconditionally injected and is
set-identical to gold.

### One point in Part I's favour, which the thread understates

The instruction *does* invite new discovery ("For new parameters not in this
list, suggest a descriptive UPPER_SNAKE_CASE name"), so the task is not purely
grounding. But recall **measured against GT185** only scores the matching half.
So the correction stands: **recall-against-GT185 is grounding-conditioned.** The
nuance sharpens the point rather than weakening it.

### Consequences for us

1. **Do not cite "69.7% recall" as a discovery benchmark.** Part I's PRs are
   sometimes read as "the rubric" and its numbers as the bar. As a discovery
   number, 69.7% is not that. Repeating it that way reproduces an error that
   has since been publicly corrected.
2. Any recall figure we report must state whether names were supplied.
3. The genuinely unmeasured quantity is recall **without** the name list.
   `titoatwork` has [preregistered](https://github.com/titoatwork/lfx-firstanalysis/blob/main/riscv-param-extraction/artifact_c/PREREGISTRATION.md)
   that measurement. **We should not race him to it** — n=2 snippets cannot
   measure it anyway.

## 3. Verified ground-truth composition

From `param_extraction/data/ground_truth.json` on the PR branch — counted here:

| Class | Count |
|---|---:|
| `NORM_DIRECT` | 102 |
| `NORM_CSR_RW` | 55 |
| `NORM_CSR_WARL` | 26 |
| `SW_RULE` | 2 |
| **total** | **185** |

`metadata`: `{"total_parameters": 185, "source": "spec/std/isa/param", "csr_source": "spec/std/isa/csr"}`

`titoatwork` reports a regenerated live ground truth of **223** — DIRECT 140 /
CSR_RW 55 / WARL 26 / SW_RULE 2. The delta is **entirely in DIRECT** (102 → 140),
with the CSR and SW_RULE classes unchanged. That is internally consistent and
arithmetically checks out.

⚠️ **Unresolved:** we counted **227** files in `spec/std/isa/param/` at
`bd775a94` (see `udb-schema-notes.md`); `titoatwork` reports 223 real parameters.
A 4-file discrepancy. Do not quote either number as "the" count without
resolving what is excluded.

## 4. WARL — the reported failure class

`titoatwork`'s per-class recall of the committed Part I v2 output:

| Class | Recall |
|---|---:|
| DIRECT | 83/100 |
| CSR_RW | 32/51 |
| **WARL** | **12/24 (50%)** |

**Prompt-only intervention made it worse.** Adding a structural
WARL-recognition section: adjusted recall 32.2% → 35.0%, but *gold WARL recall
fell* 12.5% → 8.3%, while raw WARL labels rose ~36 → 59. The model labelled more
things WARL without finding more real ones. A null result.

Read together with §2, this is sharper than it first appears: **WARL recall is
12/24 with all 24 correct names already in the prompt.** The failure is
*identification*, not vocabulary — which is exactly why more prompt text made it
worse. A model that was never missing the name gains nothing from being told the
name again.

🔸 Not independently verified: these recall figures and the ablation. They are
`titoatwork`'s measurements of his own reproduction. Cite as *reported by*, and
note we verified the name-injection claim underneath them but not the scoring.

## 4a. A second defect, independent of the name injection

§2 records one problem with Part I's published figures: the gold names were in the
prompt, so recall measures grounding. There is a **second, separate** problem, and
fixing the first does not fix it.

`titoatwork` reran the published condition with a **byte-identical prompt**, same
model, same prompt version, as Arm A of his four-arm study. Reported on #2053:

| | Published | Arm A rerun |
|---|---|---|
| WARL recall | 3/24 | **9/24** |
| Overall adjusted recall | 32.2% | 33.9% |

The aggregate barely moved. The per-class number tripled. So the instability is
concentrated in exactly the small-denominator class any WARL claim would rest on.

**Why this matters more than it first looks.** Part I's published v1 → v2
improvement was measured the same way: single runs per condition. If a byte-identical
prompt can move WARL from 3/24 to 9/24, then a v1 → v2 delta measured once per
condition cannot distinguish a prompt improvement from run-to-run variance. The
reported improvement may be real, but the measurement as performed cannot establish
it.

That is a different failure from name injection. Supplying no catalogue fixes §2 and
leaves this untouched. Both have to be addressed before any per-class figure from
that pipeline is quotable.

**What we do about it.** Our own numbers are aggregates over 9 or 18 runs, never a
single run, and N=3 was fixed in advance for this reason
(`reference/models.md` §4). `scripts/audit_claims.py` re-derives every per-class
count from the raw records, so the denominators are visible rather than asserted.

The rule worth keeping, in `titoatwork`'s framing: **do not release per-class
numbers from a single run.** That holds even after the instability is understood,
because the fix is more runs, not a better explanation.

🔸 Not independently verified: the 3/24 versus 9/24 figures are his measurements of
his own reruns. Cite as reported by. The general point, that a single run cannot
support a per-class claim, stands on its own and matches what we observed directly
(`analysis/v1_failures.md` §6, where one model produced three distinct outputs at
`temperature=0`).

## 5. 🔑 The principle — and why it is the same one we found

`titoatwork`, on WARL:

> the *word* WARL appears where the legal value set is fixed by the ISA. The
> field is WARL, but no implementation choice exists, so it isn't an
> architectural parameter. Requiring that the **set of legal values be
> implementation-chosen**, rather than that the field merely be labelled WARL,
> removes a whole class of false positives.

**This is the same discriminator we derived in phase 0 from cache capacity**, via
a completely different route. Unified statement:

> **A phrase or label signalling implementation freedom is necessary but not
> sufficient. A parameter exists only where the implementation genuinely
> chooses — and where that choice is ISA-visible.**

| Case | Signal present | Real choice? | Parameter? |
|---|---|---|:--:|
| cache block size | "implementation-specific" | yes, ISA-visible via CBO | ✅ |
| cache capacity (ours, phase 0) | "implementation-specific" | yes, but **ISA-invisible** | ❌ |
| WARL field, ISA-fixed legal set (`titoatwork`) | labelled "WARL" | **no choice exists** | ❌ |
| CSR address mapping (snippet 2.1) | "By convention" | no — architecturally assigned | ❌ |

Two independent failure routes, one rule. That generalisation is worth stating
explicitly in the README — it covers both our snippets *and* the hardest known
failure class.

## 6. Snippet 2.1's importance just increased

2.1 is about CSR **address mapping** and R/W accessibility. WARL is about CSR
**field** legal values. Different mechanisms, but the same shape of false
positive: *CSR-flavoured text that looks parameterisable and is not.*

And the CSR classes are the measured weak spots — CSR_RW 32/51, WARL 12/24. So
our negative control is probing the exact region where the only public
evaluation says extraction is worst. That is a much stronger justification for
the rejected-candidates table than "it seemed like a good idea."

## 7. Cross-model agreement — relevant to our two-model design

`titoatwork`, same prompt and chunks, two models:

- **346** vs **230** unique parameter names, **21** shared → Jaccard **3.8%**
- high-confidence *proposed-new* names: 236 vs 218, only **9** proposed by both

Conclusion he draws, which we adopt: a single model's new-parameter list should
not be trusted without a review gate.

**Implications for our plan:**

- Our two-model design is validated — but **expect disagreement**, and treat
  agreement as weak evidence rather than confirmation.
- 🔸 **Do not compute Jaccard on 2 snippets.** With n=2 the statistic is
  meaningless. Report the raw per-snippet comparison and say why we are not
  reporting a coefficient. Restraint here is itself a signal.

## 8. Scope: what is actually current

`ishaan-arora-1`:

> The recent works that have been going on for parameter extraction are internal
> and are not uploaded on this repository yet. […] those prs were the first
> version of the pipeline […] the pipeline has evolved ever since.

So **#1765–#1832 are background, not current state, and not "the rubric."**

`titoatwork`'s scoping argument, which we should take seriously:

> if the extraction pipeline is internal and still evolving, the piece that
> survives that churn is the **evaluation** — ground truth, negative controls,
> per-class recall, cross-model agreement. An extractor gets superseded by the
> next model; a test set that tells you whether an extractor works doesn't.

This agrees with our build plan phases 1 and 6 (ground truth written first; a
mechanical validator). Keep that emphasis.
