"""Meera's content pipeline.

voice/text note -> transcribe -> score 0-10 -> (>= threshold) news angle -> draft in her voice
-> sent back to Telegram as PENDING -> Meera replies APPROVE / REJECT.

Nothing is ever posted to LinkedIn. Meera publishes herself (check 07, Judgment Protected).
"""
import re
import traceback
from datetime import datetime, timezone

from . import claude, config, gemini, news, prompts, store, telegram

APPROVE_WORDS = {"approve", "approved", "yes", "ok"}
REJECT_WORDS = {"reject", "rejected", "no"}

HELP = (
    "Send me a voice note or a text note.\n\n"
    "I'll transcribe it, score it 0–10, and if it scores {t} or above I'll draft a LinkedIn post "
    "in your voice, with a current news angle from Google News. Reply APPROVE or REJECT to a draft (or use the buttons).\n\n"
    "/news <topic> — latest Google News headlines on any topic.\n\n"
    "Nothing is ever posted for you. You copy the approved draft into LinkedIn yourself.\n\n"
    "This chat's id: {chat_id}"
)


def voice_skill():
    try:
        from_db = store.active_voice_skill()
        if from_db:
            return from_db
    except Exception:
        traceback.print_exc()
    return (config.ROOT / "voice-skill.txt").read_text(encoding="utf-8")


def verify_flag(item):
    line = "─" * 33
    return (
        f"{line}\n"
        f"NEWS SOURCE: {item['headline']}\n"
        f"FROM: {item['source']} · {item['date']}\n"
        f"LINK: {item['url']}\n"
        f"⚠ Check this before publishing — you are the author of this claim\n"
        f"{line}"
    )


def write_draft(note, angle, stories):
    """Returns (post_text, story_used_or_None, model_name)."""
    system = prompts.DRAFT_SYSTEM.format(voice_skill=voice_skill())
    if stories:
        listing = "\n\n".join(
            f"[{n}] Headline: {s['headline']}\nPublication: {s['source']}\nDate: {s['date']}\nSummary: {s['summary']}"
            for n, s in enumerate(stories, 1))
        user = prompts.DRAFT_USER_WITH_NEWS.format(note=note, angle=angle or "-", news=listing)
    else:
        user = prompts.DRAFT_USER_NO_NEWS.format(note=note, angle=angle or "-")

    text, model = None, None
    if config.ANTHROPIC_API_KEY:
        try:
            text, model = claude.draft(system, user), config.CLAUDE_MODEL
        except Exception:
            traceback.print_exc()
    if not text:
        text, model = gemini.draft(system, user), config.GEMINI_MODEL

    used = None
    m = re.search(r"\n?\s*NEWS_USED:\s*\[?(\w+)\]?\s*$", text, re.I)
    if m:
        text = text[: m.start()].rstrip()
        if m.group(1).isdigit() and 1 <= int(m.group(1)) <= len(stories):
            used = stories[int(m.group(1)) - 1]
    return text, used, model


def process_note(note, chat_id, source, reply_to=None, send=None):
    """Score + draft a note. `send` is injectable so scripts/try_note.py can run without Telegram."""
    send = send or telegram.send
    note_id = store.save_note(chat_id=chat_id, telegram_message_id=reply_to, source=source,
                              transcript=note, status="received")

    # 1. Score before anything else
    s = gemini.score(note)
    store.update_note(note_id, score=s["score"], score_reason=s["reason"], angle=s["angle"])

    if s["score"] < config.SCORE_THRESHOLD:
        store.update_note(note_id, status="rejected")
        send(chat_id, f"Score: {s['score']}/10 — no draft made.\n{s['reason']}", reply_to=reply_to)
        return {"score": s, "draft": None}

    send(chat_id, f"Score: {s['score']}/10 — drafting.\n{s['reason']}", reply_to=reply_to)
    store.update_note(note_id, status="drafting")

    # 2. News angle (Google News RSS)
    stories, phrase = [], ""
    try:
        # Search phrase comes from the scoring call (saves a Gemini request); fall back if missing.
        phrase = s.get("search_phrase") or gemini.keywords(note).get("phrase", "")
        stories = news.search(phrase, limit=3)
        if not stories and len(phrase.split()) > 2:
            # Too specific: widen to the first two words and a 90-day window.
            phrase = " ".join(phrase.split()[:2])
            stories = news.search(phrase, limit=3, days=90)
    except Exception:
        traceback.print_exc()

    # 3. Draft in her voice
    post, item, model = write_draft(note, s["angle"], stories)
    body = post + ("\n\n" + verify_flag(item) if item else "")

    draft_id = store.save_draft(
        note_id=note_id, chat_id=chat_id, body=body, model=model, status="pending",
        news_headline=item["headline"] if item else None,
        news_source=item["source"] if item else None,
        news_date=item["date"] if item else None,
        news_url=item["url"] if item else None,
    )
    store.update_note(note_id, status="drafted")

    header = f"DRAFT · pending your review · {len(post.split())} words\n\n"
    buttons = [[{"text": "Approve", "callback_data": f"a:{draft_id or ''}"},
                {"text": "Reject", "callback_data": f"r:{draft_id or ''}"}]]
    ids = send(chat_id, header + body, buttons=buttons)
    store.update_draft(draft_id, telegram_message_ids=ids)

    # Always show what the news search found, so Meera can see the angle even if it wasn't used.
    if stories:
        note_used = "Used in the draft: #%d." % (stories.index(item) + 1) if item else "None fitted, so the draft doesn't use one."
        send(chat_id, f"News search (Google News): \"{phrase}\"\n\n{news.format_list(stories)}\n\n{note_used}")
    else:
        send(chat_id, f"News search (Google News): \"{phrase or '-'}\" — nothing recent found.")
    return {"score": s, "draft": body, "news": stories, "used": item, "model": model}


def decide(chat_id, draft, approve, message_id=None):
    if not draft:
        telegram.send(chat_id, "I couldn't find that draft. Reply APPROVE or REJECT directly to the draft message.")
        return
    if draft["status"] != "pending":
        telegram.send(chat_id, f"That draft is already {draft['status']}.")
        return
    status = "approved" if approve else "rejected"
    store.update_draft(draft["id"], status=status, decided_at=datetime.now(timezone.utc).isoformat())
    ids = draft.get("telegram_message_ids") or ([message_id] if message_id else [])
    for mid in ids:
        telegram.clear_buttons(chat_id, mid)
    # Reply to the draft itself, so the chat doubles as the record when there's no database.
    anchor = ids[0] if ids else None
    if approve:
        telegram.send(chat_id, "APPROVED. Copy it into LinkedIn when you're ready — nothing is posted "
                               "automatically. Check the news source first if it has one.", reply_to=anchor)
    else:
        telegram.send(chat_id, "REJECTED. Send a fuller note on the same idea if you want another go.",
                      reply_to=anchor)


def _draft_for(chat_id, message_id, draft_id=None):
    """Find the draft behind a button press or reply. Without Supabase, the Telegram message is the draft."""
    if store.enabled():
        return store.get_draft(draft_id) if draft_id else store.draft_by_message(chat_id, message_id)
    return {"id": None, "status": "pending", "telegram_message_ids": [message_id]}


def handle_update(update):
    if store.seen_update(update.get("update_id")):
        return

    cb = update.get("callback_query")
    if cb:
        msg = cb.get("message") or {}
        chat_id = msg.get("chat", {}).get("id")
        if not _allowed(chat_id):
            return
        action, _, draft_id = (cb.get("data") or "").partition(":")
        telegram.answer_callback(cb["id"], "Approved" if action == "a" else "Rejected")
        decide(chat_id, _draft_for(chat_id, msg.get("message_id"), draft_id), action == "a", msg.get("message_id"))
        return

    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or msg.get("caption") or "").strip()

    if text.startswith("/start") or text.startswith("/help"):
        telegram.send(chat_id, HELP.format(t=config.SCORE_THRESHOLD, chat_id=chat_id))
        return
    if not _allowed(chat_id):
        return

    if text.startswith("/news"):
        topic = text[len("/news"):].strip()
        if not topic:
            telegram.send(chat_id, "Usage: /news <topic>   e.g. /news niacinamide India")
            return
        stories = news.search(topic, limit=5)
        telegram.send(chat_id, f"Google News: \"{topic}\" (last 30 days)\n\n{news.format_list(stories)}"
                      if stories else f"No recent Google News results for \"{topic}\".")
        return

    try:
        # APPROVE / REJECT as a reply to a draft
        word = text.lower().strip(".! ")
        if msg.get("reply_to_message") and (word in APPROVE_WORDS or word in REJECT_WORDS):
            replied = msg["reply_to_message"]
            if not store.enabled() and not (replied.get("text") or "").startswith("DRAFT"):
                telegram.send(chat_id, "Reply APPROVE or REJECT to the draft message itself.")
                return
            decide(chat_id, _draft_for(chat_id, replied["message_id"]), word in APPROVE_WORDS)
            return

        audio = msg.get("voice") or msg.get("audio") or msg.get("video_note")
        if audio:
            telegram.typing(chat_id)
            mime = audio.get("mime_type") or ("video/mp4" if msg.get("video_note") else "audio/ogg")
            transcript = gemini.transcribe(telegram.download_file(audio["file_id"]), mime)
            if not transcript:
                telegram.send(chat_id, "I couldn't make out that voice note. Could you try again?",
                              reply_to=msg["message_id"])
                return
            telegram.send(chat_id, f"Transcript:\n\n{transcript}", reply_to=msg["message_id"])
            telegram.typing(chat_id)
            process_note(transcript, chat_id, "voice", reply_to=msg["message_id"])
        elif text and not text.startswith("/"):
            telegram.typing(chat_id)
            process_note(text, chat_id, "text", reply_to=msg["message_id"])
    except gemini.QuotaExhausted:
        traceback.print_exc()
        telegram.send(chat_id, "Gemini's free daily limit is used up on every model right now, so I couldn't "
                               "process that note. It resets around 12:30pm IST — send it again after that. "
                               "(Turning on billing in Google AI Studio removes this limit.)")
    except Exception as e:
        traceback.print_exc()
        telegram.send(chat_id, f"Something went wrong processing that note ({type(e).__name__}: "
                               f"{str(e)[:120]}). Please send it again in a minute.")


def _allowed(chat_id):
    return not config.ALLOWED_CHAT_IDS or str(chat_id) in config.ALLOWED_CHAT_IDS
