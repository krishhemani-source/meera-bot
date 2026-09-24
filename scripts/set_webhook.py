"""Point Telegram at your Vercel deployment:  python scripts/set_webhook.py https://your-project.vercel.app"""
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._env import load_env  # noqa: E402

load_env()
url = sys.argv[1].rstrip("/") + "/api/webhook"
r = requests.post(
    f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/setWebhook",
    json={
        "url": url,
        "secret_token": os.environ.get("TELEGRAM_WEBHOOK_SECRET") or None,
        "allowed_updates": ["message", "channel_post", "callback_query"],
        "drop_pending_updates": True,
    },
    timeout=30,
)
print(r.json())
