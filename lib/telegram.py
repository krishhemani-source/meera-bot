import requests

from . import config

API = "https://api.telegram.org"
MAX_LEN = 4000  # Telegram hard limit is 4096


def _call(method, **payload):
    r = requests.post(f"{API}/bot{config.TELEGRAM_BOT_TOKEN}/{method}", json=payload, timeout=30)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {data}")
    return data["result"]


def _chunks(text):
    parts, text = [], text.strip()
    while len(text) > MAX_LEN:
        cut = text.rfind("\n\n", 0, MAX_LEN)
        if cut < MAX_LEN // 2:
            cut = MAX_LEN
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    parts.append(text)
    return parts


def send(chat_id, text, reply_to=None, buttons=None):
    """Send text (split if long). Returns list of sent message_ids. Buttons go on the last chunk."""
    ids = []
    chunks = _chunks(text)
    for i, chunk in enumerate(chunks):
        payload = {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True}
        if reply_to and i == 0:
            payload["reply_parameters"] = {"message_id": reply_to, "allow_sending_without_reply": True}
        if buttons and i == len(chunks) - 1:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        ids.append(_call("sendMessage", **payload)["message_id"])
    return ids


def typing(chat_id):
    try:
        _call("sendChatAction", chat_id=chat_id, action="typing")
    except Exception:
        pass


def answer_callback(callback_id, text=""):
    try:
        _call("answerCallbackQuery", callback_query_id=callback_id, text=text)
    except Exception:
        pass


def clear_buttons(chat_id, message_id):
    try:
        _call("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id,
              reply_markup={"inline_keyboard": []})
    except Exception:
        pass


def download_file(file_id):
    path = _call("getFile", file_id=file_id)["file_path"]
    r = requests.get(f"{API}/file/bot{config.TELEGRAM_BOT_TOKEN}/{path}", timeout=60)
    r.raise_for_status()
    return r.content
