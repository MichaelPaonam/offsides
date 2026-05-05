"""Shared manifest helpers for video metadata tracking."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "data" / "highlights" / "manifest.json"


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def save_manifest(entries: list[dict]) -> None:
    entries.sort(key=lambda e: (e.get("date", ""), e.get("home_team", "")))
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def append_to_manifest(entry: dict) -> None:
    entries = load_manifest()
    existing_files = {e["file"] for e in entries}
    if entry["file"] not in existing_files:
        entries.append(entry)
        save_manifest(entries)
