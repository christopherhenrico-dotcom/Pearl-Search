"""DuckDuckGo search backend — no API key required."""

from __future__ import annotations
import re
import urllib.parse
import random
from typing import Optional

import requests

from .base import SearchResult, MediaType

# DDG HTML search endpoint (no JS, no API key)
DDG_URL = "https://html.duckduckgo.com/html/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Fallback: DDG lite
DDG_LITE = "https://lite.duckduckgo.com/lite/"

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_TV_SIGNALS = re.compile(
    r"\b(series|season|episode|episodes|ep\.?|s\d{1,2}e\d{1,2}|tv.?show|"
    r"streaming|watch online|full.?episodes)\b",
    re.IGNORECASE,
)
_MOVIE_SIGNALS = re.compile(
    r"\b(film|movie|cinema|blu.?ray|dvd|theatrical|box.?office)\b",
    re.IGNORECASE,
)


def _guess_media_type(title: str, overview: str) -> MediaType:
    combined = f"{title} {overview}"
    tv_score = len(_TV_SIGNALS.findall(combined))
    movie_score = len(_MOVIE_SIGNALS.findall(combined))
    if tv_score > movie_score:
        return MediaType.TV
    if movie_score > tv_score:
        return MediaType.MOVIE
    return MediaType.UNKNOWN


def _extract_year(text: str) -> str:
    m = _YEAR_RE.search(text)
    return m.group(0) if m else ""


def _parse_ddg_html(html: str, quality: Optional[str]) -> list[SearchResult]:
    """Parse DDG HTML search results page."""
    results: list[SearchResult] = []

    # Extract result blocks: each result has a link + snippet
    # DDG HTML format: <a class="result__a" href="...">Title</a>
    # and <a class="result__snippet">...</a>
    block_re = re.compile(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'class="result__snippet"[^>]*>(.*?)</(?:a|span)>',
        re.DOTALL,
    )

    for m in block_re.finditer(html):
        raw_url = m.group(1).strip()
        raw_title = m.group(2).strip()
        raw_snippet = m.group(3).strip()

        # Clean HTML tags
        title = re.sub(r"<[^>]+>", "", raw_title).strip()
        snippet = re.sub(r"<[^>]+>", "", raw_snippet).strip()

        # DDG wraps URLs through their redirect; extract real URL
        url = _unwrap_ddg_url(raw_url)

        if not title or not url:
            continue

        # Apply quality filter to title/snippet
        if quality and quality.lower() != "any":
            q = quality.lower().replace("p", "")
            # Don't hard-exclude — just rank later
            pass

        year = _extract_year(snippet) or _extract_year(title)
        media_type = _guess_media_type(title, snippet)

        results.append(
            SearchResult(
                title=title,
                url=url,
                media_type=media_type,
                year=year,
                overview=snippet,
                source="DuckDuckGo",
            )
        )

    return results


def _unwrap_ddg_url(url: str) -> str:
    """DDG wraps links in a redirect. Extract the real URL."""
    if url.startswith("//duckduckgo.com/l/?"):
        parsed = urllib.parse.urlparse("https:" + url)
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs:
            return urllib.parse.unquote(qs["uddg"][0])
    if url.startswith("/l/?"):
        parsed = urllib.parse.urlparse("https://duckduckgo.com" + url)
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs:
            return urllib.parse.unquote(qs["uddg"][0])
    return url


class DuckDuckGoSearch:
    """Search using DuckDuckGo HTML endpoint."""

    def __init__(self, max_results: int = 20, timeout: int = 10):
        self.max_results = max_results
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    def search(
        self,
        query: str,
        quality: Optional[str] = None,
        media_hint: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Search DuckDuckGo. Returns list of SearchResult.

        Args:
            query: Search string
            quality: Optional quality filter ("720p", "1080p", "4k")
            media_hint: Optional "movie" or "tv" to bias results
        """
        q = query
        if quality and quality.lower() != "any":
            q = f"{query} {quality}"
        if media_hint == "movie":
            q += " watch full movie"
        elif media_hint == "tv":
            q += " watch series online"
        else:
            q += " watch online"

        results = self._fetch_ddg(q, quality)

        if not results:
            # Retry without quality
            results = self._fetch_ddg(query + " watch online", None)

        return results[: self.max_results]

    def _fetch_ddg(self, query: str, quality: Optional[str]) -> list[SearchResult]:
        try:
            resp = self._session.post(
                DDG_URL,
                data={"q": query, "b": "", "kl": "us-en"},
                timeout=self.timeout,
                allow_redirects=True,
            )
            resp.raise_for_status()
            return _parse_ddg_html(resp.text, quality)
        except requests.RequestException:
            pass

        # Fallback to lite endpoint
        try:
            resp = self._session.post(
                DDG_LITE,
                data={"q": query},
                timeout=self.timeout,
                allow_redirects=True,
            )
            resp.raise_for_status()
            return _parse_ddg_lite(resp.text, quality)
        except requests.RequestException:
            return []

    def close(self) -> None:
        self._session.close()


def _parse_ddg_lite(html: str, quality: Optional[str]) -> list[SearchResult]:
    """Parse DDG lite HTML results."""
    results: list[SearchResult] = []
    # DDG lite: links in <a class="result-link">
    link_re = re.compile(
        r'<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'<td[^>]+class="result-snippet"[^>]*>(.*?)</td>',
        re.DOTALL,
    )
    for m in link_re.finditer(html):
        url = m.group(1).strip()
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        snippet = re.sub(r"<[^>]+>", "", m.group(3)).strip()
        if not title or not url or url.startswith("//"):
            continue
        year = _extract_year(snippet) or _extract_year(title)
        results.append(
            SearchResult(
                title=title,
                url=url,
                media_type=_guess_media_type(title, snippet),
                year=year,
                overview=snippet,
                source="DuckDuckGo",
            )
        )
    return results
