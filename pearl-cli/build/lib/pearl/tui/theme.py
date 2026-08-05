"""Color theme and styled printing for Pearl."""

from __future__ import annotations
from dataclasses import dataclass
from rich.style import Style
from rich.theme import Theme as RichTheme
from rich import box
from rich.box import Box


@dataclass
class Theme:
    name: str
    primary: str        # Main accent (gold/amber)
    secondary: str      # Secondary accent (red)
    tertiary: str       # Tertiary (muted teal)
    text: str           # Normal text
    dim: str            # Dim/muted text
    highlight: str      # Selected item background
    error: str          # Error messages
    success: str        # Success messages
    warning: str        # Warnings
    border: str         # Box/panel borders
    title: str          # Titles and headers


PIRATE_THEME = Theme(
    name="pirate",
    primary="bold yellow",
    secondary="bold red",
    tertiary="bold cyan",
    text="white",
    dim="bright_black",
    highlight="on dark_red",
    error="bold red",
    success="bold green",
    warning="bold yellow",
    border="red",
    title="bold yellow",
)

MINIMAL_THEME = Theme(
    name="minimal",
    primary="bold white",
    secondary="bold blue",
    tertiary="cyan",
    text="white",
    dim="bright_black",
    highlight="on blue",
    error="bold red",
    success="bold green",
    warning="bold yellow",
    border="bright_black",
    title="bold white",
)

THEMES = {
    "pirate": PIRATE_THEME,
    "minimal": MINIMAL_THEME,
}

# Rich theme for use with rich.Console
RICH_PIRATE = RichTheme({
    "pearl.primary":    "bold yellow",
    "pearl.secondary":  "bold red",
    "pearl.tertiary":   "bold cyan",
    "pearl.text":       "white",
    "pearl.dim":        "bright_black",
    "pearl.error":      "bold red",
    "pearl.success":    "bold green",
    "pearl.warning":    "bold yellow",
    "pearl.border":     "red",
    "pearl.title":      "bold yellow",
    "pearl.skull":      "bold red",
    "pearl.selected":   "bold white on dark_red",
    "pearl.cursor":     "bold yellow",
    "pearl.url":        "underline cyan",
    "pearl.year":       "bright_black",
    "pearl.rating":     "yellow",
    "pearl.tv":         "bold cyan",
    "pearl.movie":      "bold magenta",
    "pearl.unknown":    "bright_black",
    "pearl.quality":    "bold green",
    "pearl.key":        "bold yellow on grey23",
    "pearl.source":     "italic bright_black",
})

# Decorative box for panels
SKULL_BOX: Box = box.HEAVY_HEAD


def get_theme(name: str) -> Theme:
    return THEMES.get(name, PIRATE_THEME)
