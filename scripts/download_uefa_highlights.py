#!/usr/bin/env python3
"""Download UCL highlights from UEFA.com for matches missing YouTube URLs.

Uses UEFA's public APIs to find match videos and downloads them via ffmpeg.
No authentication required.

Usage:
    python scripts/download_uefa_highlights.py
    python scripts/download_uefa_highlights.py --dry-run
    python scripts/download_uefa_highlights.py --start-row 10 --delay 15
"""

import argparse
import csv
import json

from manifest import append_to_manifest
import subprocess
import time
import urllib.request
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "match_urls" / "ucl_highlights.csv"
HIGHLIGHTS_DIR = PROJECT_ROOT / "data" / "highlights"
LOG_PATH = HIGHLIGHTS_DIR / "uefa_download_log.txt"

MATCH_API = "https://match.uefa.com/v5/matches"
EDITORIAL_API = "https://editorial.uefa.com/api/cachedsearch/build"
ACCESS_API = "https://mas.uefa.com/v1/access-rights"

UCL_COMPETITION_ID = "1"
HTTP_TIMEOUT = 15

# CSV team names → UEFA's internationalName equivalents
TEAM_ALIASES = {
    "psg": "paris",
    "red star belgrade": "crvena zvezda",
    "inter milan": "inter",
    "dinamo zagreb": "gnk dinamo",
    "bayern munich": "bayern münchen",
    "atletico madrid": "atleti",
    "dortmund": "b. dortmund",
    "rb leipzig": "leipzig",
    "club brugge": "club brugge",
    "slovan bratislava": "s. bratislava",
    "ac milan": "milan",
    "sporting cp": "sporting cp",
    "sparta prague": "sparta praha",
    "shakhtar donetsk": "shakhtar",
    "bayer leverkusen": "leverkusen",
    "sturm graz": "sturm graz",
}


def log(msg: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def http_get_json(url: str) -> dict | list | None:
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        })
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log(f"  HTTP error: {e}")
        return None


def normalize_team_name(name: str) -> str:
    name = name.lower().strip()
    # Check alias map first
    if name in TEAM_ALIASES:
        return TEAM_ALIASES[name]
    for prefix in ("fc ", "cf ", "ss ", "s.s. ", "rb ", "rcd "):
        if name.startswith(prefix):
            name = name[len(prefix):]
    for suffix in (" fc", " cf"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name


def teams_match(csv_name: str, uefa_name: str) -> bool:
    a = normalize_team_name(csv_name)
    b = normalize_team_name(uefa_name)
    if a == b:
        return True
    if a in b or b in a:
        return True
    if SequenceMatcher(None, a, b).ratio() > 0.7:
        return True
    return False


def _search_matches_on_date(home: str, away: str, date: str) -> str | None:
    url = (
        f"{MATCH_API}?competitionId={UCL_COMPETITION_ID}"
        f"&fromDate={date}&toDate={date}&offset=0&limit=20&order=ASC"
    )
    data = http_get_json(url)
    if not data or not isinstance(data, list):
        return None

    for match in data:
        uefa_home = match.get("homeTeam", {}).get("internationalName", "")
        uefa_away = match.get("awayTeam", {}).get("internationalName", "")
        if teams_match(home, uefa_home) and teams_match(away, uefa_away):
            return str(match["id"])

    # Try swapped home/away (in case CSV has them reversed)
    for match in data:
        uefa_home = match.get("homeTeam", {}).get("internationalName", "")
        uefa_away = match.get("awayTeam", {}).get("internationalName", "")
        if teams_match(home, uefa_away) and teams_match(away, uefa_home):
            log("  Warning: matched with swapped home/away")
            return str(match["id"])

    return None


def _search_matches_in_range(home: str, away: str, from_date: str, to_date: str) -> str | None:
    url = (
        f"{MATCH_API}?competitionId={UCL_COMPETITION_ID}"
        f"&fromDate={from_date}&toDate={to_date}&offset=0&limit=200&order=ASC"
    )
    data = http_get_json(url)
    if not data or not isinstance(data, list):
        return None

    for match in data:
        uefa_home = match.get("homeTeam", {}).get("internationalName", "")
        uefa_away = match.get("awayTeam", {}).get("internationalName", "")
        if teams_match(home, uefa_home) and teams_match(away, uefa_away):
            return str(match["id"])
        if teams_match(home, uefa_away) and teams_match(away, uefa_home):
            log("  Warning: matched with swapped home/away")
            return str(match["id"])

    return None


def find_match_id(home: str, away: str, date: str) -> str | None:
    result = _search_matches_on_date(home, away, date)
    if result:
        return result

    # CSV dates can be off by ±2 days; try adjacent dates
    base = datetime.strptime(date, "%Y-%m-%d")
    for delta in (-1, 1, -2, 2):
        alt_date = (base + timedelta(days=delta)).strftime("%Y-%m-%d")
        result = _search_matches_on_date(home, away, alt_date)
        if result:
            log(f"  Note: found on {alt_date} (CSV had {date})")
            return result

    # Some CSV dates are significantly wrong; try ±30 day window as last resort
    from_date = (base + timedelta(days=-30)).strftime("%Y-%m-%d")
    to_date = (base + timedelta(days=30)).strftime("%Y-%m-%d")
    result = _search_matches_in_range(home, away, from_date, to_date)
    if result:
        log(f"  Note: found via wide search (CSV date {date} was significantly off)")
        return result

    return None


def get_media_asset_id(match_id: str) -> str | None:
    params = (
        f"aggregator=lightnodejson&limit=4"
        f"&param.attributes.footballEntities.match.matchId={match_id}"
        f"&param.attributes.language=en"
        f"&param.attributes.main.kind=Finals%2CHighlights%2CLong%20Highlights%2CMedium%20Highlights"
        f"&sorting=-attributes.firstPublicationDate&type=videostory"
    )
    url = f"{EDITORIAL_API}?{params}"
    data = http_get_json(url)
    if not data or not data.get("result"):
        return None

    return data["result"][0]["nodeData"]["id"]


def get_hls_url(media_asset_id: str) -> str | None:
    url = f"{ACCESS_API}?mediaAssetIds={media_asset_id}"
    data = http_get_json(url)
    if not data or not isinstance(data, list) or not data:
        return None

    entry = data[0]
    if entry.get("status") != "AVAILABLE":
        log(f"  Media asset status: {entry.get('status')}")
        return None

    return entry.get("hlsStreamUrl")


def download_hls(hls_url: str, output_path: Path) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", hls_url, "-c", "copy", "-y", str(output_path)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log("  ffmpeg timeout (300s)")
        return False
    except Exception as e:
        log(f"  ffmpeg error: {e}")
        return False


def output_path_for(season: str, stage: str, home: str, away: str, date: str) -> Path:
    season_dir = season.replace("/", "-")
    stage_dir = stage.replace(" ", "_")
    filename = f"{home}_vs_{away}_{date}.mp4".replace(" ", "_")
    return HIGHLIGHTS_DIR / season_dir / stage_dir / filename


def main():
    parser = argparse.ArgumentParser(description="Download UEFA UCL highlights")
    parser.add_argument("--dry-run", action="store_true", help="Test API calls without downloading")
    parser.add_argument("--start-row", type=int, default=0, help="Row index to start from")
    parser.add_argument("--delay", type=int, default=10, help="Seconds between matches (default: 10)")
    args = parser.parse_args()

    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))

    missing = [
        (i, row) for i, row in enumerate(rows)
        if not row["youtube_url"].strip()
    ]

    log(f"Found {len(missing)} matches missing URLs (total rows: {len(rows)})")

    if args.start_row > 0:
        missing = [(i, r) for i, r in missing if i >= args.start_row]
        log(f"Starting from row {args.start_row} ({len(missing)} remaining)")

    stats = {"downloaded": 0, "skipped": 0, "failed": 0, "no_match": 0}

    for idx, (_row_num, row) in enumerate(missing):
        home = row["home_team"]
        away = row["away_team"]
        date = row["date"]
        season = row["season"]
        stage = row["stage"]

        log(f"[{idx+1}/{len(missing)}] {home} vs {away} ({date})")

        out_path = output_path_for(season, stage, home, away, date)
        if out_path.exists():
            log("  SKIP: already downloaded")
            stats["skipped"] += 1
            continue

        # Step 1: Find UEFA match ID
        match_id = find_match_id(home, away, date)
        if not match_id:
            log("  FAIL: matchId not found")
            stats["no_match"] += 1
            if idx < len(missing) - 1:
                time.sleep(args.delay)
            continue

        log(f"  matchId: {match_id}")

        # Step 2: Get media asset ID
        asset_id = get_media_asset_id(match_id)
        if not asset_id:
            log("  FAIL: no highlights video found")
            stats["failed"] += 1
            if idx < len(missing) - 1:
                time.sleep(args.delay)
            continue

        log(f"  mediaAssetId: {asset_id}")

        # Step 3: Get HLS URL
        hls_url = get_hls_url(asset_id)
        if not hls_url:
            log("  FAIL: HLS URL not available")
            stats["failed"] += 1
            if idx < len(missing) - 1:
                time.sleep(args.delay)
            continue

        if args.dry_run:
            log(f"  DRY RUN: would download to {out_path}")
            stats["downloaded"] += 1
            if idx < len(missing) - 1:
                time.sleep(args.delay)
            continue

        # Step 4: Download
        log("  Downloading...")
        if download_hls(hls_url, out_path):
            size_mb = out_path.stat().st_size / 1024 / 1024
            log(f"  OK: {out_path.name} ({size_mb:.1f} MB)")
            stats["downloaded"] += 1
            rel_path = str(out_path.relative_to(HIGHLIGHTS_DIR))
            append_to_manifest({
                "file": rel_path,
                "season": season,
                "stage": stage,
                "matchday": row["matchday"],
                "home_team": home,
                "away_team": away,
                "date": date,
                "source": "uefa",
                "uefa_match_id": match_id,
            })
        else:
            log("  FAIL: download failed")
            stats["failed"] += 1

        if idx < len(missing) - 1:
            time.sleep(args.delay)

    log(f"\nDone. Downloaded: {stats['downloaded']}, Skipped: {stats['skipped']}, "
        f"Failed: {stats['failed']}, No match: {stats['no_match']}")


if __name__ == "__main__":
    main()
