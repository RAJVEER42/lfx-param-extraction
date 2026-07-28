#!/usr/bin/env python3
"""Run a prompt version against the challenge snippets and save raw output.

Design constraints, each traceable to a finding:

1. RAW OUTPUT IS SAVED BEFORE ANY PARSING. The response text is written to disk
   verbatim, and this script never parses YAML. Parsing lives in a separate
   step so that a parse bug can never silently launder a bad response into a
   clean-looking result.

2. finish_reason != "stop" IS A RUN FAILURE, NOT AN EMPTY RESULT.
   All candidate models are reasoning models. A model that exhausts max_tokens
   on reasoning returns an EMPTY content string. Parsed naively that reads as
   "the model found no parameters" -- which is exactly the correct answer for
   snippet 2.1. Truncation would therefore masquerade as the very behaviour we
   are trying to measure. See reference/models.md section 3.

3. N RUNS PER CELL. temperature=0 is not determinism: provider batching and MoE
   routing vary between calls. Agreement across runs is measured, not assumed.

4. FULL PROVENANCE. Prompt hashes, exact token counts from the API's own usage
   field, model id as echoed by the provider, and timestamps -- so a number in
   the writeup can always be traced to a specific response.

No secret is read from, or written to, this repository. Credentials come from
the provider SDK's own store (HF: ~/.cache/huggingface/token) or the
environment (GEMINI_API_KEY).

Usage:
    python3 scripts/run_extraction.py --prompt v1 --model deepseek-ai/DeepSeek-V4-Pro
    python3 scripts/run_extraction.py --prompt v1 --model gemini-2.5-pro --provider gemini
    python3 scripts/run_extraction.py --prompt v1 --model ... --runs 3 --dry-run
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
SNIPPETS = {
    "priv_19_3_1": "snippets/priv_19_3_1.txt",
    "priv_2_1": "snippets/priv_2_1.txt",
    # Derived, not spec text. One clause deleted for the minimal-edit pair
    # experiment; see analysis/exp1_prereg.md.
    "priv_19_3_1_nodiscovery": "snippets/priv_19_3_1_nodiscovery.txt",
}
SOURCE_LABEL = {
    "priv_19_3_1": "RISC-V Privileged ISA Specification, section 19.3.1",
    "priv_2_1": "RISC-V Privileged ISA Specification, section 2.1",
    # Same label as the unedited passage on purpose: the label must not be the
    # variable that differs between arms.
    "priv_19_3_1_nodiscovery": "RISC-V Privileged ISA Specification, section 19.3.1",
}
HEADER_PREFIXES = ("Source:", "Provided ")


def load_dotenv() -> None:
    """Load KEY=VALUE pairs from a gitignored .env, without overriding the shell.

    Keeps credentials out of both the repository and the command line. .env is
    listed in .gitignore; nothing here is ever committed.
    """
    p = REPO / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def slug(model_id: str) -> str:
    """Filesystem-safe directory name for a model."""
    return model_id.split("/")[-1].lower().replace(".", "-").replace(":", "-")


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def snippet_body(key: str) -> str:
    """Snippet text with our provenance header stripped.

    The header lines were added by us when storing the snippet; they are not
    spec text and must not be sent to the model.
    """
    p = REPO / SNIPPETS[key]
    lines = p.read_text(encoding="utf-8").splitlines()
    return "\n".join(ln for ln in lines if not ln.startswith(HEADER_PREFIXES)).strip()


def load_prompt(version: str) -> tuple[str, str]:
    d = REPO / "prompts" / version
    system = (d / "system.md").read_text(encoding="utf-8").strip()
    user_t = (d / "user_template.md").read_text(encoding="utf-8").strip()
    return system, user_t


# --- providers -------------------------------------------------------------
# Each returns a normalised dict. Provider-specific field names are mapped
# here so the rest of the script stays provider-agnostic.


def call_hf(model: str, system: str, user: str, temperature: float, max_tokens: int) -> dict:
    from huggingface_hub import InferenceClient

    client = InferenceClient(model=model)
    t0 = time.monotonic()
    r = client.chat_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    elapsed = time.monotonic() - t0
    choice = r.choices[0]
    msg = choice.message
    reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
    return {
        "content": msg.content or "",
        "reasoning_chars": len(reasoning) if reasoning else 0,
        "finish_reason": choice.finish_reason,
        "prompt_tokens": r.usage.prompt_tokens,
        "completion_tokens": r.usage.completion_tokens,
        "model_echoed": r.model,
        "elapsed_s": round(elapsed, 2),
    }


def call_gemini(model: str, system: str, user: str, temperature: float, max_tokens: int) -> dict:
    from google import genai
    from google.genai import types

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit(
            "GEMINI_API_KEY not set. Get a free key at https://aistudio.google.com/apikey\n"
            "Then either add it to a gitignored .env, or export it in your shell.\n"
            "Do not hardcode it in this repository."
        )
    client = genai.Client(api_key=key)
    t0 = time.monotonic()
    r = client.models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )
    elapsed = time.monotonic() - t0
    cand = (r.candidates or [None])[0]
    um = r.usage_metadata
    # Gemini reports thinking tokens separately when a thinking model is used.
    thoughts = getattr(um, "thoughts_token_count", None) or 0
    return {
        "content": (r.text or ""),
        "reasoning_chars": 0,
        "reasoning_tokens": thoughts,
        # Map Gemini's STOP/MAX_TOKENS onto the same vocabulary as HF, so the
        # truncation check below is provider-independent.
        "finish_reason": (
            "stop" if str(getattr(cand, "finish_reason", "")).endswith("STOP") else
            "length" if str(getattr(cand, "finish_reason", "")).endswith("MAX_TOKENS") else
            str(getattr(cand, "finish_reason", "unknown"))
        ),
        "prompt_tokens": getattr(um, "prompt_token_count", None),
        "completion_tokens": getattr(um, "candidates_token_count", None),
        "model_echoed": getattr(r, "model_version", model),
        "elapsed_s": round(elapsed, 2),
    }


PROVIDERS = {"hf": call_hf, "gemini": call_gemini}


# --- main ------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prompt", default="v1", help="prompt version directory under prompts/")
    ap.add_argument("--model", required=True)
    ap.add_argument("--provider", default="hf", choices=sorted(PROVIDERS))
    ap.add_argument("--runs", type=int, default=3, help="N runs per snippet")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--snippet", default="all", help="snippet key, or 'all'")
    ap.add_argument("--dry-run", action="store_true", help="render prompts, make no calls")
    args = ap.parse_args()

    load_dotenv()

    system, user_t = load_prompt(args.prompt)
    keys = list(SNIPPETS) if args.snippet == "all" else [args.snippet]
    outdir = REPO / "results" / slug(args.model) / args.prompt
    # Only create the output directory when something will be written. A dry run
    # used to leave an empty results/<model>/ behind, which is confusing clutter
    # for anyone reading the repo.
    if not args.dry_run:
        outdir.mkdir(parents=True, exist_ok=True)

    fn = PROVIDERS[args.provider]
    failures, ok = 0, 0

    for key in keys:
        user = user_t.format(source=SOURCE_LABEL[key], snippet=snippet_body(key))

        if args.dry_run:
            print(f"--- {key} ---\n[SYSTEM]\n{system}\n\n[USER]\n{user}\n")
            continue

        for i in range(1, args.runs + 1):
            stem = f"{key}_run{i}"
            print(f"  {args.model} / {args.prompt} / {stem} ... ", end="", flush=True)
            record = {
                "schema": "extraction_run/1",
                "timestamp_utc": now_iso(),
                "prompt_version": args.prompt,
                "snippet": key,
                "run_index": i,
                "model_requested": args.model,
                "provider": args.provider,
                "params": {"temperature": args.temperature, "max_tokens": args.max_tokens},
                "prompt_sha256_16": {"system": sha256(system), "user": sha256(user)},
                "name_list_supplied": False,  # unlike Part I; see reference/prior-art.md
            }
            try:
                res = fn(args.model, system, user, args.temperature, args.max_tokens)
                record.update(res)
                # Finding-driven check: truncation is a run failure, never an
                # empty extraction. See module docstring point 2.
                if res["finish_reason"] != "stop":
                    record["status"] = "truncated"
                    failures += 1
                    print(f"TRUNCATED (finish_reason={res['finish_reason']}) -- NOT a valid empty result")
                else:
                    record["status"] = "ok"
                    ok += 1
                    print(f"ok  {res['completion_tokens']}ct  {res['elapsed_s']}s  {len(res['content'])} chars")
            except Exception as e:  # noqa: BLE001 - record and continue
                record["status"] = "error"
                record["error"] = f"{type(e).__name__}: {e}"
                failures += 1
                print(f"ERROR {type(e).__name__}: {str(e)[:120]}")

            (outdir / f"{stem}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            # Raw content also written standalone, byte-for-byte as returned,
            # so a reviewer can read exactly what the model said.
            (outdir / f"{stem}.raw.txt").write_text(record.get("content", ""), encoding="utf-8")

    if not args.dry_run:
        print(f"\n{ok} ok, {failures} failed -> {outdir.relative_to(REPO)}")
        if failures:
            print("Failed runs are recorded with status != 'ok' and must not be")
            print("treated as empty extractions.")
    return 1 if failures and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
