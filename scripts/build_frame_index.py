#!/usr/bin/env python3
"""Build a pre-computed index of all annotated frames and metrics.

Scans data/frames/ and produces data/frames_index.json for the Gradio app.

Usage:
    python3 scripts/build_frame_index.py
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRAMES_DIR = PROJECT_ROOT / "data" / "frames"
OUTPUT_PATH = PROJECT_ROOT / "data" / "frames_index.json"


def extract_teams_from_dir(dir_name: str) -> tuple[str, str, str]:
    """Extract home team, away team, and date from directory name."""
    date_part = dir_name.rsplit("_", 1)[-1]
    match_part = dir_name.rsplit("_", 1)[0]
    teams = match_part.split("_vs_")
    if len(teams) == 2:
        return teams[0], teams[1], date_part
    return "", "", date_part


def main():
    teams_set = set()
    matches = {}

    for d in sorted(FRAMES_DIR.iterdir()):
        if not d.is_dir():
            continue
        annotated_dir = d / "annotated"
        if not annotated_dir.exists():
            continue

        home, away, date = extract_teams_from_dir(d.name)
        if not home or not away:
            continue

        teams_set.add(home)
        teams_set.add(away)

        frames = sorted([f.name for f in annotated_dir.glob("*.jpg")])
        if not frames:
            continue

        metrics = {}
        metrics_path = d / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path) as f:
                m = json.load(f)
            metrics = m.get("aggregated", {})

        matches[d.name] = {
            "home": home,
            "away": away,
            "date": date,
            "frames": frames,
            "metrics": metrics,
        }

    index = {
        "teams": sorted(teams_set),
        "matches": matches,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(index, f, indent=2)

    print(f"Index built: {len(index['teams'])} teams, {len(index['matches'])} matches")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
