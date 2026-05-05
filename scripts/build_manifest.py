#!/usr/bin/env python3
"""Build manifest.json by scanning downloaded videos and matching to CSV metadata.

Usage:
    python scripts/build_manifest.py
    python scripts/build_manifest.py --dry-run
"""

import argparse
import csv
import re
from pathlib import Path

from manifest import load_manifest, save_manifest, MANIFEST_PATH

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "match_urls" / "ucl_highlights.csv"
HIGHLIGHTS_DIR = PROJECT_ROOT / "data" / "highlights"

# Regex to extract YouTube video ID from filename: "... [VIDEO_ID].ext"
YT_ID_RE = re.compile(r"\[([a-zA-Z0-9_-]{11})\]\.[^.]+$")

# Regex to parse UEFA filename: "Home_vs_Away_YYYY-MM-DD.mp4"
UEFA_RE = re.compile(r"^(.+)_vs_(.+)_(\d{4}-\d{2}-\d{2})\.mp4$")


def load_csv_rows() -> list[dict]:
    with open(CSV_PATH) as f:
        return list(csv.DictReader(f))


def build_youtube_url_index(rows: list[dict]) -> dict[str, dict]:
    """Map video_id -> CSV row for YouTube-sourced matches."""
    index = {}
    for row in rows:
        url = row.get("youtube_url", "").strip()
        if not url:
            continue
        vid_id = url.split("v=")[-1].split("&")[0]
        if vid_id:
            index[vid_id] = row
    return index


def normalize_for_match(name: str) -> str:
    return name.lower().replace("_", " ").strip()


def find_csv_row_by_teams_date(rows: list[dict], home: str, away: str, date: str) -> dict | None:
    h = normalize_for_match(home)
    a = normalize_for_match(away)
    for row in rows:
        if row["date"] == date:
            rh = row["home_team"].lower().strip()
            ra = row["away_team"].lower().strip()
            if rh == h and ra == a:
                return row
            if rh == a and ra == h:
                return row
    return None


def build_entry_from_csv(rel_path: str, row: dict, source: str, **extra) -> dict:
    entry = {
        "file": rel_path,
        "season": row["season"],
        "stage": row["stage"],
        "matchday": row["matchday"],
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "date": row["date"],
        "source": source,
    }
    entry.update(extra)
    return entry


def build_manifest(rows: list[dict], dry_run: bool = False) -> list[dict]:
    yt_index = build_youtube_url_index(rows)
    entries = []
    unmatched = []

    for mp4 in sorted(HIGHLIGHTS_DIR.rglob("*.mp4")):
        rel = str(mp4.relative_to(HIGHLIGHTS_DIR))

        # Try YouTube match
        yt_match = YT_ID_RE.search(mp4.name)
        if yt_match:
            vid_id = yt_match.group(1)
            csv_row = yt_index.get(vid_id)
            if csv_row:
                entries.append(build_entry_from_csv(rel, csv_row, "youtube", source_id=vid_id))
                continue

        # Try UEFA match
        uefa_match = UEFA_RE.match(mp4.name)
        if uefa_match:
            home_raw, away_raw, date = uefa_match.groups()
            csv_row = find_csv_row_by_teams_date(rows, home_raw, away_raw, date)
            if csv_row:
                entries.append(build_entry_from_csv(rel, csv_row, "uefa"))
                continue

        # Unmatched
        unmatched.append(rel)
        entries.append({"file": rel, "matched": False})

    if unmatched:
        print(f"Warning: {len(unmatched)} files could not be matched to CSV:")
        for f in unmatched:
            print(f"  {f}")

    if dry_run:
        print(f"\nDry run: would write {len(entries)} entries to {MANIFEST_PATH}")
        for e in sorted(entries, key=lambda x: (x.get("date", ""), x.get("home_team", ""))):
            src = e.get("source", "?")
            matched = e.get("matched", True)
            label = f"[{src}]" if matched else "[UNMATCHED]"
            print(f"  {label} {e['file']}")
    else:
        save_manifest(entries)
        print(f"Wrote {len(entries)} entries to {MANIFEST_PATH}")

    return entries


def main():
    parser = argparse.ArgumentParser(description="Build video manifest from downloaded highlights")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be written without saving")
    args = parser.parse_args()

    rows = load_csv_rows()
    print(f"Loaded {len(rows)} CSV rows")

    mp4_count = len(list(HIGHLIGHTS_DIR.rglob("*.mp4")))
    print(f"Found {mp4_count} .mp4 files in {HIGHLIGHTS_DIR}")

    if mp4_count == 0:
        print("No videos to index.")
        return

    build_manifest(rows, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
