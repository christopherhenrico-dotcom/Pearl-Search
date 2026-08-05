"""Configuration management for Pearl."""

import os
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

CONFIG_DIR = Path.home() / ".config" / "pearl"
CONFIG_FILE = CONFIG_DIR / "config.toml"
SOURCES_FILE = CONFIG_DIR / "sources.toml"
HISTORY_FILE = CONFIG_DIR / "history.json"

DEFAULT_CONFIG = """\
# Pearl Configuration — ~/.config/pearl/config.toml
# ☠  Edit freely, Cap'n  ☠

[player]
# Command to invoke your media player
command = "vlc"
# Extra arguments passed to VLC
args = ["--no-video-title-show", "--quiet"]
# If true, Pearl waits for VLC to exit before returning to the menu
wait = false

[search]
# Default quality filter (720p, 1080p, 4k, any)
default_quality = "720p"
# Max results to display at once
max_results = 20
# Default search provider: "ddg" (DuckDuckGo, no key needed) or "tmdb"
provider = "ddg"
# Language for results (ISO 639-1)
language = "en"

[tmdb]
# Optional: TMDB API key for structured movie/TV metadata + episode browsing
# Get a free key at https://www.themoviedb.org/settings/api
api_key = ""

[display]
# Color theme: "pirate" (default), "minimal", "classic"
theme = "pirate"
# Show ASCII skull on startup
show_skull = true
# Show loading spinners
show_spinners = true

[history]
# Save search + play history
enabled = true
max_entries = 500

[sources]
# ─────────────────────────────────────────────────────────────────────────────
# SOURCE CONFIGURATION — Add your own URLs here
# ─────────────────────────────────────────────────────────────────────────────
#
# Pearl uses yt-dlp to extract streams from URLs you provide.
# yt-dlp supports hundreds of sites. See: https://github.com/yt-dlp/yt-dlp
#
# Two types of sources:
#
# 1. DIRECT URL — paste a URL and Pearl plays it immediately.
#    Works with any yt-dlp-compatible URL.
#
# 2. TEMPLATE — define a URL pattern with placeholders. Pearl fills them in
#    when you select a title. Placeholders:
#      {title}    — show/movie title (URL-encoded)
#      {year}     — release year
#      {season}   — season number (e.g. 1)
#      {episode}  — episode number (e.g. 3)
#      {s00e00}   — combined (e.g. S01E03)
#      {imdb}     — IMDb ID (requires TMDB key)
#      {tmdb}     — TMDB ID (requires TMDB key)
#      {query}    — raw search query (URL-encoded)
#
# Examples (fill in your own domains):
#
# [[sources.servers]]
# name = "Server Alpha"
# url_template = "https://example.com/search/{query}"
# priority = 1
# enabled = true
#
# [[sources.servers]]
# name = "Server Beta"
# url_template = "https://example2.com/tv/{imdb}/{season}/{episode}"
# priority = 2
# enabled = true
#
# [[sources.servers]]
# name = "Server Gamma"
# url_template = "https://example3.com/movie/{imdb}"
# priority = 3
# enabled = true
#
# Rotation strategy: "priority" (try in order), "random" (random each time)
rotation = "priority"

# Fallback: if all configured servers fail, ask the user to paste a URL
fallback_to_manual = true
"""


class Config:
    """Pearl configuration object."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    def get(self, *keys: str, default: Any = None) -> Any:
        node = self._data
        for k in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(k, default)
            if node is default:
                return default
        return node

    @property
    def player_command(self) -> str:
        return self.get("player", "command", default="vlc")

    @property
    def player_args(self) -> list[str]:
        return self.get("player", "args", default=[])

    @property
    def player_wait(self) -> bool:
        return self.get("player", "wait", default=False)

    @property
    def default_quality(self) -> str:
        return self.get("search", "default_quality", default="720p")

    @property
    def max_results(self) -> int:
        return self.get("search", "max_results", default=20)

    @property
    def search_provider(self) -> str:
        return self.get("search", "provider", default="ddg")

    @property
    def tmdb_api_key(self) -> str:
        return self.get("tmdb", "api_key", default="")

    @property
    def show_skull(self) -> bool:
        return self.get("display", "show_skull", default=True)

    @property
    def show_spinners(self) -> bool:
        return self.get("display", "show_spinners", default=True)

    @property
    def history_enabled(self) -> bool:
        return self.get("history", "enabled", default=True)

    @property
    def max_history(self) -> int:
        return self.get("history", "max_entries", default=500)

    @property
    def servers(self) -> list[dict[str, Any]]:
        servers = self.get("sources", "servers", default=[])
        if not isinstance(servers, list):
            return []
        return [s for s in servers if s.get("enabled", True)]

    @property
    def rotation_strategy(self) -> str:
        return self.get("sources", "rotation", default="priority")

    @property
    def fallback_to_manual(self) -> bool:
        return self.get("sources", "fallback_to_manual", default=True)

    @property
    def has_tmdb(self) -> bool:
        return bool(self.tmdb_api_key)

    @property
    def has_servers(self) -> bool:
        return len(self.servers) > 0


def ensure_config_dir() -> None:
    """Create config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def write_default_config() -> None:
    """Write the default config file."""
    ensure_config_dir()
    CONFIG_FILE.write_text(DEFAULT_CONFIG, encoding="utf-8")


def load_config() -> Config:
    """Load configuration from disk, creating defaults if needed."""
    if not CONFIG_FILE.exists():
        write_default_config()

    if tomllib is None:
        # No TOML parser available; return bare defaults
        return Config({})

    try:
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)
        return Config(data)
    except Exception:
        return Config({})


def open_config_in_editor() -> None:
    """Open the config file in the system editor."""
    if not CONFIG_FILE.exists():
        write_default_config()

    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))
    os.execlp(editor, editor, str(CONFIG_FILE))


def get_config_path() -> Path:
    return CONFIG_FILE
