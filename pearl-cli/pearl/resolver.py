"""URL resolver — maps configured source templates to playable URLs."""

from __future__ import annotations
import random
import urllib.parse
from typing import Optional

from .search.base import SearchResult, MediaType


class Resolver:
    """Resolves configured server URL templates into concrete playable URLs."""

    def __init__(self, config):
        self.config = config

    def resolve_all(
        self,
        result: SearchResult,
        season: Optional[int] = None,
        episode: Optional[int] = None,
    ) -> list[tuple[str, str]]:
        """
        Returns list of (server_name, resolved_url) for all enabled servers.
        Ordered by priority or randomized, depending on config.
        """
        servers = self.config.servers
        if not servers:
            return []

        resolved: list[tuple[str, str]] = []
        for server in servers:
            url = self._resolve_template(server, result, season, episode)
            if url:
                resolved.append((server.get("name", "Server"), url))

        if self.config.rotation_strategy == "random":
            random.shuffle(resolved)

        return resolved

    def _resolve_template(
        self,
        server: dict,
        result: SearchResult,
        season: Optional[int],
        episode: Optional[int],
    ) -> Optional[str]:
        template = server.get("url_template", "")
        if not template:
            return None

        # Build substitution context
        title_raw = result.title or ""
        title_encoded = urllib.parse.quote_plus(title_raw)
        query_encoded = urllib.parse.quote_plus(title_raw)

        s = str(season or 0)
        e = str(episode or 0)
        s_padded = s.zfill(2)
        e_padded = e.zfill(2)
        s00e00 = f"S{s_padded}E{e_padded}" if season and episode else ""

        ctx = {
            "title": title_encoded,
            "title_raw": title_raw,
            "year": result.year or "",
            "season": s,
            "episode": e,
            "s": s_padded,
            "e": e_padded,
            "s00e00": s00e00,
            "imdb": result.imdb_id or "",
            "tmdb": str(result.tmdb_id or ""),
            "query": query_encoded,
        }

        try:
            return template.format_map(ctx)
        except (KeyError, ValueError):
            return template  # Return as-is if template substitution fails
