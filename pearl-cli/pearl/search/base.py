"""Base types for Pearl search backends."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MediaType(Enum):
    MOVIE = "movie"
    TV = "tv"
    UNKNOWN = "unknown"


@dataclass
class EpisodeInfo:
    number: int
    title: str
    overview: str = ""
    air_date: str = ""
    runtime: Optional[int] = None  # minutes
    still_url: str = ""

    def label(self) -> str:
        return f"E{self.number:02d} — {self.title}" if self.title else f"Episode {self.number}"


@dataclass
class SeasonInfo:
    number: int
    title: str = ""
    episode_count: int = 0
    air_date: str = ""
    episodes: list[EpisodeInfo] = field(default_factory=list)

    def label(self) -> str:
        name = self.title or f"Season {self.number}"
        ep = f"  ({self.episode_count} episodes)" if self.episode_count else ""
        return f"{name}{ep}"


@dataclass
class SearchResult:
    """A single search result entry."""
    title: str
    url: str
    media_type: MediaType = MediaType.UNKNOWN
    year: str = ""
    overview: str = ""
    rating: str = ""
    language: str = ""
    # TMDB / IMDb identifiers (populated when using TMDB backend)
    tmdb_id: Optional[int] = None
    imdb_id: str = ""
    # Cached season data (populated on demand)
    seasons: list[SeasonInfo] = field(default_factory=list)
    # Source label displayed to user
    source: str = ""

    def display_title(self) -> str:
        parts = [self.title]
        if self.year:
            parts.append(f"({self.year})")
        if self.media_type != MediaType.UNKNOWN:
            icon = "🎬" if self.media_type == MediaType.MOVIE else "📺"
            parts.insert(0, icon)
        return "  ".join(parts)

    def short_overview(self, max_len: int = 90) -> str:
        if not self.overview:
            return ""
        if len(self.overview) <= max_len:
            return self.overview
        return self.overview[:max_len].rsplit(" ", 1)[0] + "…"


@dataclass
class MediaInfo:
    """Detailed media information for a selected result."""
    result: SearchResult
    seasons: list[SeasonInfo] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    status: str = ""
    tagline: str = ""
