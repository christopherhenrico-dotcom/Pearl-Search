# ☠  Pearl — The Pirate's Media CLI

```
██████╗ ███████╗ █████╗ ██████╗ ██╗     
██╔══██╗██╔════╝██╔══██╗██╔══██╗██║     
██████╔╝█████╗  ███████║██████╔╝██║     
██╔═══╝ ██╔══╝  ██╔══██║██╔══██╗██║     
██║     ███████╗██║  ██║██║  ██║███████╗
╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
```

**Search for anything. Navigate seasons and episodes in the terminal. Play with VLC.**

Pearl is a source-agnostic, pirate-themed media CLI for Arch Linux. It searches for content
using DuckDuckGo (no API key required) or TMDB (optional, for structured show metadata), then
launches VLC with any URL you point it at — including anything supported by yt-dlp.

---

## Features

- 🔍 **Full-text search** via DuckDuckGo (no key) or TMDB (free key, structured season/episode browser)
- 📺 **Season & episode navigation** — arrow-key browser for TV shows (requires TMDB key)
- 🎬 **VLC playback** — yt-dlp extracts the stream, VLC plays it
- ⚙️ **Configurable sources** — define your own URL templates in `~/.config/pearl/config.toml`
- 🔄 **Server rotation** — priority or random rotation across configured sources
- 📜 **Ship's log** — search and play history
- ☠️ **Full pirate theme** — skull ASCII art, gold/red colors, pirate language throughout
- 🐚 **Shell completions** — Bash, Zsh, and Fish

---

## Requirements

| Dependency | Install (Arch) | Notes |
|---|---|---|
| Python 3.11+ | `sudo pacman -S python` | Required |
| VLC | `sudo pacman -S vlc` | Media player |
| yt-dlp | `sudo pacman -S yt-dlp` | Stream extraction |

---

## Installation

### From your custom mirror (pacman)

```bash
# 1. Add your mirror to /etc/pacman.conf:
# [pearl-mirror]
# Server = https://your-mirror.example.com/packages

# 2. Install:
sudo pacman -S pearl-cli
```

### From source (recommended for dev)

```bash
git clone https://github.com/yourname/pearl-cli
cd pearl-cli
bash install.sh
```

### Manual pip install

```bash
pip install --user .
# or with pipx (isolated):
pipx install .
```

Make sure `~/.local/bin` is in your `$PATH`:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## Quick Start

```bash
# Search — interactive TUI with arrow-key navigation
pearl search "Breaking Bad" 1080p
pearl search "Inception" --type movie
pearl search "The Wire" --type tv

# Play any URL directly
pearl play https://example.com/video.mp4
pearl play https://vimeo.com/123456789 --quality 1080p

# View history
pearl log

# Manage configuration
pearl config          # open in $EDITOR
pearl config --show   # print config file path

# List configured sources
pearl sources

# Check dependencies
pearl doctor

# Full help
pearl help
```

---

## Navigation

Inside interactive menus:

| Key | Action |
|---|---|
| `↑` / `↓` | Move cursor |
| `Enter` | Select |
| `1`–`9` | Quick jump to item |
| `B` / `Esc` | Go back |
| `Q` | Quit |

---

## Configuration

The config file lives at `~/.config/pearl/config.toml`. It is created automatically
on first run with all defaults and inline comments explaining every option.

```bash
pearl config   # opens in $EDITOR
```

### Configuring sources

Pearl is **completely source-agnostic**. You add your own URLs under `[[sources.servers]]`.
Pearl uses yt-dlp to extract the actual stream from whatever URL you provide, so any
[yt-dlp-supported site](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
works as a source.

**URL templates** let Pearl fill in the title, season, episode, IMDb ID, etc:

```toml
[[sources.servers]]
name = "My Server A"
url_template = "https://my-server.example.com/search/{query}"
priority = 1
enabled = true

[[sources.servers]]
name = "My Server B"
url_template = "https://other-server.example.com/tv/{imdb}/s{s}e{e}"
priority = 2
enabled = true

[[sources.servers]]
name = "My Server C"
url_template = "https://third.example.com/movie/{imdb}"
priority = 3
enabled = true
```

**Available template placeholders:**

| Placeholder | Value | Example |
|---|---|---|
| `{title}` | URL-encoded title | `Breaking+Bad` |
| `{title_raw}` | Raw title | `Breaking Bad` |
| `{year}` | Release year | `2008` |
| `{season}` | Season number | `3` |
| `{episode}` | Episode number | `7` |
| `{s}` | Zero-padded season | `03` |
| `{e}` | Zero-padded episode | `07` |
| `{s00e00}` | Combined | `S03E07` |
| `{imdb}` | IMDb ID (needs TMDB key) | `tt0903747` |
| `{tmdb}` | TMDB ID (needs TMDB key) | `1396` |
| `{query}` | URL-encoded search query | `breaking+bad` |

### Rotation strategy

```toml
[sources]
rotation = "priority"   # try servers in order; first working one wins
# rotation = "random"   # random server each time
fallback_to_manual = true  # if no servers configured, prompt user to paste a URL
```

### TMDB integration (optional but recommended for TV shows)

TMDB gives you a proper season/episode browser with titles, descriptions, and air dates.
Get a **free** API key at https://www.themoviedb.org/settings/api

```toml
[tmdb]
api_key = "your_key_here"
```

With a TMDB key, `pearl search "Breaking Bad"` will show:
```
Season 1  (7 episodes)  2008
Season 2  (13 episodes) 2009
...
→ Season 3
    E01 — No Más
    E02 — Caballo Sin Nombre
    ...
```

Without a key, Pearl shows web search results which you can click through to URLs.

---

## Shell Completions

```bash
# Bash
pearl --show-completion bash >> ~/.bash_completion

# Zsh
pearl --show-completion zsh >> ~/.zshrc

# Fish
pearl --show-completion fish > ~/.config/fish/completions/pearl.fish
```

Or if installed via the PKGBUILD, completions are installed automatically.

---

## Hosting on a Custom Mirror

### 1. Build the package

```bash
cd pearl-cli
# Update version in pyproject.toml and PKGBUILD
makepkg -s   # builds pearl-cli-1.0.0-1-any.pkg.tar.zst
```

### 2. Create a repo database

```bash
mkdir -p /srv/http/packages/x86_64
cp *.pkg.tar.zst /srv/http/packages/x86_64/
repo-add /srv/http/packages/x86_64/pearl-mirror.db.tar.gz \
         /srv/http/packages/x86_64/*.pkg.tar.zst
```

### 3. Serve it (nginx example)

```nginx
server {
    listen 80;
    server_name your-mirror.example.com;
    root /srv/http;
    autoindex on;
}
```

### 4. Users add to `/etc/pacman.conf`

```ini
[pearl-mirror]
Server = https://your-mirror.example.com/packages/$arch
```

```bash
sudo pacman -Sy pearl-cli
```

---

## Project Structure

```
pearl-cli/
├── pearl/
│   ├── cli.py          Main CLI commands (search, play, log, config, doctor)
│   ├── config.py       Config loading and defaults
│   ├── player.py       VLC launcher + yt-dlp stream extraction
│   ├── resolver.py     URL template resolver for configured sources
│   ├── history.py      Ship's log (search + play history)
│   ├── ascii_art.py    Pirate ASCII art and phrases
│   ├── search/
│   │   ├── base.py     Data types (SearchResult, SeasonInfo, EpisodeInfo)
│   │   ├── ddg.py      DuckDuckGo search backend (no API key)
│   │   └── tmdb.py     TMDB search backend (free API key)
│   └── tui/
│       ├── theme.py    Color theme and rich styles
│       └── navigator.py Full-screen interactive navigator
├── pyproject.toml      Package metadata and dependencies
├── PKGBUILD            Arch Linux package build file
├── install.sh          One-command installer for Arch Linux
└── README.md           This file
```

---

## License

MIT

---

*⚓  Fair winds and following seas, Cap'n.  ⚓*
