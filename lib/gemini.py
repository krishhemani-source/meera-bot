import json
import time

from google import genai
from google.genai import errors, types

from . import config, prompts

_client = None


def client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


class QuotaExhausted(Exception):
    """Every Gemini model in the chain is out of quota or unavailable."""


def _generate(**kwargs):
    """generate_content across a chain of models.

    429 (daily free-tier quota) or 404 -> next model straight away.
    503/500 (overloaded) -> one quick retry, then next model.
    """
    last = None
    for model in [config.GEMINI_MODEL] + [m for m in config.GEMINI_FALLBACK_MODELS if m != config.GEMINI_MODEL]:
        for attempt in range(2):
            try:
                resp = client().models.generate_content(model=model, **kwargs)
                parts = resp.candidates[0].content.parts if resp.candidates else []
                return "".join(p.text for p in parts
                               if getattr(p, "text", None) and not getattr(p, "thought", False)).strip()
            except (errors.ServerError, errors.ClientError) as e:
                last = e
                code = getattr(e, "code", None)
                if code in (500, 503) and attempt == 0:
                    time.sleep(2)
                    continue
                if code in (429, 404, 500, 503):
                    print(f"gemini {model}: {code}, trying next model")
                    break
                raise
    raise QuotaExhausted(str(last)[:200])


def _json(contents, schema, system=None):
    return json.loads(_generate(
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0.2,
        ),
    ))


def transcribe(audio_bytes, mime_type):
    return _generate(
        contents=[types.Part.from_bytes(data=audio_bytes, mime_type=mime_type), prompts.TRANSCRIBE],
        config=types.GenerateContentConfig(temperature=0),
    )


def score(note):
    schema = {
        "type": "object",
        "properties": {
            "score": {"type": "integer", "minimum": 0, "maximum": 10},
            "reason": {"type": "string"},
            "angle": {"type": "string"},
            "search_phrase": {"type": "string"},
        },
        "required": ["score", "reason", "angle", "search_phrase"],
    }
    out = _json(prompts.SCORE_USER.format(note=note), schema, system=prompts.SCORE_SYSTEM)
    out["score"] = max(0, min(10, int(out["score"])))
    return out


def keywords(note):
    schema = {
        "type": "object",
        "properties": {"terms": {"type": "array", "items": {"type": "string"}}, "phrase": {"type": "string"}},
        "required": ["terms", "phrase"],
    }
    return _json(prompts.KEYWORDS.format(note=note), schema)


def draft(system, user):
    return _generate(
        contents=user,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.7),
    )
