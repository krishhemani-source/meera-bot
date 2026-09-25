"""Google News RSS search. No key, no account."""
import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

RSS = "https://news.google.com/rss/search?q={q}+when:{days}d&hl=en-IN&gl=IN&ceid=IN:en"


def _parse(item):
    source = (item.findtext("source") or "").strip()
    title = (item.findtext("title") or "").strip()
    # Google appends " - Publication" to titles; strip it.
    if source and title.endswith(" - " + source):
        title = title[: -len(" - " + source)]
    try:
        date = parsedate_to_datetime(item.findtext("pubDate")).strftime("%d %b %Y")
    except Exception:
        date = (item.findtext("pubDate") or "").strip()
    desc = re.sub(r"<[^>]+>", " ", html.unescape(item.findtext("description") or ""))
    desc = re.sub(r"\s+", " ", desc).strip()
    return {
        "headline": title,
        "source": source or "Unknown",
        "date": date,
        "url": (item.findtext("link") or "").strip(),
        "summary": title if (not desc or desc.startswith(title[:40])) else desc,
    }


def search(phrase, limit=3, days=30):
    """Return up to `limit` stories [{headline, source, date, url, summary}] from the last `days` days."""
    if not phrase:
        return []
    try:
        r = requests.get(RSS.format(q=quote_plus(phrase), days=days), timeout=15,
                         headers={"User-Agent": "Mozilla/5.0 (meera-bot)"})
        r.raise_for_status()
        items = ET.fromstring(r.content).findall("./channel/item")
    except Exception:
        return []
    return [_parse(i) for i in items[:limit]]


def format_list(stories):
    return "\n\n".join(f"{n}. {s['headline']}\n{s['source']} · {s['date']}\n{s['url']}"
                       for n, s in enumerate(stories, 1))
