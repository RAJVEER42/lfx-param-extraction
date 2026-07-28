# prompts/exp1

Byte-identical copy of `prompts/v2/`. It exists only so experiment 1's runs land
in `results/*/exp1/` without overwriting the v2 results, since the runner derives
the output directory from the prompt version.

Do not edit. If v2 changes, this copy is stale and the comparison is void.
Verify with:

    shasum -a 256 prompts/v2/system.md prompts/exp1/system.md
