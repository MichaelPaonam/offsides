#!/usr/bin/env python3
"""Annotate frames with team colors, defensive lines, and compute temporal metrics.

Team assignment via color lookup table (data/team_kits.json).
Outputs annotated images + metrics JSON per match.

Usage:
    python3 scripts/annotate_frames.py
    python3 scripts/annotate_frames.py --match "AC_Milan"
    python3 scripts/annotate_frames.py --limit 3
"""

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from manifest import load_manifest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRAMES_DIR = PROJECT_ROOT / "data" / "frames"
HIGHLIGHTS_DIR = PROJECT_ROOT / "data" / "highlights"
KITS_PATH = PROJECT_ROOT / "data" / "team_kits.json"

HOME_COLOR = (0, 0, 255)   # Red in BGR
AWAY_COLOR = (255, 100, 0)  # Blue in BGR
UNKNOWN_COLOR = (128, 128, 128)
BALL_COLOR = (0, 255, 255)  # Yellow in BGR


def load_team_kits() -> dict:
    with open(KITS_PATH) as f:
        data = json.load(f)
    data.pop("_note", None)
    return data


def get_torso_color(frame: np.ndarray, bbox: list) -> np.ndarray | None:
    """Extract dominant HSV hue from torso region of a player bbox."""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    bh = y2 - y1
    bw = x2 - x1
    if bh < 10 or bw < 5:
        return None

    # Torso: middle 40% vertically
    torso_y1 = y1 + int(bh * 0.3)
    torso_y2 = y1 + int(bh * 0.7)
    torso = frame[torso_y1:torso_y2, x1:x2]

    if torso.size == 0:
        return None

    hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)

    # Mask out green (pitch bleed)
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([85, 255, 255])
    green_mask = cv2.inRange(hsv, lower_green, upper_green)
    non_green = cv2.bitwise_not(green_mask)

    pixels = hsv[non_green > 0]
    if len(pixels) < 10:
        return None

    return np.median(pixels, axis=0)


def assign_team(median_hsv: np.ndarray, home_kit: dict, away_kit: dict) -> str:
    """Assign a player to home, away, or unknown based on jersey color."""
    if median_hsv is None:
        return "unknown"

    h, s, v = median_hsv

    home_score = kit_match_score(h, s, v, home_kit)
    away_score = kit_match_score(h, s, v, away_kit)

    if home_score > away_score and home_score > 0.3:
        return "home"
    elif away_score > home_score and away_score > 0.3:
        return "away"
    return "unknown"


def kit_match_score(h: float, s: float, v: float, kit: dict) -> float:
    """Score how well an HSV color matches a kit definition."""
    primary = kit["primary"]
    h_range = primary["h_range"]
    s_min = primary["s_min"]
    v_min = primary["v_min"]
    label = primary.get("label", "")

    # Pure white kits (white is the dominant color, not a stripe)
    if label in ("white", "white/red", "white/black"):
        if s < 60 and v > 160:
            return 0.9
        return 0.1

    # Pure black kits
    if label in ("black", "black/white"):
        if v < 80 and s < 80:
            return 0.8
        # Also match white parts of black/white stripes
        if s < 60 and v > 160:
            return 0.7
        return 0.1

    # Black/white stripes (Newcastle etc): match either low V or high V + low S
    if "black/white stripes" in label:
        if (v < 80 and s < 80) or (s < 60 and v > 160):
            return 0.8
        return 0.1

    # Colored kits: check hue range + saturation/value thresholds
    h_min, h_max = h_range
    if h_min <= h <= h_max and s >= s_min and v >= v_min:
        return 0.9

    # Handle hue wraparound for red (hues near 0 can also appear as 170-179)
    if h_max <= 30 and h_min == 0:
        if (h <= h_max or h >= 170) and s >= s_min and v >= v_min:
            return 0.85

    return 0.1



def annotate_keyframe(frame: np.ndarray, detections: dict, home_kit: dict, away_kit: dict) -> tuple[np.ndarray, dict]:
    """Draw bounding boxes colored by team, ball marker, defensive lines."""
    annotated = frame.copy()
    h, w = frame.shape[:2]

    # First pass: assign teams by jersey color
    player_assignments = []
    for player in detections.get("players", []):
        bbox = player["bbox"]
        median_hsv = get_torso_color(frame, bbox)
        team = assign_team(median_hsv, home_kit, away_kit)
        player_assignments.append({"bbox": bbox, "team": team})

    # Goalkeeper fix: player nearest each goal edge likely belongs to the team defending there
    # In broadcast view: leftmost deep player = one GK, rightmost deep player = other GK
    if len(player_assignments) >= 6:
        # Find team centroids to determine which team defends which side
        home_xs = [((p["bbox"][0] + p["bbox"][2]) / 2) for p in player_assignments if p["team"] == "home"]
        away_xs = [((p["bbox"][0] + p["bbox"][2]) / 2) for p in player_assignments if p["team"] == "away"]

        if home_xs and away_xs:
            home_avg_x = np.mean(home_xs)
            away_avg_x = np.mean(away_xs)

            # The team with lower avg X is defending the left goal
            left_team = "home" if home_avg_x < away_avg_x else "away"
            right_team = "away" if left_team == "home" else "home"

            # Find the leftmost and rightmost players
            for p in player_assignments:
                cx = (p["bbox"][0] + p["bbox"][2]) / 2
                # Player in the leftmost 10% of frame and assigned wrong or unknown
                if cx < w * 0.10 and p["team"] != left_team:
                    p["team"] = left_team
                # Player in the rightmost 10% of frame and assigned wrong or unknown
                elif cx > w * 0.90 and p["team"] != right_team:
                    p["team"] = right_team

    # Draw boxes
    players_by_team = {"home": [], "away": [], "unknown": []}
    for p in player_assignments:
        team = p["team"]
        bbox = p["bbox"]
        players_by_team[team].append(bbox)
        color = HOME_COLOR if team == "home" else AWAY_COLOR if team == "away" else UNKNOWN_COLOR
        x1, y1, x2, y2 = [int(v) for v in bbox]
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

    # Ball marker
    if detections.get("ball"):
        bx1, by1, bx2, by2 = [int(v) for v in detections["ball"]["bbox"]]
        cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2
        cv2.circle(annotated, (cx, cy), 12, BALL_COLOR, -1)
        cv2.circle(annotated, (cx, cy), 12, (0, 0, 0), 2)

    # Defensive line for each team (connect bottom of back 4)
    for team, color in [("home", HOME_COLOR), ("away", AWAY_COLOR)]:
        bboxes = players_by_team[team]
        if len(bboxes) >= 4:
            draw_defensive_line(annotated, bboxes, color)

    # Compactness ellipse
    for team, color in [("home", HOME_COLOR), ("away", AWAY_COLOR)]:
        bboxes = players_by_team[team]
        if len(bboxes) >= 3:
            draw_compactness_ellipse(annotated, bboxes, color)

    return annotated, players_by_team


def draw_defensive_line(frame: np.ndarray, bboxes: list, color: tuple):
    """Draw defensive line connecting the 4 deepest players (highest y = lowest on pitch)."""
    # Get centroids
    centroids = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b in bboxes]
    # Sort by y (highest y = closest to own goal in broadcast view)
    sorted_by_y = sorted(centroids, key=lambda c: c[1], reverse=True)
    back_four = sorted_by_y[:4]
    # Sort left to right for line drawing
    back_four.sort(key=lambda c: c[0])

    for i in range(len(back_four) - 1):
        pt1 = (int(back_four[i][0]), int(back_four[i][1]))
        pt2 = (int(back_four[i + 1][0]), int(back_four[i + 1][1]))
        cv2.line(frame, pt1, pt2, color, 2, cv2.LINE_AA)


def draw_compactness_ellipse(frame: np.ndarray, bboxes: list, color: tuple):
    """Draw ellipse encompassing team's player positions."""
    centroids = np.array([((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b in bboxes], dtype=np.float32)
    if len(centroids) < 5:
        return

    try:
        ellipse = cv2.fitEllipse(centroids)
        cv2.ellipse(frame, ellipse, color, 1, cv2.LINE_AA)
    except cv2.error:
        pass


def compute_sequence_metrics(tracks: dict, ball: list, frame_count: int) -> dict:
    """Compute temporal metrics from tracked sequence data. Normalized by frame dimensions."""
    metrics = {}

    if not tracks:
        return metrics

    # Estimate frame dimensions from bbox coordinates
    all_coords = []
    for positions in tracks.values():
        for p in positions:
            all_coords.extend(p["bbox"])
    if not all_coords:
        return metrics
    frame_width = max(all_coords[::2]) if all_coords else 1920.0
    frame_width = max(frame_width, 640.0)  # safety floor

    # Get all track centroids per frame
    frames_data = {}
    for tid, positions in tracks.items():
        for pos in positions:
            f = pos["frame"]
            if f not in frames_data:
                frames_data[f] = []
            cx = (pos["bbox"][0] + pos["bbox"][2]) / 2
            cy = (pos["bbox"][1] + pos["bbox"][3]) / 2
            frames_data[f].append({"id": tid, "x": cx, "y": cy})

    if len(frames_data) < 2:
        return metrics

    frame_indices = sorted(frames_data.keys())

    # Pressing speed: average movement speed of all tracked players (normalized by frame width)
    speeds = []
    for i in range(1, len(frame_indices)):
        prev_f = frame_indices[i - 1]
        curr_f = frame_indices[i]
        prev_players = {p["id"]: p for p in frames_data[prev_f]}
        curr_players = {p["id"]: p for p in frames_data[curr_f]}

        for pid in prev_players:
            if pid in curr_players:
                dx = curr_players[pid]["x"] - prev_players[pid]["x"]
                dy = curr_players[pid]["y"] - prev_players[pid]["y"]
                speed = np.sqrt(dx**2 + dy**2) / frame_width
                speeds.append(speed)

    metrics["pressing_speed"] = round(float(np.mean(speeds)), 4) if speeds else 0.0

    # Defensive line movement: change in average y of back players (normalized)
    first_frame = frames_data[frame_indices[0]]
    last_frame = frames_data[frame_indices[-1]]

    if len(first_frame) >= 4 and len(last_frame) >= 4:
        first_back = sorted(first_frame, key=lambda p: p["y"], reverse=True)[:4]
        last_back = sorted(last_frame, key=lambda p: p["y"], reverse=True)[:4]
        first_line_y = np.mean([p["y"] for p in first_back])
        last_line_y = np.mean([p["y"] for p in last_back])
        metrics["def_line_movement"] = round(float((last_line_y - first_line_y) / frame_width), 4)

    # Compactness delta: change in spread of players (already a ratio, no normalization needed)
    def compute_spread(players):
        if len(players) < 3:
            return 0
        xs = [p["x"] for p in players]
        ys = [p["y"] for p in players]
        return np.std(xs) + np.std(ys)

    first_spread = compute_spread(first_frame)
    last_spread = compute_spread(last_frame)
    if first_spread > 0:
        metrics["compactness_delta"] = round(float((last_spread - first_spread) / first_spread), 3)

    # Transition speed: centroid movement from first to last frame (normalized)
    first_cx = np.mean([p["x"] for p in first_frame])
    first_cy = np.mean([p["y"] for p in first_frame])
    last_cx = np.mean([p["x"] for p in last_frame])
    last_cy = np.mean([p["y"] for p in last_frame])
    metrics["transition_speed"] = round(float(np.sqrt((last_cx - first_cx)**2 + (last_cy - first_cy)**2) / frame_width), 4)

    return metrics


def process_match(match_dir: Path, team_kits: dict, manifest_entry: dict, force: bool = False) -> bool:
    """Annotate a single match."""
    det_path = match_dir / "detections.json"
    if not det_path.exists():
        return False

    annotated_dir = match_dir / "annotated"
    metrics_path = match_dir / "metrics.json"

    if annotated_dir.exists() and metrics_path.exists() and not force:
        return False

    with open(det_path) as f:
        detections = json.load(f)

    home_team = manifest_entry["home_team"]
    away_team = manifest_entry["away_team"]
    home_kit = team_kits.get(home_team, {"primary": {"h_range": [0, 179], "s_min": 0, "v_min": 0, "label": "unknown"}})
    away_kit = team_kits.get(away_team, {"primary": {"h_range": [0, 179], "s_min": 0, "v_min": 0, "label": "unknown"}})

    # Annotate tactical keyframes
    annotated_dir.mkdir(parents=True, exist_ok=True)
    tactical_frames = detections.get("tactical_keyframes", [])
    keyframes_dir = match_dir / "keyframes"

    annotated_count = 0
    for frame_name in tactical_frames:
        frame_path = keyframes_dir / frame_name
        if not frame_path.exists():
            continue

        frame = cv2.imread(str(frame_path))
        if frame is None:
            continue

        frame_det = detections["keyframes"].get(frame_name, {})
        annotated, _ = annotate_keyframe(frame, frame_det, home_kit, away_kit)
        cv2.imwrite(str(annotated_dir / frame_name), annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
        annotated_count += 1

    # Compute temporal metrics from sequences
    all_seq_metrics = {}
    sequences = detections.get("sequences", {})
    for seq_name, seq_data in sequences.items():
        tracks = seq_data.get("tracks", {})
        ball = seq_data.get("ball", [])
        frame_count = max((p["frame"] for t in tracks.values() for p in t), default=0) + 1
        seq_metrics = compute_sequence_metrics(tracks, ball, frame_count)
        if seq_metrics:
            all_seq_metrics[seq_name] = seq_metrics

    # Aggregate metrics
    aggregated = {}
    if all_seq_metrics:
        for key in ["pressing_speed", "def_line_movement", "compactness_delta", "transition_speed"]:
            values = [m[key] for m in all_seq_metrics.values() if key in m]
            if values:
                aggregated[f"avg_{key}"] = round(float(np.mean(values)), 3)

    metrics = {
        "match_id": match_dir.name,
        "home_team": home_team,
        "away_team": away_team,
        "sequences": all_seq_metrics,
        "aggregated": aggregated,
    }

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"  Annotated: {annotated_count} frames, Sequences: {len(all_seq_metrics)} with metrics")
    return True


def main():
    parser = argparse.ArgumentParser(description="Annotate frames and compute temporal metrics")
    parser.add_argument("--match", type=str, help="Process single match (substring match)")
    parser.add_argument("--limit", type=int, default=0, help="Max matches to process (0=all)")
    parser.add_argument("--force", action="store_true", help="Re-annotate even if output exists")
    args = parser.parse_args()

    team_kits = load_team_kits()
    manifest = load_manifest()

    # Build manifest lookup
    def match_id_from_entry(entry):
        home = entry["home_team"].replace(" ", "_")
        away = entry["away_team"].replace(" ", "_")
        return f"{home}_vs_{away}_{entry['date']}"

    manifest_lookup = {match_id_from_entry(e): e for e in manifest}

    # Find matches to process
    targets = []
    for match_dir in sorted(FRAMES_DIR.iterdir()):
        if not match_dir.is_dir():
            continue
        if not (match_dir / "detections.json").exists():
            continue
        if args.match and args.match.lower() not in match_dir.name.lower():
            continue
        if not args.force and (match_dir / "annotated").exists() and (match_dir / "metrics.json").exists():
            continue

        entry = manifest_lookup.get(match_dir.name)
        if not entry:
            continue
        targets.append((match_dir, entry))

    if not targets:
        print("No matches to process.")
        return

    if args.limit:
        targets = targets[:args.limit]

    print(f"Processing {len(targets)} matches\n")
    start_time = time.time()

    for idx, (match_dir, entry) in enumerate(targets):
        print(f"[{idx+1}/{len(targets)}] {match_dir.name}")
        process_match(match_dir, team_kits, entry, force=args.force)

    elapsed = time.time() - start_time
    print(f"\nDone. {len(targets)} matches in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
