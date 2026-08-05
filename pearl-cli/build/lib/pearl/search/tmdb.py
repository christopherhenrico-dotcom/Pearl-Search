"""TMDB search backend — requires free API key from themoviedb.org."""

from __future__ import annotations
import urllib.parse
from typing import Optional

import requests

from .base import (
    SearchResult,
    MediaType,
    SeasonInfo,
    EpisodeInfo,
    MediaInfo,
)

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


class TMDBSearch:
    """Search and browse using the TMDB API."""

    def __init__(self, api_key: str, language: str = "en-US", timeout: int = 10):
        self.api_key = api_key
        self.language = language
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Pearl-CLI/1.0",
            "Accept": "application/json",
        })

    def _get(self, path: str, **params) -> dict:
        params["api_key"] = self.api_key
        params["language"] = self.language
        url = f"{TMDB_BASE}{path}"
        resp = self._session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def search(
        self,
        query: str,
        quality: Optional[str] = None,
        media_hint: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search for movies and/or TV shows."""
        results: list[SearchResult] = []

        if media_hint == "movie":
            results = self._search_movies(query)
        elif media_hint == "tv":
            results = self._search_tv(query)
        else:
            # Multi-search: movies + TV
            results = self._search_multi(query)

        return results

    def _search_multi(self, query: str) -> list[SearchResult]:
        try:
            data = self._get("/search/multi", query=query, include_adult=False)
        except requests.RequestException:
            return []

        results: list[SearchResult] = []
        for item in data.get("results", []):
            media = item.get("media_type", "")
            if media == "movie":
                results.append(self._movie_to_result(item))
            elif media == "tv":
                results.append(self._tv_to_result(item))
        return results

    def _search_movies(self, query: str) -> list[SearchResult]:
        try:
            data = self._get("/search/movie", query=query, include_adult=False)
        except requests.RequestException:
            return []
        return [self._movie_to_result(i) for i in data.get("results", [])]

    def _search_tv(self, query: str) -> list[SearchResult]:
        try:
            data = self._get("/search/tv", query=query)
        except requests.RequestException:
            return []
        return [self._tv_to_result(i) for i in data.get("results", [])]

    def _movie_to_result(self, item: dict) -> SearchResult:
        release = item.get("release_date", "")
        year = release[:4] if release else ""
        vote = item.get("vote_average", 0)
        rating = f"{vote:.1f}/10" if vote else ""
        return SearchResult(
            title=item.get("title", item.get("original_title", "Unknown")),
            url=f"https://www.themoviedb.org/movie/{item.get('id', '')}",
            media_type=MediaType.MOVIE,
            year=year,
            overview=item.get("overview", ""),
            rating=rating,
            tmdb_id=item.get("id"),
            source="TMDB",
        )

    def _tv_to_result(self, item: dict) -> SearchResult:
        first_air = item.get("first_air_date", "")
        year = first_air[:4] if first_air else ""
        vote = item.get("vote_average", 0)
        rating = f"{vote:.1f}/10" if vote else ""
        return SearchResult(
            title=item.get("name", item.get("original_name", "Unknown")),
            url=f"https://www.themoviedb.org/tv/{item.get('id', '')}",
            media_type=MediaType.TV,
            year=year,
            overview=item.get("overview", ""),
            rating=rating,
            tmdb_id=item.get("id"),
            source="TMDB",
        )

    def get_seasons(self, result: SearchResult) -> list[SeasonInfo]:
        """Fetch season list for a TV show."""
        if result.media_type != MediaType.TV or not result.tmdb_id:
            return []
        try:
            data = self._get(f"/tv/{result.tmdb_id}")
        except requests.RequestException:
            return []

        seasons: list[SeasonInfo] = []
        for s in data.get("seasons", []):
            snum = s.get("season_number", 0)
            if snum == 0:
                continue  # Skip specials by default
            seasons.append(
                SeasonInfo(
                    number=snum,
                    title=s.get("name", f"Season {snum}"),
                    episode_count=s.get("episode_count", 0),
                    air_date=s.get("air_date", ""),
                )
            )
        return seasons

    def get_episodes(self, result: SearchResult, season_number: int) -> list[EpisodeInfo]:
        """Fetch episode list for a season."""
        if not result.tmdb_id:
            return []
        try:
            data = self._get(f"/tv/{result.tmdb_id}/season/{season_number}")
        except requests.RequestException:
            return []

        episodes: list[EpisodeInfo] = []
        for ep in data.get("episodes", []):
            episodes.append(
                EpisodeInfo(
                    number=ep.get("episode_number", 0),
                    title=ep.get("name", ""),
                    overview=ep.get("overview", ""),
                    air_date=ep.get("air_date", ""),
                    runtime=ep.get("runtime"),
                )
            )
        return episodes

    def get_external_ids(self, result: SearchResult) -> dict:
        """Fetch IMDb ID and other external identifiers."""
        if not result.tmdb_id:
            return {}
        path = (
            f"/movie/{result.tmdb_id}/external_ids"
            if result.media_type == MediaType.MOVIE
            else f"/tv/{result.tmdb_id}/external_ids"
        )
        try:
            return self._get(path)
        except requests.RequestException:
            return {}

    def close(self) -> None:
        self._session.close()
