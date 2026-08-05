"""Pearl CLI — command entry points."""

from __future__ import annotations
import sys
import os
import random
from typing import Optional

import click
from rich.console import Console
from rich.rule import Rule
from rich.panel import Panel
from rich.table import Table
from rich import box

from . import __version__
from .config import load_config, open_config_in_editor, get_config_path, write_default_config
from .tui.theme import RICH_PIRATE
from .tui.navigator import Navigator, console
from .ascii_art import get_full_banner, DIVIDER, SKULL, CROSSBONES, WAVE
from .search.ddg import DuckDuckGoSearch
from .search.tmdb import TMDBSearch
from .search.base import MediaType, SearchResult
from .player import Player, PlayerError
from .history import record_search, record_play, load_history, clear_history
from .resolver import Resolver

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "max_content_width": 100}


# ─────────────────────────────────────────────────────────────────────────────
# Root group
# ─────────────────────────────────────────────────────────────────────────────

@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(__version__, "-V", "--version", message="Pearl %(version)s  ☠")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    \b
    ☠  Pearl — The Pirate's Media CLI  ☠
    ─────────────────────────────────────
    Search for any content and play it with VLC.
    Configure sources in ~/.config/pearl/config.toml

    \b
    Examples:
      pearl search "Breaking Bad" 1080p
      pearl search "Inception" --type movie
      pearl play https://example.com/video.mp4
      pearl log
      pearl config
    """
    if ctx.invoked_subcommand is None:
        cfg = load_config()
        nav = Navigator(cfg)
        if cfg.show_skull:
            nav.show_welcome()
        else:
            console.print(get_full_banner(__version__), style="pearl.secondary", highlight=False)
        click.echo(ctx.get_help())


# ─────────────────────────────────────────────────────────────────────────────
# search
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("search")
@click.argument("query", nargs=-1, required=False)
@click.option(
    "--quality", "-q", default=None,
    type=click.Choice(["480p", "720p", "1080p", "4k", "any"], case_sensitive=False),
    help="Preferred quality (overrides config default).",
)
@click.option(
    "--type", "-t", "media_type", default=None,
    type=click.Choice(["movie", "tv", "any"], case_sensitive=False),
    help="Filter by media type.",
)
@click.option(
    "--provider", "-p", default=None,
    type=click.Choice(["ddg", "tmdb"], case_sensitive=False),
    help="Search provider (overrides config).",
)
@click.option(
    "--no-tui", is_flag=True, default=False,
    help="Print raw results without interactive navigation.",
)
def search_cmd(
    query: tuple,
    quality: Optional[str],
    media_type: Optional[str],
    provider: Optional[str],
    no_tui: bool,
) -> None:
    """
    Search for movies or TV shows.

    \b
    Examples:
      pearl search "breaking bad"
      pearl search "inception" 1080p
      pearl search "the wire" --type tv
      pearl search "dune" --quality 4k --provider tmdb
    
    QUERY may include a trailing quality token:
      pearl search "interstellar 1080p"
    """
    cfg = load_config()
    nav = Navigator(cfg)

    # Parse query
    raw_query = " ".join(query).strip() if query else ""

    # Extract trailing quality from query if not set via flag
    if not quality and raw_query:
        tokens = raw_query.rsplit(None, 1)
        if len(tokens) == 2:
            last = tokens[1].lower()
            if last.rstrip("p") in ("480", "720", "1080", "4k", "4") or last == "any":
                raw_query = tokens[0].strip()
                quality = tokens[1]

    # Interactive prompt if no query given
    if not raw_query:
        if no_tui:
            console.print("[pearl.error]Error: provide a QUERY argument.[/pearl.error]")
            sys.exit(1)
        nav.show_welcome()
        result = nav.prompt_search()
        if not result:
            return
        raw_query, quality = result[0], result[1] or quality

    effective_quality = quality or cfg.default_quality
    effective_provider = provider or cfg.search_provider

    nav.show_searching(raw_query, effective_quality)

    # Run search
    results = _do_search(
        query=raw_query,
        quality=effective_quality,
        media_hint=media_type,
        provider=effective_provider,
        cfg=cfg,
    )

    if cfg.history_enabled:
        record_search(raw_query, len(results), cfg)

    if no_tui:
        _print_results_plain(results)
        return

    # Interactive result selection loop
    _interactive_browse(nav, results, raw_query, effective_quality, cfg)


def _do_search(
    query: str,
    quality: Optional[str],
    media_hint: Optional[str],
    provider: str,
    cfg,
) -> list[SearchResult]:
    """Run the search and return results."""
    if provider == "tmdb":
        if not cfg.has_tmdb:
            console.print(
                "\n  [pearl.warning]☠  TMDB provider requires an API key.[/pearl.warning]\n"
                "  Add it to [pearl.primary]~/.config/pearl/config.toml[/pearl.primary] under [tmdb] api_key\n"
                "  Get a free key: https://www.themoviedb.org/settings/api\n"
                "\n  [pearl.dim]Falling back to DuckDuckGo...[/pearl.dim]\n"
            )
            provider = "ddg"
        else:
            try:
                backend = TMDBSearch(
                    api_key=cfg.tmdb_api_key,
                    language=cfg.get("search", "language", default="en-US"),
                    timeout=12,
                )
                return backend.search(query, quality=quality, media_hint=media_hint)
            except Exception as exc:
                console.print(
                    f"\n  [pearl.warning]TMDB search failed: {exc}. Falling back to DDG.[/pearl.warning]\n"
                )

    # DuckDuckGo (default)
    try:
        backend = DuckDuckGoSearch(max_results=cfg.max_results, timeout=12)
        return backend.search(query, quality=quality, media_hint=media_hint)
    except Exception as exc:
        console.print(f"\n  [pearl.error]Search failed: {exc}[/pearl.error]\n")
        return []


def _interactive_browse(
    nav: Navigator,
    results: list[SearchResult],
    query: str,
    quality: Optional[str],
    cfg,
) -> None:
    """Full interactive browse session: results → seasons → episodes → source → play."""
    player = Player(cfg)

    while True:
        selected = nav.pick_result(results, query, quality)
        if selected is None:
            return  # User quit

        # TV Show — fetch seasons & episodes
        if selected.media_type == MediaType.TV:
            seasons = _fetch_seasons(selected, cfg, nav)

            if seasons is None:
                # TMDB unavailable or user hit back; let them pick manually
                _play_result(nav, player, selected, cfg, quality)
                continue

            if not seasons:
                # No structured season data; go straight to play
                _play_result(nav, player, selected, cfg, quality)
                continue

            while True:
                season = nav.pick_season(seasons, selected.title)
                if season is None:
                    break  # Back to results

                # Fetch episodes
                episodes = _fetch_episodes(selected, season.number, cfg, nav)

                if not episodes:
                    # No episodes; play at season level
                    _play_result(nav, player, selected, cfg, quality,
                                  season_num=season.number)
                    continue

                while True:
                    episode = nav.pick_episode(episodes, selected.title, season)
                    if episode is None:
                        break  # Back to seasons

                    # Source selection & play
                    url = nav.pick_source(
                        cfg.servers, selected,
                        season_num=season.number,
                        episode_num=episode.number,
                    )
                    if url:
                        ep_title = (
                            f"{selected.title} S{season.number:02d}E{episode.number:02d}"
                            + (f" — {episode.title}" if episode.title else "")
                        )
                        _launch(nav, player, url, ep_title, quality, cfg)
        else:
            # Movie or unknown
            _play_result(nav, player, selected, cfg, quality)


def _fetch_seasons(result: SearchResult, cfg, nav: Navigator):
    """Try to get seasons. Returns list or None (skip to play)."""
    if not cfg.has_tmdb:
        return None  # No structured data available without TMDB

    try:
        backend = TMDBSearch(api_key=cfg.tmdb_api_key)
        seasons = backend.get_seasons(result)
        return seasons
    except Exception:
        return None


def _fetch_episodes(result: SearchResult, season_num: int, cfg, nav: Navigator):
    """Fetch episodes for a season."""
    if not cfg.has_tmdb:
        return []
    try:
        backend = TMDBSearch(api_key=cfg.tmdb_api_key)
        return backend.get_episodes(result, season_num)
    except Exception:
        return []


def _play_result(
    nav: Navigator,
    player: Player,
    result: SearchResult,
    cfg,
    quality: Optional[str],
    season_num: Optional[int] = None,
    episode_num: Optional[int] = None,
) -> None:
    """Pick source and play a result directly."""
    url = nav.pick_source(
        cfg.servers, result,
        season_num=season_num,
        episode_num=episode_num,
    )
    if url:
        title_parts = [result.title]
        if season_num and episode_num:
            title_parts.append(f"S{season_num:02d}E{episode_num:02d}")
        _launch(nav, player, url, " ".join(title_parts), quality, cfg)


def _launch(
    nav: Navigator,
    player: Player,
    url: str,
    title: str,
    quality: Optional[str],
    cfg,
) -> None:
    """Launch playback and record to history."""
    nav.show_playing(url, title)
    try:
        player.play(url, title=title, quality=quality)
        if cfg.history_enabled:
            record_play(title, url, cfg)
    except PlayerError as exc:
        nav.show_error(str(exc))


def _print_results_plain(results: list[SearchResult]) -> None:
    """Print results as plain text (--no-tui mode)."""
    if not results:
        console.print("[pearl.warning]No results found.[/pearl.warning]")
        return
    for i, r in enumerate(results, 1):
        icon = "🎬" if r.media_type == MediaType.MOVIE else ("📺" if r.media_type == MediaType.TV else "  ")
        year = f" ({r.year})" if r.year else ""
        console.print(f"[pearl.dim]{i:>2}.[/pearl.dim] {icon} [pearl.primary]{r.title}[/pearl.primary]{year}")
        console.print(f"    [pearl.url]{r.url}[/pearl.url]")
        if r.overview:
            console.print(f"    [pearl.dim]{r.short_overview(80)}[/pearl.dim]")


# ─────────────────────────────────────────────────────────────────────────────
# play
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("play")
@click.argument("url")
@click.option("--title", "-t", default="", help="Title to display in VLC.")
@click.option(
    "--quality", "-q", default=None,
    type=click.Choice(["480p", "720p", "1080p", "4k", "any"], case_sensitive=False),
    help="Preferred quality (used for yt-dlp format selection).",
)
@click.option(
    "--no-ytdlp", is_flag=True, default=False,
    help="Skip yt-dlp extraction and pass URL directly to VLC.",
)
def play_cmd(url: str, title: str, quality: Optional[str], no_ytdlp: bool) -> None:
    """
    Play a URL directly.

    \b
    Examples:
      pearl play https://www.youtube.com/watch?v=dQw4w9WgXcQ
      pearl play https://example.com/movie.mp4 --title "My Movie"
      pearl play https://vimeo.com/123456789 --quality 1080p
    
    Any yt-dlp compatible URL is supported. See: https://github.com/yt-dlp/yt-dlp
    """
    cfg = load_config()
    nav = Navigator(cfg)
    player = Player(cfg)
    effective_quality = quality or cfg.default_quality
    nav.show_playing(url, title or url)

    try:
        player.play(url, title=title, quality=effective_quality, try_ytdlp=not no_ytdlp)
        nav.show_success("VLC launched. Enjoy the plunder!")
        if cfg.history_enabled:
            record_play(title or url, url, cfg)
    except PlayerError as exc:
        nav.show_error(str(exc))
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# config
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("config")
@click.option("--show", is_flag=True, default=False, help="Print config file path.")
@click.option("--reset", is_flag=True, default=False, help="Reset config to defaults.")
def config_cmd(show: bool, reset: bool) -> None:
    """Open the Pearl config file in your editor."""
    cfg_path = get_config_path()

    if show:
        console.print(f"  [pearl.url]{cfg_path}[/pearl.url]")
        return

    if reset:
        if click.confirm("  Reset config to defaults?", default=False):
            write_default_config()
            console.print(f"  [pearl.success]✓[/pearl.success]  Config reset: {cfg_path}")
        return

    console.print(
        f"\n  [pearl.primary]☠  Opening config:[/pearl.primary]  [pearl.url]{cfg_path}[/pearl.url]\n"
    )
    open_config_in_editor()


# ─────────────────────────────────────────────────────────────────────────────
# sources
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("sources")
def sources_cmd() -> None:
    """List your configured media sources."""
    cfg = load_config()

    console.print()
    console.print(Rule("[pearl.secondary]☠  Configured Sources  ☠[/pearl.secondary]", style="red"))
    console.print()

    servers = cfg.servers

    if not servers:
        console.print(
            "  [pearl.warning]No sources configured, Cap'n.[/pearl.warning]\n"
            "\n"
            "  Add sources to [pearl.primary]~/.config/pearl/config.toml[/pearl.primary]\n"
            "  under [pearl.tertiary][[sources.servers]][/pearl.tertiary] — see the template for examples.\n"
            "\n"
            "  Sources use yt-dlp to extract streams, so any yt-dlp-compatible\n"
            "  URL template works. See: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md\n"
        )
        return

    t = Table(
        box=box.HEAVY_HEAD,
        show_header=True,
        header_style="pearl.primary",
        border_style="pearl.border",
        pad_edge=True,
    )
    t.add_column("#", style="pearl.dim", width=4)
    t.add_column("Name", style="pearl.primary", min_width=20)
    t.add_column("Template", style="pearl.url", min_width=40)
    t.add_column("Priority", style="pearl.dim", width=10)

    for i, s in enumerate(servers, 1):
        t.add_row(
            str(i),
            s.get("name", "Unnamed"),
            s.get("url_template", ""),
            str(s.get("priority", i)),
        )

    console.print(t)
    console.print()
    console.print(
        f"  [pearl.dim]Rotation strategy:[/pearl.dim] "
        f"[pearl.primary]{cfg.rotation_strategy}[/pearl.primary]"
    )
    console.print(
        f"  [pearl.dim]Fallback to manual URL:[/pearl.dim] "
        f"[pearl.primary]{cfg.fallback_to_manual}[/pearl.primary]"
    )
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# log  (ship's log / history)
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("log")
@click.option("--clear", is_flag=True, default=False, help="Clear all history.")
@click.option("--limit", "-n", default=30, show_default=True, help="Number of entries to show.")
def log_cmd(clear: bool, limit: int) -> None:
    """View or clear your ship's log (play/search history)."""
    cfg = load_config()

    if clear:
        if click.confirm("  Clear all ship's log entries?", default=False):
            clear_history()
            console.print("  [pearl.success]✓[/pearl.success]  Ship's log cleared.")
        return

    entries = load_history(cfg.max_history)
    nav = Navigator(cfg)
    nav.show_history(entries[-limit:])


# ─────────────────────────────────────────────────────────────────────────────
# status / doctor
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("doctor")
def doctor_cmd() -> None:
    """Check Pearl's dependencies and configuration."""
    cfg = load_config()
    player = Player(cfg)
    deps = player.check_dependencies()

    console.print()
    console.print(Rule("[pearl.secondary]☠  Pearl Doctor  ☠[/pearl.secondary]", style="red"))
    console.print()

    # Dependencies
    for dep, ok in deps.items():
        status = "[pearl.success]✓  found[/pearl.success]" if ok else "[pearl.error]✗  MISSING[/pearl.error]"
        console.print(f"  [pearl.primary]{dep:<12}[/pearl.primary]  {status}")

    console.print()

    # Config
    cfg_path = get_config_path()
    console.print(f"  [pearl.dim]Config:[/pearl.dim]     [pearl.url]{cfg_path}[/pearl.url]")
    console.print(f"  [pearl.dim]Provider:[/pearl.dim]   [pearl.primary]{cfg.search_provider}[/pearl.primary]")
    console.print(f"  [pearl.dim]Quality:[/pearl.dim]    [pearl.primary]{cfg.default_quality}[/pearl.primary]")
    console.print(f"  [pearl.dim]Player:[/pearl.dim]     [pearl.primary]{cfg.player_command}[/pearl.primary]")
    console.print(f"  [pearl.dim]TMDB key:[/pearl.dim]   " + (
        "[pearl.success]configured[/pearl.success]"
        if cfg.has_tmdb else
        "[pearl.dim]not set (optional)[/pearl.dim]"
    ))
    console.print(f"  [pearl.dim]Sources:[/pearl.dim]    [pearl.primary]{len(cfg.servers)} configured[/pearl.primary]")
    console.print()

    if not deps.get("vlc"):
        console.print("  [pearl.warning]⚠  Install VLC:    sudo pacman -S vlc[/pearl.warning]")
    if not deps.get("yt-dlp"):
        console.print("  [pearl.warning]⚠  Install yt-dlp: sudo pacman -S yt-dlp[/pearl.warning]")

    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# help
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("help")
def help_cmd() -> None:
    """Show detailed help and usage guide."""
    cfg = load_config()
    nav = Navigator(cfg)
    nav.show_welcome()

    console.print(Rule("[pearl.secondary]☠  Full Command Reference  ☠[/pearl.secondary]", style="red"))
    console.print()

    cmds = [
        ("pearl search \"<query>\"", "Interactive search — select result, season, episode, then play"),
        ("pearl search \"<query>\" 1080p", "Search with quality filter (720p, 1080p, 4k, any)"),
        ("pearl search \"<q>\" --type movie", "Limit to movies only (movie | tv | any)"),
        ("pearl search \"<q>\" --provider tmdb", "Use TMDB backend (requires API key in config)"),
        ("pearl search \"<q>\" --no-tui", "Print raw results without interactive navigation"),
        ("pearl play <url>", "Play any URL directly via VLC (+ yt-dlp extraction)"),
        ("pearl play <url> --no-ytdlp", "Pass URL straight to VLC without yt-dlp"),
        ("pearl log", "View search + play history (ship's log)"),
        ("pearl log --clear", "Clear all history"),
        ("pearl sources", "List configured media source servers"),
        ("pearl config", "Open config file in $EDITOR"),
        ("pearl config --reset", "Reset config to defaults"),
        ("pearl doctor", "Check dependencies and configuration"),
    ]

    t = Table(
        box=box.SIMPLE,
        show_header=False,
        pad_edge=False,
        show_edge=False,
    )
    t.add_column("Command", style="pearl.primary", min_width=45)
    t.add_column("Description", style="pearl.dim")

    for cmd, desc in cmds:
        t.add_row(cmd, desc)

    console.print(t)
    console.print()
    console.print(
        "  [pearl.primary]Navigation keys:[/pearl.primary]  "
        "[pearl.key] ↑↓ [/pearl.key] Move  "
        "[pearl.key] Enter [/pearl.key] Select  "
        "[pearl.key] B/Esc [/pearl.key] Back  "
        "[pearl.key] Q [/pearl.key] Quit\n"
    )
    console.print(
        "  [pearl.dim]Config file:[/pearl.dim] [pearl.url]~/.config/pearl/config.toml[/pearl.url]\n"
        "  [pearl.dim]Free TMDB key:[/pearl.dim] https://www.themoviedb.org/settings/api\n"
        "  [pearl.dim]yt-dlp sites:[/pearl.dim] https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n\n  [pearl.secondary]☠  Fare thee well, Cap'n. Until next tide.  ☠[/pearl.secondary]\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
