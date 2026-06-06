"""
SOUL.md patch generator: takes a delta report, identifies significant behavioral
shifts, and generates targeted corrective instructions for the newer model version.
"""

import json
import os
import sys
from datetime import datetime, timezone

import google.generativeai as genai

import config

DIMENSION_DESCRIPTIONS = {
    "directness": ("leads with the answer", "leads with caveats"),
    "hedge_frequency": ("more assertive, less hedging", "more hedging, less assertive"),
    "opinion_volunteering": ("more opinionated", "more neutral/option-presenting"),
    "pushback_resilience": ("holds ground when challenged", "folds when challenged"),
    "explanation_depth": ("assumes more context", "explains more basics"),
    "risk_tolerance": ("more action-biased", "more cautious"),
    "emotional_register": ("warmer, more personality", "colder, more clinical"),
    "conciseness": ("tighter, denser writing", "more verbose, more padding"),
}


def load_report(path):
    with open(path) as f:
        return json.load(f)


def identify_corrections(report, threshold=0.75):
    summary = report["dimension_summary"]
    model_a = report["metadata"]["model_a"]
    model_b = report["metadata"]["model_b"]

    corrections = []
    for dim_key, data in summary.items():
        delta = data["mean_delta"]
        if abs(delta) < threshold:
            continue

        desc = DIMENSION_DESCRIPTIONS.get(dim_key, ("higher", "lower"))
        if delta > 0:
            shift_desc = f"{model_b} scores higher on {dim_key} ({desc[0]})"
            correction_dir = "decrease"
        else:
            shift_desc = f"{model_b} scores lower on {dim_key} ({desc[1]})"
            correction_dir = "increase"

        corrections.append({
            "dimension": dim_key,
            "delta": delta,
            "model_a_median": data["model_a_median"],
            "model_b_median": data["model_b_median"],
            "shift_description": shift_desc,
            "correction_direction": correction_dir,
            "severity": "high" if abs(delta) >= 1.5 else "moderate",
        })

    corrections.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return corrections


def generate_patch(report, corrections):
    if not corrections:
        return {"instructions": [], "summary": "No significant behavioral deltas detected. No corrections needed."}

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(config.GEMINI_JUDGE_MODEL)

    model_a = report["metadata"]["model_a"]
    model_b = report["metadata"]["model_b"]

    corrections_desc = "\n".join(
        f"- {c['dimension']}: {model_b} is {c['shift_description']} (delta: {c['delta']:+.1f}, severity: {c['severity']})"
        for c in corrections
    )

    prompt = f"""You are an expert in prompt engineering and LLM behavioral tuning.

Given the following behavioral deltas between two Claude model versions, generate targeted corrective instructions to add to a SOUL.md system prompt file. The goal is to make {model_b} behave more like {model_a} on these specific dimensions.

## Reference model: {model_a}
## Target model (needs correction): {model_b}

## Detected behavioral shifts:
{corrections_desc}

## Requirements:
1. Generate one instruction per dimension that needs correction.
2. Each instruction should be a direct behavioral directive, not a description of the problem.
3. Instructions should be specific and actionable, not vague ("be more direct" is too vague).
4. Use concrete behavioral anchors ("lead with the answer in the first sentence" is specific).
5. Do NOT reference model version numbers in the instructions -- they should be timeless.
6. Keep each instruction to 1-2 sentences max.
7. Order by severity (most impactful first).

Respond in this exact JSON format:
{{
  "instructions": [
    {{
      "dimension": "dimension_name",
      "instruction": "the corrective instruction text",
      "confidence": 0.0-1.0
    }}
  ],
  "summary": "1-2 sentence summary of the overall behavioral correction needed"
}}
"""

    result = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.3, response_mime_type="application/json"),
    )

    return json.loads(result.text)


def format_soul_patch(patch, report):
    model_a = report["metadata"]["model_a"]
    model_b = report["metadata"]["model_b"]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"## Behavioral Corrections ({model_b} toward {model_a} disposition)",
        f"## Generated: {ts}",
        "",
        patch["summary"],
        "",
    ]

    for item in patch["instructions"]:
        confidence_marker = ""
        if item["confidence"] < 0.6:
            confidence_marker = " [low confidence]"
        lines.append(f"- {item['instruction']}{confidence_marker}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <delta_report_json> [threshold]")
        print("  delta_report_json: path to a delta report from analyzer.py")
        print("  threshold: minimum |mean_delta| to generate a correction (default: 0.75)")
        sys.exit(1)

    report_path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.75

    if not os.path.exists(report_path):
        print(f"File not found: {report_path}")
        sys.exit(1)

    report = load_report(report_path)
    corrections = identify_corrections(report, threshold)

    if not corrections:
        print("No significant behavioral deltas detected. No corrections needed.")
        return

    print(f"Found {len(corrections)} dimensions needing correction:")
    for c in corrections:
        print(f"  {c['dimension']}: delta {c['delta']:+.1f} ({c['severity']})")

    print("\nGenerating SOUL.md patch...")
    patch = generate_patch(report, corrections)

    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    model_b = report["metadata"]["model_b"]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    patch_json_path = os.path.join(config.REPORTS_DIR, f"patch_{model_b}_{ts}.json")
    with open(patch_json_path, "w") as f:
        json.dump(patch, f, indent=2)
    print(f"Patch JSON saved to {patch_json_path}")

    patch_text = format_soul_patch(patch, report)
    patch_md_path = os.path.join(config.REPORTS_DIR, f"patch_{model_b}_{ts}.md")
    with open(patch_md_path, "w") as f:
        f.write(patch_text)
    print(f"Patch markdown saved to {patch_md_path}")

    print(f"\n{'='*60}")
    print("GENERATED SOUL.MD PATCH")
    print(f"{'='*60}\n")
    print(patch_text)


if __name__ == "__main__":
    main()
