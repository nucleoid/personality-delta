"""
Merge two partial comparison JSON files into one complete comparison.
Deduplicates by prompt_id, takes first occurrence if duplicated.
"""

import json
import os
import sys
from datetime import datetime, timezone

import config


def merge_comparisons(file_a, file_b, output=None):
    with open(file_a) as f:
        data_a = json.load(f)
    with open(file_b) as f:
        data_b = json.load(f)

    seen = {}
    for comp in data_a["comparisons"] + data_b["comparisons"]:
        pid = comp["prompt_id"]
        if pid not in seen:
            seen[pid] = comp

    # Sort by prompt_id to keep canonical order
    def sort_key(pid):
        cat, num = pid.rsplit("-", 1)
        cat_order = ["tactical", "judgment", "architecture", "research", "creative", "pushback"]
        return (cat_order.index(cat) if cat in cat_order else 99, int(num))

    merged_comparisons = sorted(seen.values(), key=lambda c: sort_key(c["prompt_id"]))

    merged = {
        "metadata": {
            **data_a["metadata"],
            "merged_from": [file_a, file_b],
            "merge_timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "comparisons": merged_comparisons,
    }

    if not output:
        a = merged["metadata"]["model_a"]
        b = merged["metadata"]["model_b"]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output = os.path.join(config.BASELINES_DIR, f"comparison_{a}_vs_{b}_{ts}.json")

    os.makedirs(config.BASELINES_DIR, exist_ok=True)
    with open(output, "w") as f:
        json.dump(merged, f, indent=2)

    total = len(merged_comparisons)
    print(f"Merged {len(data_a['comparisons'])} + {len(data_b['comparisons'])} comparisons -> {total} unique")
    print(f"Saved to {output}")
    return output


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <file_a.json> <file_b.json> [output.json]")
        sys.exit(1)
    output = sys.argv[3] if len(sys.argv) > 3 else None
    merge_comparisons(sys.argv[1], sys.argv[2], output)
