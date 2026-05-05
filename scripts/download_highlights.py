#!/usr/bin/env python3
"""
Offsides — UEFA Champions League Highlights Downloader

Downloads YouTube highlight videos from a pre-curated CSV file.
Deterministic: same CSV = same downloads every time.

Usage:
    source venv/bin/activate
    python scripts/download_highlights.py

Requirements:
    - yt-dlp (pip install yt-dlp)
    - CSV file at data/match_urls/ucl_highlights.csv with YouTube URLs

Storage estimate (720p):
    - ~50-100MB per 10-minute highlight clip
    - ~250 matches × 75MB avg = ~18GB for both seasons

The script:
    - Reads the CSV for YouTube URLs
    - Skips rows with empty URLs
    - Skips already-downloaded videos (resumable)
    - Downloads at 720p max
    - Saves to data/highlights/{season}/{stage}/
    - Logs progress to data/highlights/download_log.txt
"""

import csv
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from manifest import append_to_manifest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "match_urls" / "ucl_highlights.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "highlights"
LOG_FILE = OUTPUT_DIR / "download_log.txt"

MAX_QUALITY = "720"
FORMAT_SPEC = f"bestvideo[height<={MAX_QUALITY}]+bestaudio/best[height<={MAX_QUALITY}]"
OUTPUT_TEMPLATE = "%(title)s [%(id)s].%(ext)s"


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_output_dir(season: str, stage: str) -> Path:
    safe_season = season.strip().replace("/", "-")
    safe_stage = stage.strip().replace(" ", "_")
    return OUTPUT_DIR / safe_season / safe_stage


def is_already_downloaded(output_dir: Path, youtube_url: str) -> bool:
    video_id = youtube_url.strip().split("v=")[-1].split("&")[0]
    if not video_id:
        return False
    for f in output_dir.iterdir() if output_dir.exists() else []:
        if video_id in f.name:
            return True
    return False


def download_video(youtube_url: str, output_dir: Path, match_label: str) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "yt-dlp",
        "--format", FORMAT_SPEC,
        "--output", str(output_dir / OUTPUT_TEMPLATE),
        "--no-overwrites",
        "--retries", "3",
        "--fragment-retries", "3",
        "--socket-timeout", "30",
        "--no-playlist",
        "--merge-output-format", "mp4",
        youtube_url.strip(),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode == 0:
            log(f"OK: {match_label}")
            return True
        else:
            log(f"FAIL: {match_label} — {result.stderr.strip()[:200]}")
            return False
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT: {match_label}")
        return False
    except Exception as e:
        log(f"ERROR: {match_label} — {e}")
        return False


def main():
    if not CSV_PATH.exists():
        print(f"ERROR: CSV not found at {CSV_PATH}")
        print("Create the CSV with columns: season,stage,matchday,home_team,away_team,date,youtube_url")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log("Starting download session")
    log(f"CSV: {CSV_PATH}")
    log(f"Output: {OUTPUT_DIR}")
    log(f"Quality: {MAX_QUALITY}p")
    log("=" * 60)

    stats = {"total": 0, "skipped_no_url": 0, "skipped_exists": 0, "downloaded": 0, "failed": 0}

    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            stats["total"] += 1
            youtube_url = row.get("youtube_url", "").strip()

            if not youtube_url:
                stats["skipped_no_url"] += 1
                continue

            season = row.get("season", "unknown")
            stage = row.get("stage", "unknown")
            home = row.get("home_team", "unknown")
            away = row.get("away_team", "unknown")
            date = row.get("date", "")
            match_label = f"{season} | {stage} | {home} vs {away} ({date})"

            output_dir = get_output_dir(season, stage)

            if is_already_downloaded(output_dir, youtube_url):
                log(f"SKIP (exists): {match_label}")
                stats["skipped_exists"] += 1
                continue

            log(f"DOWNLOADING: {match_label}")
            success = download_video(youtube_url, output_dir, match_label)

            if success:
                stats["downloaded"] += 1
                video_id = youtube_url.split("v=")[-1].split("&")[0]
                downloaded_file = None
                for f in output_dir.iterdir():
                    if video_id in f.name and f.suffix == ".mp4":
                        downloaded_file = f
                        break
                if downloaded_file:
                    rel_path = str(downloaded_file.relative_to(OUTPUT_DIR))
                    append_to_manifest({
                        "file": rel_path,
                        "season": season,
                        "stage": stage,
                        "matchday": row.get("matchday", ""),
                        "home_team": home,
                        "away_team": away,
                        "date": date,
                        "source": "youtube",
                        "source_id": video_id,
                    })
            else:
                stats["failed"] += 1

    log("=" * 60)
    log("Session complete")
    log(f"  Total rows:      {stats['total']}")
    log(f"  No URL (skipped): {stats['skipped_no_url']}")
    log(f"  Already exists:   {stats['skipped_exists']}")
    log(f"  Downloaded:       {stats['downloaded']}")
    log(f"  Failed:           {stats['failed']}")
    log("=" * 60)


if __name__ == "__main__":
    main()
