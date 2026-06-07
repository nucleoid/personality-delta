# Data Schema

## Comparison files (`baselines/comparison_*.json`)

Raw response pairs from two model versions.

```json
{
  "metadata": {
    "model_a": "opus-4.6",          // reference model key
    "model_b": "gpt-5.5",           // comparison model key
    "model_a_id": "claude-opus-4-6", // API model identifier
    "model_b_id": "gpt-5.5",
    "system_prompt_hash": 12345,     // hash of system prompt used
    "timestamp": "2026-06-06T03:03:34+00:00"
  },
  "comparisons": [
    {
      "prompt_id": "tactical-01",
      "category": "tactical",
      "prompt": "the prompt text...",
      "follow_up": null,             // multi-turn follow-up (pushback only)
      "surfaces": ["directness", "risk_tolerance"],
      "model_a": {
        "turns": [
          {"role": "user", "content": "..."},
          {"role": "assistant", "content": "model A response"}
        ]
      },
      "model_b": {
        "turns": [
          {"role": "user", "content": "..."},
          {"role": "assistant", "content": "model B response"}
        ]
      },
      "timing": {
        "model_a_seconds": 18.9,
        "model_b_seconds": 17.2
      }
    }
  ]
}
```

## Delta reports (`reports/delta_*.json`)

Behavioral dimension scores and deltas from the LLM judge.

```json
{
  "metadata": {
    "model_a": "opus-4.6",
    "model_b": "gpt-5.5",
    "judge_model": "gemini-2.5-flash",
    "scoring_passes": 5,
    "analysis_timestamp": "2026-06-06T10:56:10+00:00",
    "dimensions_scored": ["directness", "hedge_frequency", ...]
  },
  "prompt_scores": [
    {
      "prompt_id": "tactical-01",
      "category": "tactical",
      "dimensions": {
        "directness": {
          "model_a": {
            "score": 6,               // median of 5 passes
            "reasoning": "judge reasoning text",
            "all_scores": [5, 6, 6, 6, 7],
            "iqr": 2,                  // interquartile range
            "passes": 5
          },
          "model_b": {
            "score": 2,
            "reasoning": "...",
            "all_scores": [2, 2, 2, 3, 3],
            "iqr": 1,
            "passes": 5
          },
          "delta": -4                  // model_b - model_a
        }
      }
    }
  ],
  "dimension_summary": {
    "directness": {
      "model_a_median": 6,
      "model_b_median": 6,
      "median_delta": 0,
      "mean_delta": 0.1,
      "sample_size": 30,
      "model_a_range": [2, 7],
      "model_b_range": [2, 7],
      "direction": "higher"           // model_b trend vs model_a
    }
  }
}
```

## Correction patches (`reports/patch_*.json`)

System prompt corrections to close behavioral gaps.

```json
{
  "instructions": [
    {
      "dimension": "risk_tolerance",
      "instruction": "corrective instruction text",
      "confidence": 0.95             // 0-1, generator confidence
    }
  ],
  "summary": "one-line summary of the correction"
}
```

## Website data (`assets/data.json`)

Simplified format for the visualization dashboard, keyed by comparison identifier.

```json
{
  "4.7": {
    "model_b": "opus-4.7",
    "summary": {
      "directness": {
        "model_a_median": 6,
        "model_b_median": 6,
        "mean_delta": -0.03,
        ...
      }
    },
    "prompt_scores": [
      {
        "prompt_id": "tactical-01",
        "category": "tactical",
        "dimensions": {
          "directness": {"a": 6, "b": 6, "delta": 0}
        }
      }
    ]
  }
}
```

## Significance threshold

A dimension delta is considered **significant** when |mean_delta| >= 1.0 across the 30-prompt set. This threshold was chosen empirically: deltas below 1.0 are within the noise range of the 5-pass median scoring methodology.
