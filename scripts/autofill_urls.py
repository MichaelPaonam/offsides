#!/usr/bin/env python3
"""
Offsides — Auto-fill YouTube URLs for UCL highlights

Searches YouTube via yt-dlp for each match in the CSV that has no URL,
and writes the top result back into the CSV.

Usage:
    source venv/bin/activate
    python scripts/autofill_urls.py

Options:
    --dry-run       Print what would be searched without modifying the CSV
    --delay 3       Seconds between searches to avoid rate limiting (default: 3)
    --start-row 0   Row index to start from (for resuming after interruption)

After running:
    1. Open data/match_urls/ucl_highlights.csv
    2. Spot-check 10-20 URLs to verify they point to correct highlights
    3. Delete any bad rows (wrong match, fan uploads, etc.)
    4. Run scripts/download_highlights.py

The script is resumable — re-running it only fills rows that still have empty URLs.
"""

import csv
import subprocess
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "match_urls" / "ucl_highlights.csv"
LOG_FILE = PROJECT_ROOT / "data" / "match_urls" / "autofill_log.txt"


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def build_search_query(row: dict) -> str:
    home = row.get("home_team", "").strip()
    away = row.get("away_team", "").strip()
    date = row.get("date", "").strip()
    season = row.get("season", "").strip()

    year_month = date[:7] if date else season

    query = f"UEFA Champions League highlights {home} vs {away} {year_month}"

    return query


def search_youtube(query: str, timeout: int = 30) -> tuple[str, str]:
    """Search YouTube via yt-dlp and return (url, title) of top result."""
    cmd = [
        "yt-dlp",
        f"ytsearch1:{query}",
        "--get-url",
        "--get-title",
        "--format", "best",
        "--no-download",
        "--no-playlist",
        "--socket-timeout", str(timeout),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                title = lines[0]
                url = lines[1]
                return url, title
        return "", ""
    except subprocess.TimeoutExpired:
        return "", ""
    except Exception:
        return "", ""


def get_video_id_url(query: str, timeout: int = 30) -> tuple[str, str]:
    """Alternative: get video ID and construct clean URL."""
    cmd = [
        "yt-dlp",
        f"ytsearch1:{query}",
        "--get-id",
        "--get-title",
        "--no-download",
        "--no-playlist",
        "--socket-timeout", str(timeout),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                title = lines[0]
                video_id = lines[1]
                url = f"https://www.youtube.com/watch?v={video_id}"
                return url, title
        return "", ""
    except subprocess.TimeoutExpired:
        return "", ""
    except Exception:
        return "", ""


def main():
    parser = argparse.ArgumentParser(description="Auto-fill YouTube URLs for UCL highlights")
    parser.add_argument("--dry-run", action="store_true", help="Print search queries without modifying CSV")
    parser.add_argument("--delay", type=int, default=3, help="Seconds between searches (default: 3)")
    parser.add_argument("--start-row", type=int, default=0, help="Row index to start from (for resuming)")
    args = parser.parse_args()

    if not CSV_PATH.exists():
        print(f"ERROR: CSV not found at {CSV_PATH}")
        print("Run scripts/generate_match_list.py first.")
        sys.exit(1)

    # Read all rows
    rows = []
    fieldnames = ["season", "stage", "matchday", "home_team", "away_team", "date", "youtube_url"]
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            fieldnames = list(reader.fieldnames)
        for row in reader:
            rows.append(row)

    total = len(rows)
    empty_urls = sum(1 for r in rows if not r.get("youtube_url", "").strip())

    log("=" * 60)
    log(f"Auto-fill YouTube URLs")
    log(f"CSV: {CSV_PATH}")
    log(f"Total rows: {total}")
    log(f"Rows needing URLs: {empty_urls}")
    log(f"Starting from row: {args.start_row}")
    log(f"Delay between searches: {args.delay}s")
    log(f"Dry run: {args.dry_run}")
    log("=" * 60)

    if args.dry_run:
        for i, row in enumerate(rows[args.start_row:], start=args.start_row):
            if row.get("youtube_url", "").strip():
                continue
            query = build_search_query(row)
            home = row.get("home_team", "")
            away = row.get("away_team", "")
            print(f"[{i}] {home} vs {away} → search: \"{query}\"")
        return

    stats = {"filled": 0, "failed": 0, "skipped": 0}

    for i, row in enumerate(rows[args.start_row:], start=args.start_row):
        if row.get("youtube_url", "").strip():
            stats["skipped"] += 1
            continue

        home = row.get("home_team", "")
        away = row.get("away_team", "")
        date = row.get("date", "")
        match_label = f"{home} vs {away} ({date})"

        query = build_search_query(row)
        log(f"[{i}/{total}] Searching: {match_label}")

        url, title = get_video_id_url(query)

        if url:
            rows[i]["youtube_url"] = url
            stats["filled"] += 1
            log(f"  FOUND: {title[:80]}")
            log(f"  URL: {url}")
        else:
            stats["failed"] += 1
            log(f"  NOT FOUND")

        # Write CSV after each successful find (resumable)
        if url:
            with open(CSV_PATH, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

        time.sleep(args.delay)

    # Final write
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log("=" * 60)
    log("Complete")
    log(f"  Filled:  {stats['filled']}")
    log(f"  Failed:  {stats['failed']}")
    log(f"  Skipped: {stats['skipped']} (already had URL)")
    log("=" * 60)
    print()
    print("NEXT STEP: Review the CSV and spot-check URLs before downloading.")
    print(f"  Open: {CSV_PATH}")
    print("  Then run: python scripts/download_highlights.py")


if __name__ == "__main__":
    main()
