import anthropic

from . import config

_client = None


def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def draft(system, user):
    """Draft with Claude. Returns text, or None if the request was refused (caller falls back)."""
    resp = client().beta.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        return None
    return "".join(b.text for b in resp.content if b.type == "text").strip()
