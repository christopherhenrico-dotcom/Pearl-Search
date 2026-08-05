"""Media player integration for Pearl — VLC + yt-dlp stream extraction."""

from __future__ import annotations
import subprocess
import shutil
import sys
import os
from typing import Optional

from rich.console import Console
from rich.theme import Theme

from .tui.theme import RICH_PIRATE

console = Console(theme=RICH_PIRATE, highlight=False)


class PlayerError(Exception):
    pass


def _which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def _require(cmd: str, install_hint: str) -> str:
    path = _which(cmd)
    if not path:
        raise PlayerError(
            f"'{cmd}' not found in PATH.\n  Install: {install_hint}"
        )
    return path


def _extract_with_ytdlp(url: str, quality: Optional[str] = None) -> str:
    """
    Use yt-dlp to extract a direct stream URL from the given URL.
    Returns a direct stream URL that VLC can consume.
    Raises PlayerError if extraction fails or yt-dlp is not installed.
    """
    ytdlp = _which("yt-dlp")
    if not ytdlp:
        # Try yt_dlp Python module
        try:
            import yt_dlp  # type: ignore
            return _extract_with_ytdlp_module(url, quality)
        except ImportError:
            raise PlayerError(
                "yt-dlp not found. Install: sudo pacman -S yt-dlp\n"
                "  or: pip install yt-dlp"
            )

    # Build format selection
    fmt = _build_format(quality)

    cmd = [ytdlp, "--get-url", "-f", fmt, "--no-playlist", url]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise PlayerError(f"yt-dlp failed:\n  {stderr}")

        stream_url = result.stdout.strip()
        if not stream_url:
            raise PlayerError("yt-dlp returned no stream URL.")

        # May return multiple URLs (video + audio); take the first
        return stream_url.splitlines()[0]
    except subprocess.TimeoutExpired:
        raise PlayerError("yt-dlp timed out extracting stream URL.")
    except FileNotFoundError:
        raise PlayerError("yt-dlp binary not found after detection.")


def _extract_with_ytdlp_module(url: str, quality: Optional[str]) -> str:
    """Extract stream URL using yt-dlp Python API."""
    import yt_dlp  # type: ignore

    fmt = _build_format(quality)
    ydl_opts = {
        "format": fmt,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise PlayerError("yt-dlp could not extract info from URL.")
        return info.get("url", url)


def _build_format(quality: Optional[str]) -> str:
    """Build yt-dlp format selector from quality string."""
    if not quality or quality.lower() == "any":
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    q = quality.lower().rstrip("p")
    height_map = {"4k": "2160", "2160": "2160", "1080": "1080", "720": "720", "480": "480"}
    height = height_map.get(q, "720")

    return (
        f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]"
        f"/bestvideo[height<={height}]+bestaudio"
        f"/best[height<={height}]"
        f"/best"
    )


class Player:
    """Handles media playback via VLC."""

    def __init__(self, config):
        self.config = config

    def play(
        self,
        url: str,
        title: str = "",
        quality: Optional[str] = None,
        try_ytdlp: bool = True,
    ) -> None:
        """
        Play a URL.
        
        Strategy:
        1. If VLC can handle the URL directly (http/https direct stream, local file),
           pass it straight to VLC.
        2. If yt-dlp is available and the URL looks like a webpage (not a direct
           stream), use yt-dlp to extract the stream URL first.
        3. Fall back to passing the URL directly to VLC.

        Raises PlayerError if VLC is not found.
        """
        vlc_cmd = self.config.player_command
        vlc_path = _which(vlc_cmd)
        if not vlc_path:
            raise PlayerError(
                f"VLC not found (looked for '{vlc_cmd}').\n"
                f"  Install: sudo pacman -S vlc"
            )

        stream_url = url

        # Try yt-dlp extraction for webpage-like URLs
        if try_ytdlp and self._looks_like_webpage(url):
            try:
                console.print(
                    "  [pearl.dim]Extracting stream via yt-dlp…[/pearl.dim]"
                )
                stream_url = _extract_with_ytdlp(url, quality)
                console.print(
                    f"  [pearl.success]✓[/pearl.success]  "
                    f"[pearl.dim]Stream extracted[/pearl.dim]"
                )
            except PlayerError as exc:
                # yt-dlp failed; pass URL directly to VLC and hope for the best
                console.print(
                    f"  [pearl.warning]⚠[/pearl.warning]  "
                    f"[pearl.dim]yt-dlp: {exc}. Passing URL directly to VLC.[/pearl.dim]"
                )
                stream_url = url

        # Build VLC command
        args = [vlc_path] + self.config.player_args

        if title:
            args += ["--meta-title", title]

        args.append(stream_url)

        try:
            if self.config.player_wait:
                subprocess.run(args, check=False)
            else:
                # Detach VLC from Pearl's process group so it runs independently
                kwargs: dict = {}
                if sys.platform != "win32":
                    kwargs["start_new_session"] = True
                subprocess.Popen(args, **kwargs)
        except FileNotFoundError:
            raise PlayerError(f"VLC binary not found at: {vlc_path}")
        except OSError as exc:
            raise PlayerError(f"Failed to launch VLC: {exc}")

    @staticmethod
    def _looks_like_webpage(url: str) -> bool:
        """Heuristic: does this URL look like a webpage vs. a direct stream?"""
        # Direct stream indicators
        stream_exts = (
            ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m3u8",
            ".ts", ".flv", ".wmv", ".mpg", ".mpeg",
        )
        lower = url.lower()
        if any(lower.endswith(ext) for ext in stream_exts):
            return False
        if "manifest" in lower or ".m3u" in lower:
            return False
        # Looks like a webpage if it's http/https and no stream extension
        return lower.startswith(("http://", "https://"))

    def check_dependencies(self) -> dict[str, bool]:
        """Check which dependencies are available."""
        vlc = bool(_which(self.config.player_command))
        ytdlp = bool(_which("yt-dlp"))
        if not ytdlp:
            try:
                import yt_dlp  # type: ignore
                ytdlp = True
            except ImportError:
                pass
        return {"vlc": vlc, "yt-dlp": ytdlp}
