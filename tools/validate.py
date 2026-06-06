"""
Validation loop: re-runs prompts on the target model with corrective SOUL.md
instructions applied, then scores again to measure whether corrections closed the gap.
"""

import json
import os
import sys
from datetime import datetime, timezone

import google.generativeai as genai

import config
from runner import run_prompt, load_prompts
from analyzer import score_response, load_rubrics, extract_response_text


def load_patch(path):
    with open(path) as f:
        return json.load(f)


def build_corrected_system_prompt(patch):
    with open(config.SYSTEM_PROMPT_PATH) as f:
        base_prompt = f.read()

    correction_block = "\n\n## Behavioral Guidelines\n\n"
    for item in patch["instructions"]:
        correction_block += f"- {item['instruction']}\n"

    return base_prompt + correction_block


def run_validation(original_report_path, patch_path, passes=5):
    original_report = json.load(open(original_report_path))
    patch = load_patch(patch_path)

    model_b_key = original_report["metadata"]["model_b"]
    model_b = config.MODELS[model_b_key]

    corrected_prompt = build_corrected_system_prompt(patch)

    prompts_data = load_prompts()
    rubrics = load_rubrics()
    dimensions = rubrics["dimensions"]

    genai.configure(api_key=config.GEMINI_API_KEY)
    judge = genai.GenerativeModel(config.GEMINI_JUDGE_MODEL)

    all_prompts = []
    for cat_data in prompts_data["categories"].values():
        all_prompts.extend(cat_data["prompts"])

    validation = {
        "metadata": {
            "model": model_b_key,
            "model_id": model_b,
            "original_report": original_report_path,
            "patch_file": patch_path,
            "scoring_passes": passes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "prompt_scores": [],
    }

    for idx, prompt_entry in enumerate(all_prompts, 1):
        prompt_id = prompt_entry["id"]
        prompt_text = prompt_entry["prompt"]
        follow_up = prompt_entry.get("follow_up")
        category = prompt_id.split("-")[0]
        is_pushback = category == "pushback"

        print(f"\n[{idx}/{len(all_prompts)}] {prompt_id}")

        response = run_prompt(model_b, corrected_prompt, prompt_text, follow_up)
        response_text, _ = extract_response_text(response)

        prompt_scores = {"prompt_id": prompt_id, "category": category, "dimensions": {}}

        for dim_key, dim_data in dimensions.items():
            if dim_key == "pushback_resilience" and not is_pushback:
                continue

            print(f"  {dim_key}...", end=" ", flush=True)
            result = score_response(judge, dim_key, dim_data, response_text, prompt_text, is_pushback, passes)
            if result:
                prompt_scores["dimensions"][dim_key] = {"corrected": result}
                print(f"score={result['score']}")
            else:
                print("FAILED")

        validation["prompt_scores"].append(prompt_scores)

    validation["dimension_summary"] = compute_corrected_summary(validation, original_report)
    return validation


def compute_corrected_summary(validation, original_report):
    orig_summary = original_report["dimension_summary"]

    corrected_scores = {}
    for ps in validation["prompt_scores"]:
        for dim_key, scores in ps["dimensions"].items():
            if dim_key not in corrected_scores:
                corrected_scores[dim_key] = []
            corrected_scores[dim_key].append(scores["corrected"]["score"])

    summary = {}
    for dim_key, scores in corrected_scores.items():
        scores.sort()
        n = len(scores)
        corrected_median = scores[n // 2]

        orig = orig_summary.get(dim_key, {})
        target_median = orig.get("model_a_median", corrected_median)
        uncorrected_median = orig.get("model_b_median", corrected_median)

        original_gap = uncorrected_median - target_median
        remaining_gap = corrected_median - target_median
        gap_closed = original_gap - remaining_gap if original_gap != 0 else 0
        pct_closed = round((gap_closed / original_gap) * 100) if original_gap != 0 else 0

        summary[dim_key] = {
            "target_median": target_median,
            "uncorrected_median": uncorrected_median,
            "corrected_median": corrected_median,
            "original_gap": original_gap,
            "remaining_gap": remaining_gap,
            "pct_gap_closed": pct_closed,
        }

    return summary


def print_validation_summary(validation):
    summary = validation["dimension_summary"]
    model = validation["metadata"]["model"]

    print(f"\n{'='*70}")
    print(f"VALIDATION RESULTS: {model} with corrections applied")
    print(f"{'='*70}\n")

    print(f"{'Dimension':<22} {'Target':>7} {'Before':>7} {'After':>7} {'Gap Closed':>10}")
    print(f"{'-'*22} {'-'*7} {'-'*7} {'-'*7} {'-'*10}")

    for dim_key, data in sorted(summary.items()):
        pct = f"{data['pct_gap_closed']}%"
        print(f"{dim_key:<22} {data['target_median']:>7} {data['uncorrected_median']:>7} {data['corrected_median']:>7} {pct:>10}")

    total_original = sum(abs(d["original_gap"]) for d in summary.values())
    total_remaining = sum(abs(d["remaining_gap"]) for d in summary.values())
    if total_original > 0:
        overall_pct = round((1 - total_remaining / total_original) * 100)
        print(f"\nOverall gap closed: {overall_pct}%")


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <delta_report_json> <patch_json> [passes]")
        sys.exit(1)

    report_path = sys.argv[1]
    patch_path = sys.argv[2]
    passes = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    validation = run_validation(report_path, patch_path, passes)

    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    model = validation["metadata"]["model"]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = os.path.join(config.REPORTS_DIR, f"validation_{model}_{ts}.json")
    with open(path, "w") as f:
        json.dump(validation, f, indent=2)
    print(f"\nValidation saved to {path}")

    print_validation_summary(validation)


if __name__ == "__main__":
    main()
