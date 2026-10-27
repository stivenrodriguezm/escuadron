"""Titulares cripto/macro reales desde feeds RSS públicos (sin claves)."""
from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx

log = logging.getLogger("news")
FEEDS = ["https://www.coindesk.com/arc/outboundfeeds/rss/",
         "https://cointelegraph.com/rss",
         "https://decrypt.co/feed"]
CACHE_TTL_S = 15 * 60
_cache: dict[str, object] = {"at": 0.0, "items": []}


def _parse(xml_text: str, since: datetime) -> list[tuple[datetime, str]]:
    out = []
    for item in ET.fromstring(xml_text).iter("item"):
        title = (item.findtext("title") or "").strip()
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            continue
        if title and published >= since:
            out.append((published, title))
    return out


async def recent_headlines(hours: int = 24, limit: int = 20) -> list[str]:
    """Titulares de las últimas `hours` horas, más recientes primero, sin duplicados."""
    if time.time() - float(_cache["at"]) < CACHE_TTL_S and _cache["items"]:
        return list(_cache["items"])[:limit]  # type: ignore[arg-type]
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    items: list[tuple[datetime, str]] = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0 (trading-squad)"}) as client:
        for url in FEEDS:
            try:
                r = await client.get(url)
                r.raise_for_status()
                items += _parse(r.text, since)
            except (httpx.HTTPError, ET.ParseError) as exc:
                log.warning("Feed %s no disponible: %s", url, exc)
    seen: set[str] = set()
    titles = []
    for _, title in sorted(items, reverse=True):
        key = title.lower()[:60]
        if key not in seen:
            seen.add(key)
            titles.append(title[:110])
    _cache.update(at=time.time(), items=titles)
    return titles[:limit]
