# prompts/v3 — the two-part fix

Minimal diff from `prompts/v2/`: **only the T3 section changes.** Everything else,
including the worked example and every other rule, is byte-identical, so the
comparison has one variable.

Motivated by `analysis/exp1_results.md`, which showed the fix has to do two things,
not one:

1. **Exclude** execution-environment discoverability, which produced 5 of 6 false
   positives in exp1 Arm A.
2. **Supply** the correct test, because exp1 Arm B showed that removing the wrong
   reason *without* giving the right one destroys the true positive: recall fell
   from 6 of 6 to 2 of 6.

A prompt that only did (1) would be expected to reproduce Arm B's collapse. That
is prediction Z2 in `analysis/exp2_prereg.md`.

Not part of the v1 → v2 comparison. Results stay in their own file.
