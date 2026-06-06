import os
from dotenv import load_dotenv

load_dotenv()

MODELS = {
    "opus-4.6": "claude-opus-4-6",
    "opus-4.7": "claude-opus-4-7",
    "opus-4.8": "claude-opus-4-8",
    "sonnet-4.6": "claude-sonnet-4-6",
    "sonnet-4.7": "claude-sonnet-4",
    "gpt-5.5": "gpt-5.5",
    "gpt-5.4-mini": "gpt-5.4-mini",
}

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_JUDGE_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT_PATH = os.getenv("SYSTEM_PROMPT_PATH", "system-prompt.md")

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
PROMPTS_PATH = os.path.join(ROOT_DIR, "prompts", "prompts.json")
RUBRICS_PATH = os.path.join(ROOT_DIR, "rubrics", "dimensions.json")
BASELINES_DIR = os.path.join(ROOT_DIR, "data", "baselines")
REPORTS_DIR = os.path.join(ROOT_DIR, "data", "reports")
