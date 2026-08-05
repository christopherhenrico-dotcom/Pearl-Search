"""Pirate ASCII art and theme elements for Pearl."""

BANNER = r"""
██████╗ ███████╗ █████╗ ██████╗ ██╗     
██╔══██╗██╔════╝██╔══██╗██╔══██╗██║     
██████╔╝█████╗  ███████║██████╔╝██║     
██╔═══╝ ██╔══╝  ██╔══██║██╔══██╗██║     
██║     ███████╗██║  ██║██║  ██║███████╗
╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
"""

SKULL = r"""
    ░░░░░░░░░░░░░
  ░░  ░░░░░░░░  ░░
 ░░  ░░        ░░  ░░
░░░  ░░  ████  ░░  ░░░
░░░  ░░  ████  ░░  ░░░
░░░░░░░░░░░░░░░░░░░░░░
░░░  ████░░████  ░░░░░
░░░░░░░░░░░░░░░░░░░░░░
  ░░░░░░░░░░░░░░░░░░
    ░  ░░░  ░░░  ░
"""

SKULL_SMALL = r"""
  ☠  ☠  ☠
"""

JOLLY_ROGER = r"""
     .-.
    (o o)    PEARL — THE SEVEN SEAS MEDIA CLI
    | O |    v{version}
   /|---|\ 
  / |   | \ 
"""

CROSSBONES = "⚓  ☠  ⚓"

DIVIDER = "─" * 72

WAVE = "〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰〰"

SAIL = r"""
    |
   /|\
  / | \
 /  |  \
/   |   \
---------
"""

# Pirate phrases for various actions
SEARCH_PHRASES = [
    "Scanning the horizon for treasure...",
    "Sending lookouts up the crow's nest...",
    "Consulting the ancient sea charts...",
    "Navigating the digital seas...",
    "Hoisting the search flag...",
]

PLAY_PHRASES = [
    "Batten down the hatches — streaming commences!",
    "All hands on deck — launching the galleon!",
    "Fire the cannons — VLC away!",
    "Raising anchor — setting sail for your content!",
    "The plunder begins!",
]

LOADING_PHRASES = [
    "Keel-hauling the data...",
    "Swabbing the poop deck...",
    "Counting the doubloons...",
    "Reading Davy Jones' manifest...",
    "Charting the course...",
]

ERROR_PHRASES = [
    "Blimey! Something went awry!",
    "Walk the plank — an error occurred!",
    "Shiver me timbers!",
    "Scallywag error detected!",
    "The Kraken interfered!",
]

EMPTY_PHRASES = [
    "No treasure found in these waters, Cap'n.",
    "The seas be empty here. Try different coordinates.",
    "Davy Jones kept this one. Try another search.",
    "Not a soul on the horizon.",
]


def get_full_banner(version: str = "1.0.0") -> str:
    jolly = JOLLY_ROGER.format(version=version)
    return f"{BANNER}\n{jolly}\n{CROSSBONES}"
