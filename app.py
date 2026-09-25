"""Vercel entry point. Telegram POSTs every update to /api/webhook.

Plain WSGI app (no framework) — Vercel loads the top-level `app`.
"""
import json
import sys
import traceback

try:
    from lib import config, pipeline
    IMPORT_ERROR = None
except Exception:  # surface startup errors on GET instead of a bare 500
    IMPORT_ERROR = traceback.format_exc()


def app(environ, start_response):
    def reply(status, body):
        data = json.dumps(body).encode()
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(data)))])
        return [data]

    if IMPORT_ERROR:
        print(IMPORT_ERROR, file=sys.stderr)  # visible in Vercel → Logs
        return reply("500 Internal Server Error", {"ok": False, "error": "startup failed, see Vercel logs"})
    if environ.get("REQUEST_METHOD") != "POST":
        # Which settings are present (never their values) — for debugging deploys.
        return reply("200 OK", {"ok": True, "service": "meera-bot", "configured": {
            "TELEGRAM_BOT_TOKEN": bool(config.TELEGRAM_BOT_TOKEN),
            "GEMINI_API_KEY": bool(config.GEMINI_API_KEY),
            "TELEGRAM_WEBHOOK_SECRET": bool(config.TELEGRAM_WEBHOOK_SECRET),
            "ALLOWED_CHAT_IDS": len(config.ALLOWED_CHAT_IDS),
            "GEMINI_MODEL": config.GEMINI_MODEL,
        }})

    secret = environ.get("HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN", "")
    if config.TELEGRAM_WEBHOOK_SECRET and secret != config.TELEGRAM_WEBHOOK_SECRET:
        return reply("401 Unauthorized", {"ok": False})

    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        update = json.loads(environ["wsgi.input"].read(length) or b"{}")
        pipeline.handle_update(update)
    except Exception:
        traceback.print_exc()
    # Always 200 so Telegram doesn't retry-loop a note that errored.
    return reply("200 OK", {"ok": True})
