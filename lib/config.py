import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def env(name, default=""):
    """Blank values (e.g. an empty Vercel env var) fall back to the default."""
    return os.environ.get(name, "").strip() or default


TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET")
# Comma-separated chat ids allowed to use the bot (Meera's DM / channel). Empty = allow all.
ALLOWED_CHAT_IDS = {c.strip() for c in env("ALLOWED_CHAT_IDS").split(",") if c.strip()}

GEMINI_API_KEY = env("GEMINI_API_KEY")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-3.6-flash")

# If set, drafts are written by Claude (holds voice better); otherwise Gemini drafts.
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
CLAUDE_MODEL = env("CLAUDE_MODEL", "claude-opus-5")

SUPABASE_URL = env("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_KEY = env("SUPABASE_SERVICE_KEY")

SCORE_THRESHOLD = int(env("SCORE_THRESHOLD", "6"))
