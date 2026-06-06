# Personality Delta

Behavioral comparison harness that measures personality drift between LLM model versions and generates corrective system prompt instructions to preserve a target disposition.

**Live results:** [personality-delta.pragmaticcoder.com](https://personality-delta.pragmaticcoder.com)

## What it does

1. Runs 30 reference prompts on two model versions with the same system prompt
2. Scores each response on 8 behavioral dimensions using an independent LLM judge
3. Computes per-dimension deltas to identify significant personality shifts
4. Generates targeted system prompt corrections to close the gap
5. Validates corrections by re-running and re-scoring

## Key findings (June 2026)

Reference model: **Claude Opus 4.6**

| Comparison | Significant deltas | Notes |
|---|---|---|
| vs Opus 4.7 | None | Virtually identical under same system prompt |
| vs Opus 4.8 | risk_tolerance (-1.1) | More cautious recommendations |
| vs GPT 5.5 | risk_tolerance (-1.4) | Most cautious; also trends toward more hedging, less opinionated |
| vs GPT 5.4 Mini | None | Trends toward generic assistant personality but below threshold |

**Risk tolerance is the primary personality differentiator.** System prompts handle most intra-family version drift. Cross-vendor gaps are wider but correctable with targeted instructions.

## Behavioral dimensions

| Dimension | Description | Opus 4.6 baseline |
|---|---|---|
| Directness | Answer-first vs caveat-first | 6/7 |
| Hedge frequency | Density of performative uncertainty | 1/7 (low) |
| Opinion volunteering | Offers opinions without being asked | 7/7 |
| Pushback resilience | Holds ground when challenged | 6/7 |
| Explanation depth | How much it explains things the user already knows | 4/7 |
| Risk tolerance | Action-biased vs cautious in recommendations | 5/7 |
| Emotional register | Warm/conversational vs clinical/formal | 5/7 |
| Conciseness | Information density per word | 6/7 |

## Project structure

```
personality-delta/
  index.html, styles.css, main.js   # Results website
  assets/data.json                   # Visualization data
  tools/                             # Python tooling
    runner.py                        # Comparison runner (Claude CLI + OpenAI Codex)
    analyzer.py                      # LLM-as-judge delta scorer (Gemini)
    generator.py                     # SOUL.md patch generation
    validate.py                      # Correction validation loop
    merge.py                         # Merge partial comparison files
    config.py                        # Configuration
    requirements.txt                 # Python dependencies
  prompts/prompts.json               # 30 reference prompts (6 categories)
  rubrics/dimensions.json            # 8 dimension scoring rubrics
  data/
    baselines/                       # Raw model response pairs
    reports/                         # Delta reports and correction patches
  research/                          # Background research on LLM-as-judge methodology
```

## Running your own comparison

### Prerequisites

- Python 3.11+
- Claude Code CLI (`claude -p`) for Claude models
- `openclaw infer` for OpenAI/Codex models
- Gemini API key for the judge model

### Setup

```bash
cd tools
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set environment variables (or create a `.env` file):
```
GEMINI_API_KEY=your-key
SYSTEM_PROMPT_PATH=path/to/your/system-prompt.md
```

### Run a comparison

```bash
python runner.py opus-4.6 opus-4.7
```

Responses are saved to `data/baselines/` with incremental checkpointing.

### Score the comparison

```bash
python analyzer.py data/baselines/comparison_opus-4.6_vs_opus-4.7.json 5
```

The `5` is the number of scoring passes per dimension (higher = more reliable).

### Generate a correction patch

```bash
python generator.py data/reports/delta_opus-4.6_vs_gpt-5.5.json 0.75
```

### Validate corrections

```bash
python validate.py data/reports/delta_opus-4.6_vs_gpt-5.5.json data/reports/patch_gpt-5.5_v2.json 5
```

## Methodology

- **Judge model:** Gemini 2.5 Flash (non-Anthropic to avoid self-bias when scoring Anthropic outputs)
- **Scoring:** Rubric-grounded, chain-of-thought evaluation on a 1-7 scale with concrete behavioral anchors
- **Reliability:** 5-pass scoring at temperature 0.05, median aggregation, JSON-mode output
- **Significance threshold:** |mean delta| >= 1.0 across the 30-prompt set
- **Controls:** Same system prompt for all models, temperature 0 for response generation

See `research/` for detailed literature review on LLM-as-judge methodology and Claude version behavioral differences.

## License

MIT
