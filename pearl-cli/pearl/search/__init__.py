"""Search backends for Pearl."""
from .base import SearchResult, EpisodeInfo, SeasonInfo, MediaInfo, MediaType
from .ddg import DuckDuckGoSearch
from .tmdb import TMDBSearch

__all__ = [
    "SearchResult",
    "EpisodeInfo",
    "SeasonInfo",
    "MediaInfo",
    "MediaType",
    "DuckDuckGoSearch",
    "TMDBSearch",
]
