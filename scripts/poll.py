"""Run the bot from your own machine (no Vercel, no webhook) — handy for testing.

    python scripts/poll.py

Stops any webhook first, since Telegram allows only one of webhook / polling at a time.
Re-run scripts/set_webhook.py after you deploy to Vercel.
"""
import os
import sys
import traceback

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._env import load_env  # noqa: E402

load_env()
from lib import config, pipeline  # noqa: E402

API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
requests.post(f"{API}/deleteWebhook", timeout=30)
print("Polling Telegram. Send the bot a note. Ctrl+C to stop.", flush=True)

offset = None
while True:
    try:
        r = requests.get(f"{API}/getUpdates", timeout=60, params={
            "timeout": 50, "offset": offset,
            "allowed_updates": '["message","channel_post","callback_query"]',
        }).json()
        for update in r.get("result", []):
            offset = update["update_id"] + 1
            kind = next((k for k in update if k != "update_id"), "?")
            print(f"update {update['update_id']}: {kind}", flush=True)
            pipeline.handle_update(update)
    except KeyboardInterrupt:
        break
    except Exception:
        traceback.print_exc()
