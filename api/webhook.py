"""Vercel serverless entry point. Telegram POSTs every update here."""
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import config, pipeline  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._reply(200, {"ok": True, "service": "meera-bot"})

    def do_POST(self):
        secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if config.TELEGRAM_WEBHOOK_SECRET and secret != config.TELEGRAM_WEBHOOK_SECRET:
            return self._reply(401, {"ok": False})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            update = json.loads(self.rfile.read(length) or b"{}")
            pipeline.handle_update(update)
        except Exception:
            traceback.print_exc()
        # Always 200 so Telegram doesn't retry-loop a note that errored.
        self._reply(200, {"ok": True})

    def _reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
