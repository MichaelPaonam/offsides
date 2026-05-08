#!/usr/bin/env python3
"""Scrape UCL match stats (xG, scores, possession) from FBRef.

Uses SeleniumBase to bypass 403 blocks. Scrapes schedule pages for
per-match xG + scores, then computes rolling team stats.

Usage:
    python3 scripts/scrape_fbref.py
    python3 scripts/scrape_fbref.py --with-possession  # also scrape match pages (slow)
"""

import argparse
import json
import re
import time
from pathlib import Path

from seleniumbase import SB
from bs4 import BeautifulSoup
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "match_stats.json"

SCHEDULE_URLS = [
    "https://fbref.com/en/comps/8/2023-2024/schedule/2023-2024-Champions-League-Scores-and-Fixtures",
    "https://fbref.com/en/comps/8/2024-2025/schedule/2024-2025-Champions-League-Scores-and-Fixtures",
]

FBREF_TO_LOCAL = {
    "AC Milan": "AC_Milan",
    "Milan": "AC_Milan",
    "Antwerp": "Antwerp",
    "Arsenal": "Arsenal",
    "Aston Villa": "Aston_Villa",
    "Atalanta": "Atalanta",
    "Atlético Madrid": "Atletico_Madrid",
    "Atletico Madrid": "Atletico_Madrid",
    "Barcelona": "Barcelona",
    "Bayer Leverkusen": "Bayer_Leverkusen",
    "Bayern Munich": "Bayern_Munich",
    "Bayern de Munique": "Bayern_Munich",
    "Benfica": "Benfica",
    "Bologna": "Bologna",
    "Braga": "Braga",
    "Brest": "Brest",
    "Celtic": "Celtic",
    "Club Brugge": "Club_Brugge",
    "Club Bruges": "Club_Brugge",
    "Crvena Zvezda": "Crvena_Zvezda",
    "Red Star": "Crvena_Zvezda",
    "Red Star Belgrade": "Red_Star_Belgrade",
    "Dinamo Zagreb": "Dinamo_Zagreb",
    "GNK Dinamo Zagreb": "Dinamo_Zagreb",
    "Borussia Dortmund": "Dortmund",
    "Dortmund": "Dortmund",
    "FC Copenhagen": "FC_Copenhagen",
    "Copenhagen": "FC_Copenhagen",
    "Feyenoord": "Feyenoord",
    "Galatasaray": "Galatasaray",
    "Girona": "Girona",
    "Inter Milan": "Inter_Milan",
    "Internazionale": "Inter_Milan",
    "Inter": "Inter_Milan",
    "Juventus": "Juventus",
    "Lazio": "Lazio",
    "Lens": "Lens",
    "Lille": "Lille",
    "Liverpool": "Liverpool",
    "Manchester City": "Man_City",
    "Man City": "Man_City",
    "Manchester United": "Manchester_United",
    "Man Utd": "Manchester_United",
    "Monaco": "Monaco",
    "Napoli": "Napoli",
    "Newcastle United": "Newcastle",
    "Newcastle Utd": "Newcastle",
    "Paris Saint-Germain": "PSG",
    "Paris S-G": "PSG",
    "PSV Eindhoven": "PSV",
    "PSV": "PSV",
    "FC Porto": "Porto",
    "Porto": "Porto",
    "RB Leipzig": "RB_Leipzig",
    "Real Madrid": "Real_Madrid",
    "Real Sociedad": "Real_Sociedad",
    "Red Star Belgrade": "Red_Star_Belgrade",
    "Red Bull Salzburg": "Salzburg",
    "Salzburg": "Salzburg",
    "Sevilla": "Sevilla",
    "Shakhtar Donetsk": "Shakhtar_Donetsk",
    "Shakhtar": "Shakhtar_Donetsk",
    "ŠK Slovan Bratislava": "Slovan_Bratislava",
    "Slovan Bratislava": "Slovan_Bratislava",
    "Sparta Prague": "Sparta_Prague",
    "Sparta Praha": "Sparta_Prague",
    "Sporting CP": "Sporting_CP",
    "Sporting": "Sporting_CP",
    "Sturm Graz": "Sturm_Graz",
    "VfB Stuttgart": "Stuttgart",
    "Stuttgart": "Stuttgart",
    "Union Berlin": "Union_Berlin",
    "BSC Young Boys": "Young_Boys",
    "Young Boys": "Young_Boys",
}


def normalize_team(name: str) -> str:
    """Convert FBRef team name to our local format."""
    name = name.strip()
    if name in FBREF_TO_LOCAL:
        return FBREF_TO_LOCAL[name]
    # Fallback: replace spaces with underscores
    return name.replace(" ", "_")


def parse_score(score_text: str) -> tuple[int, int] | None:
    """Parse '2–1' or '2-1' into (home_goals, away_goals)."""
    score_text = score_text.strip()
    for sep in ["–", "-", "—"]:
        if sep in score_text:
            parts = score_text.split(sep)
            if len(parts) == 2:
                try:
                    return int(parts[0].strip()), int(parts[1].strip())
                except ValueError:
                    return None
    return None


def scrape_schedule_page(sb, url: str) -> list[dict]:
    """Scrape a single FBRef schedule page for match data."""
    print(f"  Loading: {url}")
    sb.open(url)
    time.sleep(3)

    html = sb.get_page_source()
    soup = BeautifulSoup(html, "html.parser")

    # Find the schedule table
    table = soup.find("table", id=lambda x: x and "sched" in x)
    if not table:
        tables = soup.find_all("table")
        print(f"  WARNING: No sched table found. {len(tables)} tables on page.")
        for t in tables[:5]:
            print(f"    Table id={t.get('id', 'none')}")
        return []

    matches = []
    tbody = table.find("tbody")
    if not tbody:
        return []

    rows = tbody.find_all("tr")
    print(f"  Found {len(rows)} rows in schedule table")

    for row in rows:
        # Skip spacer rows
        if row.get("class") and "spacer" in " ".join(row.get("class", [])):
            continue
        if row.find("th", {"colspan": True}):
            continue

        cells = row.find_all(["td", "th"])
        if len(cells) < 5:
            continue

        # Extract data by data-stat attribute
        date_cell = row.find(attrs={"data-stat": "date"})
        home_cell = row.find(attrs={"data-stat": "home_team"})
        away_cell = row.find(attrs={"data-stat": "away_team"})
        score_cell = row.find(attrs={"data-stat": "score"})
        home_xg_cell = row.find(attrs={"data-stat": "home_xg"})
        away_xg_cell = row.find(attrs={"data-stat": "away_xg"})

        if not all([date_cell, home_cell, away_cell]):
            continue

        date_text = date_cell.get_text(strip=True)
        score_text = score_cell.get_text(strip=True) if score_cell else ""

        # Use <a> tag text for team names (raw cell text has country codes appended)
        home_a = home_cell.find("a")
        away_a = away_cell.find("a")
        home_text = home_a.get_text(strip=True) if home_a else home_cell.get_text(strip=True)
        away_text = away_a.get_text(strip=True) if away_a else away_cell.get_text(strip=True)

        if not date_text or not home_text or not away_text:
            continue

        # Parse xG (may not exist on CL schedule pages)
        home_xg = None
        away_xg = None
        if home_xg_cell:
            try:
                home_xg = float(home_xg_cell.get_text(strip=True))
            except (ValueError, TypeError):
                pass
        if away_xg_cell:
            try:
                away_xg = float(away_xg_cell.get_text(strip=True))
            except (ValueError, TypeError):
                pass

        # Parse score
        score = parse_score(score_text)

        # Get match report link for possession scraping later
        match_link = None
        mr_cell = row.find(attrs={"data-stat": "match_report"})
        if mr_cell:
            a_tag = mr_cell.find("a")
            if a_tag and a_tag.get("href"):
                match_link = "https://fbref.com" + a_tag["href"]

        home_local = normalize_team(home_text)
        away_local = normalize_team(away_text)

        match_data = {
            "date": date_text,
            "home_team": home_local,
            "away_team": away_local,
            "home_team_fbref": home_text,
            "away_team_fbref": away_text,
            "score": f"{score[0]}-{score[1]}" if score else None,
            "home_goals": score[0] if score else None,
            "away_goals": score[1] if score else None,
            "home_xg": home_xg,
            "away_xg": away_xg,
            "match_link": match_link,
        }
        matches.append(match_data)

    return matches


def scrape_match_possession(sb, url: str) -> tuple[int | None, int | None]:
    """Scrape possession from an individual match report page."""
    sb.open(url)
    time.sleep(7)

    html = sb.get_page_source()
    soup = BeautifulSoup(html, "html.parser")

    # Look for possession in team stats or match summary
    # FBRef shows possession as percentage in various places
    poss_pattern = re.compile(r"(\d+)%")

    # Try the team stats summary section
    team_stats = soup.find("div", id="team_stats")
    if team_stats:
        percentages = poss_pattern.findall(team_stats.get_text())
        if len(percentages) >= 2:
            return int(percentages[0]), int(percentages[1])

    # Try broader search
    for div in soup.find_all("div", {"id": re.compile("team_stats")}):
        text = div.get_text()
        matches = poss_pattern.findall(text)
        if len(matches) >= 2:
            return int(matches[0]), int(matches[1])

    return None, None


def compute_team_stats(all_matches: list[dict]) -> dict:
    """Compute rolling team statistics from all match data."""
    # Sort by date
    all_matches.sort(key=lambda m: m["date"])

    # Group matches by team (each team appears in multiple matches)
    team_matches = {}
    for m in all_matches:
        home = m["home_team"]
        away = m["away_team"]

        if home not in team_matches:
            team_matches[home] = []
        if away not in team_matches:
            team_matches[away] = []

        team_matches[home].append({
            "date": m["date"],
            "side": "home",
            "goals_for": m["home_goals"],
            "goals_against": m["away_goals"],
            "xg_for": m["home_xg"],
            "xg_against": m["away_xg"],
            "possession": m.get("home_possession"),
        })
        team_matches[away].append({
            "date": m["date"],
            "side": "away",
            "goals_for": m["away_goals"],
            "goals_against": m["home_goals"],
            "xg_for": m["away_xg"],
            "xg_against": m["home_xg"],
            "possession": m.get("away_possession"),
        })

    # Compute rolling stats (last 5 UCL matches)
    stats = {}
    for team, matches in team_matches.items():
        matches.sort(key=lambda x: x["date"])
        last5 = matches[-5:]

        goals_for = [m["goals_for"] for m in last5 if m["goals_for"] is not None]
        goals_against = [m["goals_against"] for m in last5 if m["goals_against"] is not None]
        xg_for = [m["xg_for"] for m in last5 if m["xg_for"] is not None]
        xg_against = [m["xg_against"] for m in last5 if m["xg_against"] is not None]
        poss = [m["possession"] for m in last5 if m["possession"] is not None]

        # Form string
        form = ""
        for m in last5:
            if m["goals_for"] is None or m["goals_against"] is None:
                continue
            if m["goals_for"] > m["goals_against"]:
                form += "W"
            elif m["goals_for"] < m["goals_against"]:
                form += "L"
            else:
                form += "D"

        # PPDA estimate from possession (rough correlation: lower possession ≈ higher PPDA)
        avg_poss = float(np.mean(poss)) if poss else 50.0
        ppda_estimate = round(8.0 + (55 - avg_poss) * 0.15, 1)

        stats[team] = {
            "xg_last5": round(float(np.mean(xg_for)), 2) if xg_for else None,
            "xga_last5": round(float(np.mean(xg_against)), 2) if xg_against else None,
            "ppda": ppda_estimate,
            "possession_pct": round(float(np.mean(poss))) if poss else None,
            "form": form,
            "goals_scored_last5": sum(goals_for) if goals_for else 0,
            "goals_conceded_last5": sum(goals_against) if goals_against else 0,
            "matches_played": len(matches),
        }

    return stats


def main():
    parser = argparse.ArgumentParser(description="Scrape FBRef UCL stats")
    parser.add_argument("--with-possession", action="store_true",
                        help="Also scrape individual match pages for possession (slow)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit match page scraping to N matches")
    args = parser.parse_args()

    all_matches = []

    print("=== FBRef UCL Stats Scraper ===\n")

    with SB(uc=True, headless=True) as sb:
        # Step 1: Scrape schedule pages
        for url in SCHEDULE_URLS:
            print(f"\nScraping schedule page...")
            matches = scrape_schedule_page(sb, url)
            print(f"  Extracted {len(matches)} matches")
            all_matches.extend(matches)
            time.sleep(5)

        # Step 2: Optionally scrape possession from match pages
        if args.with_possession:
            matches_with_links = [m for m in all_matches if m.get("match_link")]
            if args.limit:
                matches_with_links = matches_with_links[:args.limit]

            print(f"\nScraping possession from {len(matches_with_links)} match pages...")
            for i, match in enumerate(matches_with_links):
                print(f"  [{i+1}/{len(matches_with_links)}] {match['home_team']} vs {match['away_team']}...")
                home_poss, away_poss = scrape_match_possession(sb, match["match_link"])
                match["home_possession"] = home_poss
                match["away_possession"] = away_poss
                if home_poss:
                    print(f"    Possession: {home_poss}% - {away_poss}%")

    # Step 3: Compute team stats
    print(f"\nComputing team rolling stats...")
    team_stats = compute_team_stats(all_matches)
    print(f"  Stats computed for {len(team_stats)} teams")

    # Step 4: Build match index keyed by match_id
    matches_index = {}
    for m in all_matches:
        match_id = f"{m['home_team']}_vs_{m['away_team']}_{m['date']}"
        entry = {
            "home_team": m["home_team"],
            "away_team": m["away_team"],
            "date": m["date"],
            "score": m["score"],
            "home_xg": m["home_xg"],
            "away_xg": m["away_xg"],
        }
        if m.get("home_possession"):
            entry["home_possession"] = m["home_possession"]
            entry["away_possession"] = m["away_possession"]
        matches_index[match_id] = entry

    # Step 5: Output
    output = {
        "matches": matches_index,
        "team_stats": team_stats,
        "scrape_info": {
            "source": "fbref.com",
            "competition": "UEFA Champions League",
            "seasons": ["2023-24", "2024-25"],
            "total_matches": len(matches_index),
            "total_teams": len(team_stats),
        }
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput: {OUTPUT_PATH}")
    print(f"  Matches: {len(matches_index)}")
    print(f"  Teams: {len(team_stats)}")

    # Show coverage against our frame dirs
    frames_dir = PROJECT_ROOT / "data" / "frames"
    if frames_dir.exists():
        our_matches = {d.name for d in frames_dir.iterdir() if d.is_dir()}
        covered = our_matches & set(matches_index.keys())
        print(f"\n  Coverage: {len(covered)}/{len(our_matches)} of our matches found in FBRef data")
        if len(covered) < len(our_matches):
            missing = sorted(our_matches - set(matches_index.keys()))[:10]
            print(f"  Missing examples: {missing[:5]}")


if __name__ == "__main__":
    main()
