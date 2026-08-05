"""Ship's log — search and play history for Pearl."""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import HISTORY_FILE


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def load_history(max_entries: int = 500) -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        entries = data if isinstance(data, list) else []
        return entries[-max_entries:]
    except Exception:
        return []


def save_history(entries: list[dict], max_entries: int = 500) -> None:
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        trimmed = entries[-max_entries:]
        HISTORY_FILE.write_text(
            json.dumps(trimmed, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def record_search(query: str, result_count: int, config) -> None:
    if not config.history_enabled:
        return
    entries = load_history(config.max_history)
    entries.append({
        "type": "search",
        "title": query,
        "detail": f"{result_count} results",
        "when": _now(),
    })
    save_history(entries, config.max_history)


def record_play(title: str, url: str, config, media_type: str = "") -> None:
    if not config.history_enabled:
        return
    entries = load_history(config.max_history)
    entries.append({
        "type": media_type or "play",
        "title": title,
        "detail": url,
        "when": _now(),
    })
    save_history(entries, config.max_history)


def clear_history() -> None:
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
