"""Supabase persistence via its REST API. Every function is a no-op if Supabase isn't configured."""
import requests

from . import config


def enabled():
    return bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY)


def _req(method, table, params=None, body=None, prefer="return=representation"):
    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }
    r = requests.request(method, f"{config.SUPABASE_URL}/rest/v1/{table}",
                         params=params, json=body, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json() if r.text else []


def seen_update(update_id):
    """Record a Telegram update id. Returns True if we've already processed it (Telegram retry)."""
    if not enabled():
        return False
    try:
        _req("POST", "processed_updates", body={"update_id": update_id}, prefer="return=minimal")
        return False
    except requests.HTTPError as e:
        return e.response is not None and e.response.status_code == 409


def active_voice_skill():
    if not enabled():
        return None
    rows = _req("GET", "voice_skill", params={"active": "eq.true", "order": "created_at.desc", "limit": 1})
    return rows[0]["content"] if rows else None


def save_note(**fields):
    if not enabled():
        return None
    return _req("POST", "notes", body=fields)[0]["id"]


def update_note(note_id, **fields):
    if enabled() and note_id:
        _req("PATCH", "notes", params={"id": f"eq.{note_id}"}, body=fields)


def save_draft(**fields):
    if not enabled():
        return None
    return _req("POST", "drafts", body=fields)[0]["id"]


def update_draft(draft_id, **fields):
    if enabled() and draft_id:
        _req("PATCH", "drafts", params={"id": f"eq.{draft_id}"}, body=fields)


def get_draft(draft_id):
    if not enabled():
        return None
    rows = _req("GET", "drafts", params={"id": f"eq.{draft_id}", "limit": 1})
    return rows[0] if rows else None


def draft_by_message(chat_id, message_id):
    if not enabled():
        return None
    rows = _req("GET", "drafts", params={
        "chat_id": f"eq.{chat_id}",
        "telegram_message_ids": f"cs.{{{message_id}}}",
        "limit": 1,
    })
    return rows[0] if rows else None
