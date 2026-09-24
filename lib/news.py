"""Google News RSS search. No key, no account."""
import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

RSS = "https://news.google.com/rss/search?q={q}+when:30d&hl=en-IN&gl=IN&ceid=IN:en"


def top_story(phrase):
    """Return {headline, source, date, url, summary} for the top result, or None."""
    if not phrase:
        return None
    try:
        r = requests.get(RSS.format(q=quote_plus(phrase)), timeout=15,
                         headers={"User-Agent": "Mozilla/5.0 (meera-bot)"})
        r.raise_for_status()
        item = ET.fromstring(r.content).find("./channel/item")
    except Exception:
        return None
    if item is None:
        return None

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
