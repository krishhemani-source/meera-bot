"""Run a note through score -> news -> draft locally, printing instead of sending to Telegram.

    python scripts/try_note.py "Customer DM'd asking why our niacinamide is 4% not 10%..."
    python scripts/try_note.py --file some_note.txt
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._env import load_env  # noqa: E402

load_env()
os.environ["SUPABASE_URL"] = ""  # never write test runs to the real database

from lib import pipeline  # noqa: E402

args = sys.argv[1:]
note = open(args[1]).read() if args[:1] == ["--file"] else " ".join(args)
if not note:
    sys.exit(__doc__)


def fake_send(chat_id, text, reply_to=None, buttons=None):
    print("\n" + "=" * 60 + "\n" + text + "\n")
    return [0]


pipeline.process_note(note, chat_id=0, source="text", send=fake_send)
