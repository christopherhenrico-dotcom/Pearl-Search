"""Interactive terminal navigator for Pearl — keyboard-driven menu system."""

from __future__ import annotations
import sys
import os
import random
from typing import Any, Callable, Optional, TypeVar

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.columns import Columns
from rich.rule import Rule
from rich import box

from .theme import PIRATE_THEME, RICH_PIRATE
from ..ascii_art import (
    BANNER, SKULL, CROSSBONES, DIVIDER, WAVE,
    SEARCH_PHRASES, PLAY_PHRASES, LOADING_PHRASES,
    EMPTY_PHRASES, ERROR_PHRASES, get_full_banner,
)
from ..search.base import SearchResult, SeasonInfo, EpisodeInfo, MediaType

T = TypeVar("T")

# Terminal key codes
KEY_UP    = "\x1b[A"
KEY_DOWN  = "\x1b[B"
KEY_RIGHT = "\x1b[C"
KEY_LEFT  = "\x1b[D"
KEY_ENTER = "\r"
KEY_ENTER2 = "\n"
KEY_ESC   = "\x1b"
KEY_Q     = "q"
KEY_QUIT  = "Q"
KEY_BACK  = "b"
KEY_HELP  = "?"
KEY_SLASH = "/"
KEY_P     = "p"
KEY_C     = "c"


def _get_key() -> str:
    """Read a single keypress from stdin (Unix only)."""
    import tty
    import termios

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            # Read potential escape sequence
            try:
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    return "\x1b[" + ch3
                return "\x1b" + ch2
            except Exception:
                return ch
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


console = Console(theme=RICH_PIRATE, highlight=False)


def _skull_panel(content: str, title: str = "") -> Panel:
    return Panel(
        content,
        title=f"[pearl.secondary]☠  {title}  ☠[/pearl.secondary]" if title else "",
        border_style="pearl.border",
        padding=(0, 2),
        box=box.HEAVY,
    )


def _render_result_row(
    idx: int,
    result: SearchResult,
    selected: bool,
    cursor_pos: int,
) -> Text:
    t = Text()
    is_cursor = idx == cursor_pos

    # Cursor indicator
    if is_cursor:
        t.append(" ❯ ", style="pearl.cursor")
    else:
        t.append("   ", style="")

    # Row number
    t.append(f"{idx + 1:>2}. ", style="pearl.dim")

    # Media type icon
    if result.media_type == MediaType.MOVIE:
        t.append("🎬 ", style="pearl.movie")
    elif result.media_type == MediaType.TV:
        t.append("📺 ", style="pearl.tv")
    else:
        t.append("   ", style="")

    # Title
    style = "pearl.selected" if is_cursor else "pearl.primary"
    t.append(result.title, style=style)

    # Year
    if result.year:
        t.append(f"  {result.year}", style="pearl.year")

    # Rating
    if result.rating:
        t.append(f"  ⭐ {result.rating}", style="pearl.rating")

    # Source
    if result.source:
        t.append(f"  [{result.source}]", style="pearl.source")

    return t


def _render_season_row(idx: int, season: SeasonInfo, is_cursor: bool) -> Text:
    t = Text()
    if is_cursor:
        t.append(" ❯ ", style="pearl.cursor")
    else:
        t.append("   ", style="")
    t.append(f"{idx + 1:>2}. ", style="pearl.dim")
    style = "pearl.selected" if is_cursor else "pearl.primary"
    t.append(season.label(), style=style)
    if season.air_date:
        t.append(f"  {season.air_date[:4]}", style="pearl.year")
    return t


def _render_episode_row(idx: int, ep: EpisodeInfo, is_cursor: bool) -> Text:
    t = Text()
    if is_cursor:
        t.append(" ❯ ", style="pearl.cursor")
    else:
        t.append("   ", style="")
    t.append(f"{idx + 1:>2}. ", style="pearl.dim")
    style = "pearl.selected" if is_cursor else "pearl.primary"
    t.append(ep.label(), style=style)
    if ep.air_date:
        t.append(f"  {ep.air_date}", style="pearl.year")
    if ep.runtime:
        t.append(f"  {ep.runtime}m", style="pearl.dim")
    return t


def _keybind_bar(bindings: list[tuple[str, str]]) -> str:
    parts = []
    for key, action in bindings:
        parts.append(f"[pearl.key] {key} [/pearl.key][pearl.dim] {action}[/pearl.dim]")
    return "  ".join(parts)


class Navigator:
    """Full-screen interactive navigator for Pearl."""

    def __init__(self, config: Any):
        self.config = config

    # ──────────────────────────────────────────────────────────────────────────
    # Public entry points
    # ──────────────────────────────────────────────────────────────────────────

    def show_welcome(self) -> None:
        console.clear()
        console.print(BANNER, style="pearl.secondary", highlight=False)
        console.print(
            f"  [pearl.dim]{CROSSBONES}[/pearl.dim]",
            highlight=False,
        )
        console.print()
        console.print(
            "  [pearl.primary]The Seven Seas Media CLI[/pearl.primary]  "
            "[pearl.dim]— Hoist the Jolly Roger and set sail for your content[/pearl.dim]"
        )
        console.print()
        self._print_help_quick()
        console.print()

    def prompt_search(self) -> Optional[tuple[str, Optional[str]]]:
        """Show an inline search prompt. Returns (query, quality) or None."""
        console.print()
        console.print(
            f"  [pearl.secondary]☠[/pearl.secondary]  "
            f"[pearl.primary]Enter your search query[/pearl.primary]  "
            f"[pearl.secondary]☠[/pearl.secondary]"
        )
        console.print(
            f"  [pearl.dim]Quality: 720p 1080p 4k any  |  Leave quality blank for default[/pearl.dim]"
        )
        console.print()
        try:
            raw = console.input("  [pearl.cursor]⚓  Query ❯[/pearl.cursor]  ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

        if not raw:
            return None

        # Parse optional trailing quality
        quality: Optional[str] = None
        tokens = raw.rsplit(None, 1)
        if len(tokens) == 2 and tokens[1].lower().rstrip("p") in ("720", "1080", "4k", "4", "any"):
            raw, quality = tokens[0], tokens[1]
        
        return raw.strip(), quality

    def show_searching(self, query: str, quality: Optional[str] = None) -> None:
        phrase = random.choice(SEARCH_PHRASES)
        q_tag = f" [pearl.quality]{quality}[/pearl.quality]" if quality else ""
        console.print()
        console.print(
            f"  [pearl.secondary]⚓[/pearl.secondary]  "
            f"[pearl.primary]{phrase}[/pearl.primary]{q_tag}"
        )
        console.print(f"  [pearl.dim]Query:[/pearl.dim] [pearl.tertiary]{query}[/pearl.tertiary]")
        console.print()

    def pick_result(
        self,
        results: list[SearchResult],
        query: str,
        quality: Optional[str],
    ) -> Optional[SearchResult]:
        """Interactive result picker. Returns selected SearchResult or None."""
        if not results:
            phrase = random.choice(EMPTY_PHRASES)
            console.print(f"\n  [pearl.warning]☠  {phrase}[/pearl.warning]\n")
            return None

        cursor = 0
        page_size = min(20, self._terminal_height() - 12)

        while True:
            self._render_results(results, cursor, page_size, query, quality)
            key = _get_key()

            if key in (KEY_UP,) and cursor > 0:
                cursor -= 1
            elif key in (KEY_DOWN,) and cursor < len(results) - 1:
                cursor += 1
            elif key in (KEY_ENTER, KEY_ENTER2):
                return results[cursor]
            elif key in (KEY_Q, KEY_QUIT, KEY_ESC):
                return None
            elif key == "1" and len(results) >= 1:
                cursor = 0
            # Number shortcuts 1-9
            elif key.isdigit() and int(key) > 0:
                n = int(key) - 1
                if 0 <= n < len(results):
                    cursor = n

    def pick_season(
        self,
        seasons: list[SeasonInfo],
        show_title: str,
    ) -> Optional[SeasonInfo]:
        """Interactive season picker."""
        if not seasons:
            console.print("\n  [pearl.warning]No seasons found.[/pearl.warning]\n")
            return None

        cursor = 0

        while True:
            self._render_seasons(seasons, cursor, show_title)
            key = _get_key()

            if key in (KEY_UP,) and cursor > 0:
                cursor -= 1
            elif key in (KEY_DOWN,) and cursor < len(seasons) - 1:
                cursor += 1
            elif key in (KEY_ENTER, KEY_ENTER2):
                return seasons[cursor]
            elif key in (KEY_Q, KEY_QUIT, KEY_ESC, KEY_BACK):
                return None
            elif key.isdigit() and int(key) > 0:
                n = int(key) - 1
                if 0 <= n < len(seasons):
                    cursor = n

    def pick_episode(
        self,
        episodes: list[EpisodeInfo],
        show_title: str,
        season: SeasonInfo,
    ) -> Optional[EpisodeInfo]:
        """Interactive episode picker."""
        if not episodes:
            console.print("\n  [pearl.warning]No episodes found.[/pearl.warning]\n")
            return None

        cursor = 0

        while True:
            self._render_episodes(episodes, cursor, show_title, season)
            key = _get_key()

            if key in (KEY_UP,) and cursor > 0:
                cursor -= 1
            elif key in (KEY_DOWN,) and cursor < len(episodes) - 1:
                cursor += 1
            elif key in (KEY_ENTER, KEY_ENTER2):
                return episodes[cursor]
            elif key in (KEY_Q, KEY_QUIT, KEY_ESC, KEY_BACK):
                return None
            elif key.isdigit() and int(key) > 0:
                n = int(key) - 1
                if 0 <= n < len(episodes):
                    cursor = n

    def pick_source(
        self,
        servers: list[dict],
        result: SearchResult,
        season_num: Optional[int] = None,
        episode_num: Optional[int] = None,
    ) -> Optional[str]:
        """
        Show source selection. If no servers configured, prompt for manual URL.
        Returns a final URL string or None.
        """
        from ..resolver import Resolver

        resolver = Resolver(self.config)

        # Build resolved URLs from all configured servers
        resolved = resolver.resolve_all(
            result=result,
            season=season_num,
            episode=episode_num,
        )

        options: list[tuple[str, str]] = []  # (label, url)

        for name, url in resolved:
            options.append((name, url))

        if options:
            # Show source picker menu
            chosen = self._pick_from_list(
                items=options,
                label_fn=lambda x: x[0],
                title="Choose a source",
                subtitle=f"{result.title}" + (
                    f" S{season_num:02d}E{episode_num:02d}" if season_num and episode_num else ""
                ),
            )
            if chosen:
                return chosen[1]

        # Fallback: manual URL
        if self.config.fallback_to_manual or not options:
            return self._prompt_manual_url(result, season_num, episode_num)

        return None

    def _prompt_manual_url(
        self,
        result: SearchResult,
        season: Optional[int],
        episode: Optional[int],
    ) -> Optional[str]:
        console.print()
        console.print(
            "  [pearl.warning]☠  No configured sources found.[/pearl.warning]"
        )
        console.print(
            "  [pearl.dim]Paste a direct URL (any yt-dlp compatible link) to play:[/pearl.dim]"
        )
        if season and episode:
            console.print(
                f"  [pearl.dim]Target: {result.title} S{season:02d}E{episode:02d}[/pearl.dim]"
            )
        elif result.media_type == MediaType.MOVIE:
            console.print(f"  [pearl.dim]Target: {result.title}[/pearl.dim]")
        console.print()
        try:
            url = console.input("  [pearl.cursor]⚓  URL ❯[/pearl.cursor]  ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        return url if url else None

    def show_playing(self, url: str, title: str) -> None:
        phrase = random.choice(PLAY_PHRASES)
        console.print()
        console.print(Rule(f"[pearl.secondary]⚓  {phrase}  ⚓[/pearl.secondary]", style="red"))
        console.print(f"  [pearl.primary]Title:[/pearl.primary]  [pearl.tertiary]{title}[/pearl.tertiary]")
        console.print(f"  [pearl.primary]URL:  [/pearl.primary]  [pearl.url]{url}[/pearl.url]")
        console.print()

    def show_error(self, message: str) -> None:
        phrase = random.choice(ERROR_PHRASES)
        console.print(
            f"\n  [pearl.error]☠  {phrase}[/pearl.error]\n"
            f"  [pearl.dim]{message}[/pearl.dim]\n"
        )

    def show_info(self, message: str) -> None:
        console.print(f"  [pearl.primary]⚓[/pearl.primary]  {message}")

    def show_success(self, message: str) -> None:
        console.print(f"  [pearl.success]✓[/pearl.success]  {message}")

    def confirm(self, prompt: str) -> bool:
        try:
            ans = console.input(
                f"  [pearl.cursor]⚓[/pearl.cursor]  {prompt} [pearl.dim][y/N][/pearl.dim]  "
            ).strip().lower()
            return ans in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    def show_history(self, entries: list[dict]) -> None:
        if not entries:
            console.print("\n  [pearl.dim]No treasure in the ship's log yet.[/pearl.dim]\n")
            return

        console.print()
        console.print(Rule("[pearl.secondary]☠  Ship's Log  ☠[/pearl.secondary]", style="red"))
        console.print()

        t = Table(
            box=box.SIMPLE,
            show_header=True,
            header_style="pearl.primary",
            border_style="pearl.border",
            pad_edge=False,
        )
        t.add_column("#", style="pearl.dim", width=4)
        t.add_column("Title", style="pearl.primary", min_width=30)
        t.add_column("Type", style="pearl.dim", width=8)
        t.add_column("When", style="pearl.dim", width=16)

        for i, entry in enumerate(reversed(entries[-30:]), 1):
            t.add_row(
                str(i),
                entry.get("title", ""),
                entry.get("type", ""),
                entry.get("when", ""),
            )

        console.print(t)
        console.print()

    # ──────────────────────────────────────────────────────────────────────────
    # Private rendering helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _render_results(
        self,
        results: list[SearchResult],
        cursor: int,
        page_size: int,
        query: str,
        quality: Optional[str],
    ) -> None:
        console.clear()
        console.print(BANNER, style="pearl.secondary", highlight=False)
        console.print(
            Rule(f"[pearl.secondary]☠  Search Results  ☠[/pearl.secondary]", style="red")
        )
        console.print(
            f"  [pearl.dim]Query:[/pearl.dim] [pearl.tertiary]{query}[/pearl.tertiary]"
            + (f"  [pearl.quality]{quality}[/pearl.quality]" if quality else "")
            + f"  [pearl.dim]({len(results)} results)[/pearl.dim]"
        )
        console.print()

        # Windowed view
        half = page_size // 2
        start = max(0, min(cursor - half, len(results) - page_size))
        end = min(start + page_size, len(results))
        visible = results[start:end]

        for i, r in enumerate(visible):
            actual_idx = start + i
            row = _render_result_row(actual_idx, r, actual_idx == cursor, cursor)
            console.print(row)
            # Show brief snippet under cursor
            if actual_idx == cursor and r.overview:
                snip = r.short_overview(80)
                console.print(f"       [pearl.dim]{snip}[/pearl.dim]")

        console.print()
        console.print(
            "  " + _keybind_bar([
                ("↑↓", "Navigate"),
                ("Enter", "Select"),
                ("1-9", "Quick pick"),
                ("Q/Esc", "Back"),
            ])
        )

    def _render_seasons(
        self,
        seasons: list[SeasonInfo],
        cursor: int,
        show_title: str,
    ) -> None:
        console.clear()
        console.print(BANNER, style="pearl.secondary", highlight=False)
        console.print(Rule(f"[pearl.secondary]☠  Seasons  ☠[/pearl.secondary]", style="red"))
        console.print(
            f"  [pearl.primary]{show_title}[/pearl.primary]  "
            f"[pearl.dim]— Pick your season, Cap'n[/pearl.dim]"
        )
        console.print()

        for i, s in enumerate(seasons):
            row = _render_season_row(i, s, i == cursor)
            console.print(row)

        console.print()
        console.print(
            "  " + _keybind_bar([("↑↓", "Navigate"), ("Enter", "Select"), ("B/Esc", "Back")])
        )

    def _render_episodes(
        self,
        episodes: list[EpisodeInfo],
        cursor: int,
        show_title: str,
        season: SeasonInfo,
    ) -> None:
        page_size = min(25, self._terminal_height() - 12)
        half = page_size // 2
        start = max(0, min(cursor - half, len(episodes) - page_size))
        end = min(start + page_size, len(episodes))
        visible = episodes[start:end]

        console.clear()
        console.print(BANNER, style="pearl.secondary", highlight=False)
        console.print(Rule(f"[pearl.secondary]☠  Episodes  ☠[/pearl.secondary]", style="red"))
        console.print(
            f"  [pearl.primary]{show_title}[/pearl.primary]  "
            f"[pearl.dim]—[/pearl.dim]  [pearl.tertiary]{season.label()}[/pearl.tertiary]"
        )
        console.print()

        for i, ep in enumerate(visible):
            actual = start + i
            row = _render_episode_row(actual, ep, actual == cursor)
            console.print(row)
            if actual == cursor and ep.overview:
                snip = ep.overview[:80]
                if len(ep.overview) > 80:
                    snip = snip.rsplit(" ", 1)[0] + "…"
                console.print(f"       [pearl.dim]{snip}[/pearl.dim]")

        console.print()
        console.print(
            "  " + _keybind_bar([("↑↓", "Navigate"), ("Enter", "Play"), ("B/Esc", "Back")])
        )

    def _pick_from_list(
        self,
        items: list[T],
        label_fn: Callable[[T], str],
        title: str,
        subtitle: str = "",
    ) -> Optional[T]:
        cursor = 0

        while True:
            console.clear()
            console.print(BANNER, style="pearl.secondary", highlight=False)
            console.print(Rule(f"[pearl.secondary]☠  {title}  ☠[/pearl.secondary]", style="red"))
            if subtitle:
                console.print(f"  [pearl.dim]{subtitle}[/pearl.dim]")
            console.print()

            for i, item in enumerate(items):
                prefix = " ❯ " if i == cursor else "   "
                label = label_fn(item)
                style = "pearl.selected" if i == cursor else "pearl.primary"
                console.print(f"  [pearl.dim]{i + 1:>2}.[/pearl.dim] [{style}]{prefix}{label}[/{style}]")

            console.print()
            console.print(
                "  " + _keybind_bar([("↑↓", "Navigate"), ("Enter", "Select"), ("B/Esc", "Cancel")])
            )

            key = _get_key()
            if key in (KEY_UP,) and cursor > 0:
                cursor -= 1
            elif key in (KEY_DOWN,) and cursor < len(items) - 1:
                cursor += 1
            elif key in (KEY_ENTER, KEY_ENTER2):
                return items[cursor]
            elif key in (KEY_Q, KEY_QUIT, KEY_ESC, KEY_BACK):
                return None
            elif key.isdigit() and int(key) > 0:
                n = int(key) - 1
                if 0 <= n < len(items):
                    cursor = n

    def _print_help_quick(self) -> None:
        console.print(
            "  [pearl.dim]Commands:[/pearl.dim]\n"
            "    [pearl.primary]pearl search[/pearl.primary] [pearl.tertiary]\"Breaking Bad\" 1080p[/pearl.tertiary]   — Search for content\n"
            "    [pearl.primary]pearl play[/pearl.primary]   [pearl.tertiary]<url>[/pearl.tertiary]                   — Play a URL directly\n"
            "    [pearl.primary]pearl log[/pearl.primary]                              — View ship's log (history)\n"
            "    [pearl.primary]pearl config[/pearl.primary]                           — Open config in editor\n"
            "    [pearl.primary]pearl sources[/pearl.primary]                          — Show configured sources\n"
            "    [pearl.primary]pearl help[/pearl.primary]                             — Full help\n"
        )

    @staticmethod
    def _terminal_height() -> int:
        try:
            return os.get_terminal_size().lines
        except Exception:
            return 40
