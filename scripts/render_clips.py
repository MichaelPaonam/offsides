#!/usr/bin/env python3
"""Render annotated video clips from tracked sequences.

Applies YOLO detections + team colors + defensive lines onto sequence frames
and stitches them into MP4 clips for the Gradio demo.

Usage:
    python3 scripts/render_clips.py                           # all demo matches
    python3 scripts/render_clips.py --match "PSG_vs_Dortmund" # single match
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotate_frames import (
    get_torso_color,
    draw_defensive_line,
    draw_compactness_ellipse,
    load_team_kits,
    HOME_COLOR,
    AWAY_COLOR,
    UNKNOWN_COLOR,
    BALL_COLOR,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRAMES_DIR = PROJECT_ROOT / "data" / "frames"
CLIPS_DIR = PROJECT_ROOT / "data" / "vlm_results" / "clips"
KITS_PATH = PROJECT_ROOT / "data" / "team_kits.json"


def get_team_names_from_match(match_dir: str) -> tuple[str, str]:
    """Extract home and away team names from directory name like 'PSG_vs_Dortmund_2024-05-01'."""
    parts = match_dir.rsplit("_", 1)[0]  # Remove date
    teams = parts.split("_vs_")
    if len(teams) == 2:
        return teams[0], teams[1]
    return "", ""


def find_kit(team_name: str, kits: dict) -> dict | None:
    """Find kit definition for a team name."""
    normalized = team_name.replace("_", " ")
    for kit_name, kit_data in kits.items():
        if normalized.lower() in kit_name.lower() or kit_name.lower() in normalized.lower():
            return kit_data
    return None


def annotate_sequence_frame(
    frame: np.ndarray,
    tracks: dict,
    ball_tracks: list,
    frame_idx: int,
    home_kit: dict,
    away_kit: dict,
) -> np.ndarray:
    """Annotate a single frame from a tracked sequence using KMeans clustering."""
    from sklearn.cluster import KMeans

    annotated = frame.copy()
    h, w = frame.shape[:2]

    player_assignments = []
    colors_hsv = []
    valid_indices = []

    for track_id, positions in tracks.items():
        pos_at_frame = [p for p in positions if p["frame"] == frame_idx]
        if not pos_at_frame:
            continue
        bbox = pos_at_frame[0]["bbox"]
        median_hsv = get_torso_color(frame, bbox)
        player_assignments.append({"bbox": bbox, "team": "unknown", "track_id": track_id})
        if median_hsv is not None:
            colors_hsv.append(median_hsv)
            valid_indices.append(len(player_assignments) - 1)

    # KMeans clustering into 2 teams
    if len(colors_hsv) >= 4:
        X = np.array(colors_hsv)
        kmeans = KMeans(n_clusters=2, random_state=0, n_init=10).fit(X)
        labels = kmeans.labels_

        cluster_xs = {0: [], 1: []}
        for idx, vi in enumerate(valid_indices):
            bbox = player_assignments[vi]["bbox"]
            cx = (bbox[0] + bbox[2]) / 2
            cluster_xs[labels[idx]].append(cx)

        avg_x_0 = np.mean(cluster_xs[0]) if cluster_xs[0] else w / 2
        avg_x_1 = np.mean(cluster_xs[1]) if cluster_xs[1] else w / 2

        home_cluster = 0 if avg_x_0 < avg_x_1 else 1

        for idx, vi in enumerate(valid_indices):
            player_assignments[vi]["team"] = "home" if labels[idx] == home_cluster else "away"

    # Draw bounding boxes
    players_by_team = {"home": [], "away": [], "unknown": []}
    for p in player_assignments:
        team = p["team"]
        bbox = p["bbox"]
        players_by_team[team].append(bbox)
        color = HOME_COLOR if team == "home" else AWAY_COLOR if team == "away" else UNKNOWN_COLOR
        x1, y1, x2, y2 = [int(v) for v in bbox]
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

    # Ball
    if ball_tracks:
        ball_at_frame = [b for b in ball_tracks if b["frame"] == frame_idx]
        if ball_at_frame:
            bx1, by1, bx2, by2 = [int(v) for v in ball_at_frame[0]["bbox"]]
            cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2
            cv2.circle(annotated, (cx, cy), 10, BALL_COLOR, -1)
            cv2.circle(annotated, (cx, cy), 10, (0, 0, 0), 2)

    # Defensive lines
    for team, color in [("home", HOME_COLOR), ("away", AWAY_COLOR)]:
        bboxes = players_by_team[team]
        if len(bboxes) >= 4:
            draw_defensive_line(annotated, bboxes, color)

    # Compactness ellipses
    for team, color in [("home", HOME_COLOR), ("away", AWAY_COLOR)]:
        bboxes = players_by_team[team]
        if len(bboxes) >= 5:
            draw_compactness_ellipse(annotated, bboxes, color)

    return annotated


def render_clip(
    match_dir: Path,
    seq_name: str,
    tracks: dict,
    ball_tracks: list,
    home_kit: dict,
    away_kit: dict,
    output_path: Path,
    fps: int = 30,
) -> bool:
    """Render a single sequence into an annotated MP4 clip."""
    seq_dir = match_dir / "sequences" / seq_name
    if not seq_dir.exists():
        return False

    frame_files = sorted(seq_dir.glob("frame_*.jpg"))
    if not frame_files:
        return False

    first_frame = cv2.imread(str(frame_files[0]))
    if first_frame is None:
        return False
    h, w = first_frame.shape[:2]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(".tmp.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(tmp_path), fourcc, fps, (w, h))

    for i, frame_file in enumerate(frame_files):
        frame = cv2.imread(str(frame_file))
        if frame is None:
            continue
        annotated = annotate_sequence_frame(frame, tracks, ball_tracks, i, home_kit, away_kit)
        writer.write(annotated)

    writer.release()

    # Convert to H.264 for browser playback
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(tmp_path), "-c:v", "libx264", "-preset", "fast",
             "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path)],
            capture_output=True, check=True,
        )
        tmp_path.unlink()
    except (subprocess.CalledProcessError, FileNotFoundError):
        tmp_path.rename(output_path)

    return True


def select_best_sequences(detections: dict, n: int = 2) -> list[str]:
    """Select sequences with the most tracked players (most tactical content)."""
    seq_data = detections.get("sequences", {})
    scored = []
    for seq_name, data in seq_data.items():
        tracks = data.get("tracks", data)
        if isinstance(tracks, dict) and "tracks" in tracks:
            tracks = tracks["tracks"]
        n_tracks = len(tracks)
        scored.append((seq_name, n_tracks))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scored[:n]]


def process_match(match_dir: Path, kits: dict, n_clips: int = 2) -> list[Path]:
    """Process a single match directory, render top N sequence clips."""
    det_path = match_dir / "detections.json"
    if not det_path.exists():
        print(f"  No detections.json, skipping")
        return []

    with open(det_path) as f:
        detections = json.load(f)

    home_name, away_name = get_team_names_from_match(match_dir.name)
    home_kit = find_kit(home_name, kits)
    away_kit = find_kit(away_name, kits)

    if not home_kit or not away_kit:
        print(f"  Kit not found for {home_name} or {away_name}, using defaults")
        home_kit = home_kit or {"primary": {"h_range": [0, 10], "s_min": 100, "v_min": 100, "label": "red"}}
        away_kit = away_kit or {"primary": {"h_range": [100, 130], "s_min": 100, "v_min": 100, "label": "blue"}}

    best_seqs = select_best_sequences(detections, n=n_clips)
    if not best_seqs:
        print(f"  No sequences found")
        return []

    clips = []
    for seq_name in best_seqs:
        seq_data = detections["sequences"].get(seq_name, {})
        if "tracks" in seq_data:
            tracks = seq_data["tracks"]
            ball_tracks = seq_data.get("ball", [])
        else:
            tracks = seq_data
            ball_tracks = []

        output_path = CLIPS_DIR / match_dir.name / f"{seq_name}.mp4"
        print(f"  Rendering {seq_name} ({len(tracks)} tracks)...")
        success = render_clip(match_dir, seq_name, tracks, ball_tracks, home_kit, away_kit, output_path)
        if success:
            clips.append(output_path)
            print(f"    -> {output_path.relative_to(PROJECT_ROOT)}")

    return clips


def main():
    parser = argparse.ArgumentParser(description="Render annotated video clips from sequences")
    parser.add_argument("--match", type=str, help="Process single match (substring)")
    parser.add_argument("--clips", type=int, default=2, help="Number of clips per match")
    parser.add_argument("--all", action="store_true", help="Process all matches (not just results.json)")
    args = parser.parse_args()

    kits = load_team_kits()

    if args.all:
        match_dirs = {d.name for d in FRAMES_DIR.iterdir() if d.is_dir()}
    else:
        # Use the form matches referenced in VLM results
        results_path = PROJECT_ROOT / "data" / "vlm_results" / "results.json"
        if results_path.exists():
            with open(results_path) as f:
                results = json.load(f)
            match_dirs = set()
            for m in results["matches"]:
                for fp in m.get("frames_used", []):
                    parts = Path(fp).parts
                    if len(parts) >= 3:
                        match_dirs.add(parts[2])
        else:
            match_dirs = {d.name for d in FRAMES_DIR.iterdir() if d.is_dir()}

    if args.match:
        match_dirs = {d for d in match_dirs if args.match.lower() in d.lower()}

    match_dirs = sorted(match_dirs)
    print(f"Rendering clips for {len(match_dirs)} matches\n")

    all_clips = []
    for match_name in match_dirs:
        match_dir = FRAMES_DIR / match_name
        if not match_dir.exists():
            continue
        seq_dir = match_dir / "sequences"
        if not seq_dir.exists():
            continue
        print(f"[{match_name}]")
        clips = process_match(match_dir, kits, n_clips=args.clips)
        all_clips.extend(clips)
        print()

    print(f"Done. {len(all_clips)} clips rendered to {CLIPS_DIR.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
