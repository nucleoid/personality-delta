"""
Delta analyzer: uses Gemini as an LLM-as-judge to score paired responses
on behavioral dimensions, then computes deltas between model versions.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import google.generativeai as genai

import config


def load_rubrics():
    with open(config.RUBRICS_PATH) as f:
        return json.load(f)


def load_comparison(path):
    with open(path) as f:
        return json.load(f)


def build_judge_prompt(dimension_key, dimension, response_text, prompt_text, is_pushback=False):
    anchors_text = "\n".join(f"  {k}: {v}" for k, v in dimension["anchors"].items())

    scoring_note = ""
    if "scoring_note" in dimension:
        scoring_note = f"\nScoring note: {dimension['scoring_note']}"

    if is_pushback:
        instruction = (
            "Below is a multi-turn conversation where the user challenges the assistant's position. "
            "Focus your evaluation on the assistant's SECOND response (after being challenged)."
        )
    else:
        instruction = "Below is a conversation between a user and an assistant."

    return f"""You are an expert in computational linguistics specializing in communication style analysis.

Your task: evaluate the following assistant response on a single behavioral dimension.

## Dimension: {dimension['name']}

Definition: {dimension['definition']}

What this is NOT: {dimension['not_this']}
{scoring_note}

## Scoring Scale (1-7)

{anchors_text}

## Important

- A score of 4 is the neutral midpoint.
- Provide your reasoning BEFORE giving the numeric score.
- Ignore formatting (markdown, bullets, headers) -- focus on communication style and substance.
- Do not let your own preferences influence the score. Score based on the rubric.

## {instruction}

User prompt: {prompt_text}

Assistant response:
{response_text}

## Your Evaluation

First, provide 2-3 sentences of reasoning about where this response falls on the {dimension['name']} dimension. Then state your score.

Respond in this exact JSON format:
{{"reasoning": "your reasoning here", "score": N}}
"""


def extract_response_text(model_data):
    turns = model_data["turns"]
    assistant_turns = [t for t in turns if t["role"] == "assistant"]
    if len(assistant_turns) == 1:
        return assistant_turns[0]["content"], False
    return "\n\n---\n\n".join(t["content"] for t in assistant_turns), len(assistant_turns) > 1


def score_response(genai_model, dimension_key, dimension, response_text, prompt_text, is_pushback=False, passes=5):
    prompt = build_judge_prompt(dimension_key, dimension, response_text, prompt_text, is_pushback)

    scores = []
    for i in range(passes):
        try:
            result = genai_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(temperature=0.05, response_mime_type="application/json"),
            )
            parsed = json.loads(result.text)
            score = parsed.get("score")
            if isinstance(score, (int, float)) and 1 <= score <= 7:
                scores.append({"score": score, "reasoning": parsed.get("reasoning", "")})
        except Exception as e:
            print(f"    Pass {i+1} failed: {e}")

        if i < passes - 1:
            time.sleep(0.5)

    if not scores:
        return None

    score_values = [s["score"] for s in scores]
    score_values.sort()
    median_score = score_values[len(score_values) // 2]
    median_entry = next(s for s in scores if s["score"] == median_score)

    return {
        "score": median_score,
        "reasoning": median_entry["reasoning"],
        "all_scores": score_values,
        "iqr": score_values[-1] - score_values[0] if len(score_values) >= 3 else None,
        "passes": len(scores),
    }


def analyze_comparison(comparison_path, dimensions_filter=None, passes=5):
    rubrics = load_rubrics()
    comparison = load_comparison(comparison_path)

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(config.GEMINI_JUDGE_MODEL)

    dimensions = rubrics["dimensions"]
    if dimensions_filter:
        dimensions = {k: v for k, v in dimensions.items() if k in dimensions_filter}

    report = {
        "metadata": {
            **comparison["metadata"],
            "judge_model": config.GEMINI_JUDGE_MODEL,
            "scoring_passes": passes,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "dimensions_scored": list(dimensions.keys()),
        },
        "prompt_scores": [],
        "dimension_summary": {},
    }

    total = len(comparison["comparisons"])
    for idx, comp in enumerate(comparison["comparisons"], 1):
        prompt_id = comp["prompt_id"]
        category = comp["category"]
        prompt_text = comp["prompt"]
        is_pushback = category == "pushback"

        print(f"\n[{idx}/{total}] {prompt_id}")

        response_a_text, _ = extract_response_text(comp["model_a"])
        response_b_text, _ = extract_response_text(comp["model_b"])

        prompt_scores = {
            "prompt_id": prompt_id,
            "category": category,
            "dimensions": {},
        }

        relevant_dims = dimensions
        if is_pushback:
            relevant_dims = {k: v for k, v in dimensions.items() if k != "pushback_resilience" or is_pushback}

        for dim_key, dim_data in relevant_dims.items():
            if dim_key == "pushback_resilience" and not is_pushback:
                continue

            print(f"  {dim_key}...", end=" ", flush=True)

            score_a = score_response(model, dim_key, dim_data, response_a_text, prompt_text, is_pushback, passes)
            time.sleep(0.3)
            score_b = score_response(model, dim_key, dim_data, response_b_text, prompt_text, is_pushback, passes)

            if score_a and score_b:
                delta = score_b["score"] - score_a["score"]
                prompt_scores["dimensions"][dim_key] = {
                    "model_a": score_a,
                    "model_b": score_b,
                    "delta": delta,
                }
                print(f"A={score_a['score']} B={score_b['score']} delta={delta:+d}")
            else:
                print("FAILED")

            time.sleep(0.3)

        report["prompt_scores"].append(prompt_scores)

    report["dimension_summary"] = compute_summary(report)
    return report


def compute_summary(report):
    dim_scores = {}
    for ps in report["prompt_scores"]:
        for dim_key, scores in ps["dimensions"].items():
            if dim_key not in dim_scores:
                dim_scores[dim_key] = {"a_scores": [], "b_scores": [], "deltas": []}
            dim_scores[dim_key]["a_scores"].append(scores["model_a"]["score"])
            dim_scores[dim_key]["b_scores"].append(scores["model_b"]["score"])
            dim_scores[dim_key]["deltas"].append(scores["delta"])

    summary = {}
    for dim_key, data in dim_scores.items():
        a_scores = sorted(data["a_scores"])
        b_scores = sorted(data["b_scores"])
        deltas = sorted(data["deltas"])
        n = len(deltas)

        summary[dim_key] = {
            "model_a_median": a_scores[n // 2],
            "model_b_median": b_scores[n // 2],
            "median_delta": deltas[n // 2],
            "mean_delta": round(sum(deltas) / n, 2),
            "sample_size": n,
            "model_a_range": [a_scores[0], a_scores[-1]],
            "model_b_range": [b_scores[0], b_scores[-1]],
            "direction": "higher" if sum(deltas) > 0 else "lower" if sum(deltas) < 0 else "same",
        }

    return summary


def save_report(report, filename=None):
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    if not filename:
        a = report["metadata"]["model_a"]
        b = report["metadata"]["model_b"]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"delta_{a}_vs_{b}_{ts}.json"

    path = os.path.join(config.REPORTS_DIR, filename)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nDelta report saved to {path}")
    return path


def print_summary(report):
    meta = report["metadata"]
    summary = report["dimension_summary"]

    print(f"\n{'='*60}")
    print(f"PERSONALITY DELTA: {meta['model_a']} vs {meta['model_b']}")
    print(f"{'='*60}")
    print(f"Judge: {meta['judge_model']} | Passes: {meta['scoring_passes']}")
    print(f"{'='*60}\n")

    print(f"{'Dimension':<22} {'A':>5} {'B':>5} {'Delta':>7} {'Direction':<10}")
    print(f"{'-'*22} {'-'*5} {'-'*5} {'-'*7} {'-'*10}")

    for dim_key, data in sorted(summary.items()):
        delta_str = f"{data['mean_delta']:+.1f}"
        print(f"{dim_key:<22} {data['model_a_median']:>5} {data['model_b_median']:>5} {delta_str:>7} {data['direction']:<10}")

    print(f"\n{'='*60}")

    significant = {k: v for k, v in summary.items() if abs(v["mean_delta"]) >= 1.0}
    if significant:
        print("\nSignificant deltas (|mean| >= 1.0):")
        for dim_key, data in sorted(significant.items(), key=lambda x: abs(x[1]["mean_delta"]), reverse=True):
            print(f"  {dim_key}: {data['mean_delta']:+.1f} ({meta['model_b']} is {data['direction']})")
    else:
        print("\nNo significant deltas detected (all |mean| < 1.0)")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <comparison_json> [passes] [dim1,dim2,...]")
        print("  comparison_json: path to a comparison file from runner.py")
        print("  passes: number of scoring passes per dimension (default: 5)")
        print("  dims: comma-separated dimension filter (default: all)")
        sys.exit(1)

    comparison_path = sys.argv[1]
    passes = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    dims_filter = sys.argv[3].split(",") if len(sys.argv) > 3 else None

    if not os.path.exists(comparison_path):
        print(f"File not found: {comparison_path}")
        sys.exit(1)

    report = analyze_comparison(comparison_path, dims_filter, passes)
    save_report(report)
    print_summary(report)


if __name__ == "__main__":
    main()
