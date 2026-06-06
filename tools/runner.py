"""
Comparison runner: sends each reference prompt to two model versions and saves
paired responses. Supports Claude (via CLI) and OpenAI-compatible models.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import config

CLAUDE_CLI = os.path.expanduser("~/.local/bin/claude")


def load_prompts():
    with open(config.PROMPTS_PATH) as f:
        return json.load(f)


def load_system_prompt():
    with open(config.SYSTEM_PROMPT_PATH) as f:
        return f.read()


OPENCLAW_PROVIDERS = {
    "gpt-5.5": "openai-codex/gpt-5.5",
    "gpt-5.4-mini": "openai-codex/gpt-5.4-mini",
    "gpt-5.2": "openai-codex/gpt-5.2",
}


def call_claude(model_id, system_prompt, prompt_text):
    env = {**os.environ, "HOME": os.path.expanduser("~")}
    result = subprocess.run(
        [
            CLAUDE_CLI, "-p",
            "--model", model_id,
            "--output-format", "text",
            "--permission-mode", "bypassPermissions",
            "--system-prompt", system_prompt,
            prompt_text,
        ],
        capture_output=True,
        text=True,
        timeout=180,
        stdin=subprocess.DEVNULL,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed (rc={result.returncode}): stdout={result.stdout[:200]} stderr={result.stderr[:300]}")
    return result.stdout.strip()


def call_openclaw(model_id, system_prompt, prompt_text):
    provider_model = OPENCLAW_PROVIDERS.get(model_id, model_id)
    full_prompt = f"System instructions: {system_prompt}\n\n{prompt_text}"
    result = subprocess.run(
        ["openclaw", "infer", "model", "run",
         "--model", provider_model,
         "--prompt", full_prompt,
         "--json"],
        capture_output=True,
        text=True,
        timeout=180,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError(f"openclaw infer failed (rc={result.returncode}): {result.stderr[:300]}")
    data = json.loads(result.stdout)
    if not data.get("ok"):
        raise RuntimeError(f"openclaw infer error: {result.stdout[:300]}")
    return data["outputs"][0]["text"].strip()


def call_model(model_id, system_prompt, prompt_text):
    if model_id in OPENCLAW_PROVIDERS:
        return call_openclaw(model_id, system_prompt, prompt_text)
    return call_claude(model_id, system_prompt, prompt_text)


def run_prompt(model_id, system_prompt, prompt_text, follow_up=None):
    first_response = call_model(model_id, system_prompt, prompt_text)

    if not follow_up:
        return {"turns": [{"role": "user", "content": prompt_text}, {"role": "assistant", "content": first_response}]}

    multi_turn_prompt = (
        f"{prompt_text}\n\n"
        f"[Assistant's previous response:]\n{first_response}\n\n"
        f"[User's follow-up:]\n{follow_up}"
    )
    second_response = call_model(model_id, system_prompt, multi_turn_prompt)

    return {
        "turns": [
            {"role": "user", "content": prompt_text},
            {"role": "assistant", "content": first_response},
            {"role": "user", "content": follow_up},
            {"role": "assistant", "content": second_response},
        ]
    }


def run_comparison(model_a_key, model_b_key, categories=None, skip=0, checkpoint_path=None):
    prompts_data = load_prompts()
    system_prompt = load_system_prompt()

    model_a = config.MODELS[model_a_key]
    model_b = config.MODELS[model_b_key]

    # Load existing checkpoint if provided
    existing = {}
    if checkpoint_path and os.path.exists(checkpoint_path):
        with open(checkpoint_path) as f:
            ckpt = json.load(f)
        existing = {c["prompt_id"]: c for c in ckpt.get("comparisons", [])}
        print(f"Resuming from checkpoint: {len(existing)} prompts already done")

    results = {
        "metadata": {
            "model_a": model_a_key,
            "model_b": model_b_key,
            "model_a_id": model_a,
            "model_b_id": model_b,
            "system_prompt_hash": hash(system_prompt) & 0xFFFFFFFF,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "comparisons": list(existing.values()),
    }

    all_categories = prompts_data["categories"]
    if categories:
        all_categories = {k: v for k, v in all_categories.items() if k in categories}

    total = sum(len(cat["prompts"]) for cat in all_categories.values())
    done = 0

    for cat_name, cat_data in all_categories.items():
        for prompt_entry in cat_data["prompts"]:
            prompt_id = prompt_entry["id"]
            prompt_text = prompt_entry["prompt"]
            follow_up = prompt_entry.get("follow_up")
            done += 1

            if done <= skip:
                print(f"[{done}/{total}] {prompt_id} ... SKIPPED (resume)")
                continue

            if prompt_id in existing:
                print(f"[{done}/{total}] {prompt_id} ... SKIPPED (checkpoint)")
                continue

            print(f"[{done}/{total}] {prompt_id} ...", end=" ", flush=True)

            t0 = time.time()
            response_a = run_prompt(model_a, system_prompt, prompt_text, follow_up)
            t_a = time.time() - t0

            t0 = time.time()
            response_b = run_prompt(model_b, system_prompt, prompt_text, follow_up)
            t_b = time.time() - t0

            comparison = {
                "prompt_id": prompt_id,
                "category": cat_name,
                "prompt": prompt_text,
                "follow_up": follow_up,
                "surfaces": prompt_entry.get("surfaces", []),
                "model_a": response_a,
                "model_b": response_b,
                "timing": {"model_a_seconds": round(t_a, 1), "model_b_seconds": round(t_b, 1)},
            }
            results["comparisons"].append(comparison)
            print(f"done ({t_a:.1f}s / {t_b:.1f}s)")

            # Incremental save after every prompt
            if checkpoint_path:
                with open(checkpoint_path, "w") as f:
                    json.dump(results, f, indent=2)

    return results


def save_results(results, filename=None):
    os.makedirs(config.BASELINES_DIR, exist_ok=True)
    if not filename:
        a = results["metadata"]["model_a"]
        b = results["metadata"]["model_b"]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"comparison_{a}_vs_{b}_{ts}.json"

    path = os.path.join(config.BASELINES_DIR, filename)
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {path}")
    return path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run personality comparison between two models")
    parser.add_argument("model_a", help=f"Model A key. Available: {', '.join(config.MODELS.keys())}")
    parser.add_argument("model_b", help=f"Model B key. Available: {', '.join(config.MODELS.keys())}")
    parser.add_argument("--categories", help="Comma-separated category filter")
    parser.add_argument("--skip", type=int, default=0, help="Skip first N prompts (legacy resume)")
    parser.add_argument("--checkpoint", help="Path to checkpoint file for incremental save/resume")
    args = parser.parse_args()

    if args.model_a not in config.MODELS:
        print(f"Unknown model: {args.model_a}. Available: {', '.join(config.MODELS.keys())}")
        sys.exit(1)
    if args.model_b not in config.MODELS:
        print(f"Unknown model: {args.model_b}. Available: {', '.join(config.MODELS.keys())}")
        sys.exit(1)

    categories = args.categories.split(",") if args.categories else None

    # Auto-generate checkpoint path if not provided
    checkpoint = args.checkpoint
    if not checkpoint:
        a, b = args.model_a, args.model_b
        cats = "-".join(categories) if categories else "all"
        checkpoint = os.path.join(config.BASELINES_DIR, f"ckpt_{a}_vs_{b}_{cats}.json")
        os.makedirs(config.BASELINES_DIR, exist_ok=True)

    print(f"Running comparison: {args.model_a} vs {args.model_b}")
    if categories:
        print(f"Categories: {', '.join(categories)}")
    print(f"Checkpoint: {checkpoint}")
    print()

    results = run_comparison(args.model_a, args.model_b, categories, args.skip, checkpoint)
    # Final save with timestamped filename
    save_results(results)


if __name__ == "__main__":
    main()
