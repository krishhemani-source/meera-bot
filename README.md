# Meera — Telegram → LinkedIn draft pipeline

Meera drops a voice or text note into Telegram. The bot:

1. **Transcribes** voice notes (Gemini) and sends the transcript back.
2. **Scores** the note 0–10 with a one-line reason (Gemini Flash). Below 6 → "no draft made", and it stops.
3. **Finds a news angle**: pulls a search phrase from the note and fetches the top Google News story (no key needed).
4. **Drafts** a LinkedIn post in Meera's voice (`voice-skill.txt`). Claude drafts if `ANTHROPIC_API_KEY` is set, otherwise Gemini.
5. If the draft uses the news item, it **appends the verify flag** (headline, source, date, link, "⚠ Check this before publishing").
6. Sends the draft back as **pending**, with Approve / Reject buttons. Replying `APPROVE` or `REJECT` to the draft also works.

**It never posts to LinkedIn.** Meera copies the approved draft over and publishes it herself. That's the Cut (check 07, Judgment Protected).

```
api/webhook.py      Vercel entry point (Telegram → here)
lib/pipeline.py     the flow above
lib/prompts.py      transcription, scoring rubric, keyword, drafting prompts
lib/gemini.py       transcribe / score / keywords / draft
lib/claude.py       draft (optional)
lib/news.py         Google News RSS
lib/store.py        Supabase (optional — notes, drafts, voice skill)
voice-skill.txt     Meera's voice, from the Voice Guide
supabase/schema.sql tables
scripts/            try_note.py (local test), set_webhook.py
```

## Setup

1. `cp .env.example .env` and fill in `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, and a random `TELEGRAM_WEBHOOK_SECRET`. The Anthropic and Supabase keys are optional.
2. Try it locally with no Telegram needed:
   ```
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   .venv/bin/python scripts/try_note.py "Customer DM'd asking why our niacinamide is 4% not 10%..."
   ```
   To run the real bot from your laptop without deploying: `.venv/bin/python scripts/poll.py`, then message the bot in Telegram.
3. (Optional) Supabase: run `supabase/schema.sql` in the SQL editor, then set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`. Without it everything still works, including Approve/Reject: the decision is recorded in the Telegram chat, as a reply to the draft. You just don't get a searchable history.
4. Push to GitHub, then import the repo in Vercel. Add the same env vars under Settings → Environment Variables and deploy.
5. Connect Telegram: `.venv/bin/python scripts/set_webhook.py https://your-project.vercel.app`, which should print `"ok": true`.
6. Send `/start` to the bot. It replies with the chat id. Put that in `ALLOWED_CHAT_IDS` in Vercel and redeploy, so only Meera can use it.

For a Telegram **channel**, add the bot as a channel admin. Channel posts are handled the same way.

## Tuning

- Scoring too lenient? Tighten the rubric in `lib/prompts.py` (`SCORE_SYSTEM`) or raise `SCORE_THRESHOLD`. Test with a task reminder, which should score 3 or below. If every note passes, the rubric is too soft.
- Changing the voice: edit `voice-skill.txt`, or insert a row into the `voice_skill` table (the newest active row wins over the file).
