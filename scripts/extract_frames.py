#!/usr/bin/env python3
"""Extract keyframes and sequences from UCL highlight videos.

Scene-change detection → pre-filter (green ratio, edge density) → save keyframes + sequences.

Usage:
    python scripts/extract_frames.py                         # all videos
    python scripts/extract_frames.py --match "AC_Milan_vs_Newcastle_2023-09-19"
    python scripts/extract_frames.py --limit 3               # first 3 videos
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
HIGHLIGHTS_DIR = PROJECT_ROOT / "data" / "highlights"
FRAMES_DIR = PROJECT_ROOT / "data" / "frames"

# Scene detection
SCENE_DIFF_THRESHOLD = 20.0  # mean absolute diff between frames to mark a scene cut
MIN_SCENE_FRAMES = 24  # minimum frames in a scene (~0.8 seconds at 30fps)

# Pre-filter thresholds (moderate)
GREEN_RATIO_MIN = 0.25  # minimum fraction of green pixels to keep scene
EDGE_DENSITY_MIN = 0.02  # minimum fraction of edge pixels (discard solid graphics)
SKIP_PERCENT = 0.05  # skip first/last 5% of video

# Sequence parameters
MIN_SEQUENCE_FRAMES = 60  # ~2 seconds at 30fps
MAX_SEQUENCE_FRAMES = 90  # ~3 seconds at 30fps
MAX_SEQUENCES_PER_VIDEO = 5
MAX_KEYFRAMES_PER_VIDEO = 25


def compute_green_ratio(frame: np.ndarray) -> float:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    return np.count_nonzero(mask) / mask.size


def compute_edge_density(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    return np.count_nonzero(edges) / edges.size


def is_closeup(frame: np.ndarray) -> bool:
    """Detect close-up shots where a player fills the frame with blurred green background."""
    h, w = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # Check center region vs full frame green ratio
    ch, cw = h // 4, w // 4
    center = mask[ch:h-ch, cw:w-cw]
    center_green = np.count_nonzero(center) / center.size
    full_green = np.count_nonzero(mask) / mask.size

    # Close-ups: moderate green overall (player fills frame) with center less green
    # Wide tactical shots typically have full_green > 0.65
    if full_green < 0.65 and center_green < 0.40:
        return True

    # Close-ups with blurred green background: edges green, center not
    if full_green > 0.20 and center_green < 0.20 and (full_green - center_green) > 0.10:
        return True

    # Detect via edge sharpness contrast: close-ups have sharp foreground, blurry background
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    center_lap = cv2.Laplacian(gray[ch:h-ch, cw:w-cw], cv2.CV_64F).var()
    edge_regions = np.concatenate([gray[:ch, :].flatten(), gray[h-ch:, :].flatten()])
    edge_lap = cv2.Laplacian(edge_regions.reshape(ch*2, w), cv2.CV_64F).var()
    if center_lap > 3 * edge_lap and edge_lap < 100:
        return True

    # Large non-green blob in center — player fills frame
    center_non_green = 1.0 - center_green
    if center_non_green > 0.75 and full_green > 0.30:
        return True

    return False


def is_tactical_scene(frame: np.ndarray) -> bool:
    green = compute_green_ratio(frame)
    if green < GREEN_RATIO_MIN:
        return False
    edge = compute_edge_density(frame)
    if edge < EDGE_DENSITY_MIN:
        return False
    if is_closeup(frame):
        return False
    return True


def detect_scenes(video_path: Path) -> list[dict]:
    """Detect scene boundaries and return list of scenes with frame ranges."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames == 0:
        cap.release()
        return []

    skip_start = int(total_frames * SKIP_PERCENT)
    skip_end = int(total_frames * (1 - SKIP_PERCENT))

    cap.set(cv2.CAP_PROP_POS_FRAMES, skip_start)
    ret, prev_frame = cap.read()
    if not ret:
        cap.release()
        return []

    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    scenes = []
    current_scene_start = skip_start
    frame_idx = skip_start + 1

    while frame_idx < skip_end:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev_gray, gray)
        mean_diff = np.mean(diff)

        if mean_diff > SCENE_DIFF_THRESHOLD:
            scene_length = frame_idx - current_scene_start
            if scene_length >= MIN_SCENE_FRAMES:
                scenes.append({
                    "start": current_scene_start,
                    "end": frame_idx - 1,
                    "length": scene_length,
                })
            current_scene_start = frame_idx

        prev_gray = gray
        frame_idx += 1

    # Final scene
    scene_length = frame_idx - current_scene_start
    if scene_length >= MIN_SCENE_FRAMES:
        scenes.append({
            "start": current_scene_start,
            "end": frame_idx - 1,
            "length": scene_length,
        })

    cap.release()
    return scenes


def extract_match(video_path: Path, match_id: str) -> dict:
    """Extract keyframes and sequences from a single video."""
    output_dir = FRAMES_DIR / match_id
    keyframes_dir = output_dir / "keyframes"
    sequences_dir = output_dir / "sequences"
    keyframes_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "match_id": match_id,
        "video": str(video_path.relative_to(HIGHLIGHTS_DIR)),
        "keyframes": [],
        "sequences": [],
    }

    scenes = detect_scenes(video_path)
    if not scenes:
        print(f"  No scenes detected")
        return metadata

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Filter scenes: check middle frame for tactical content
    tactical_scenes = []
    for scene in scenes:
        mid_frame_idx = (scene["start"] + scene["end"]) // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame_idx)
        ret, frame = cap.read()
        if ret and is_tactical_scene(frame):
            tactical_scenes.append(scene)

    print(f"  {len(scenes)} scenes total, {len(tactical_scenes)} tactical")

    # Extract keyframes — try multiple candidates per scene, pick best
    keyframe_count = 0
    for scene in tactical_scenes:
        if keyframe_count >= MAX_KEYFRAMES_PER_VIDEO:
            break

        # Try 3 positions: 1/4, 1/2, 3/4 through the scene
        best_frame = None
        best_green = 0
        for frac in (0.5, 0.33, 0.66):
            candidate_idx = scene["start"] + int(scene["length"] * frac)
            cap.set(cv2.CAP_PROP_POS_FRAMES, candidate_idx)
            ret, frame = cap.read()
            if not ret:
                continue
            if not is_tactical_scene(frame):
                continue
            green = compute_green_ratio(frame)
            if green > best_green:
                best_green = green
                best_frame = (frame, candidate_idx)

        if best_frame is None:
            continue

        frame, frame_idx = best_frame
        filename = f"frame_{keyframe_count:03d}.jpg"
        cv2.imwrite(str(keyframes_dir / filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        metadata["keyframes"].append({
            "file": filename,
            "frame_idx": frame_idx,
            "timestamp": frame_idx / fps,
            "scene_start": scene["start"],
            "scene_end": scene["end"],
        })
        keyframe_count += 1

    # Extract sequences (longer tactical scenes, 2-3 seconds of frames)
    sequence_count = 0
    long_scenes = sorted(
        [s for s in tactical_scenes if s["length"] >= MIN_SEQUENCE_FRAMES],
        key=lambda s: s["length"],
        reverse=True,
    )

    for scene in long_scenes:
        if sequence_count >= MAX_SEQUENCES_PER_VIDEO:
            break

        seq_dir = sequences_dir / f"seq_{sequence_count:02d}"
        seq_dir.mkdir(parents=True, exist_ok=True)

        # Take frames from the middle of the scene
        scene_mid = (scene["start"] + scene["end"]) // 2
        seq_length = min(scene["length"], MAX_SEQUENCE_FRAMES)
        seq_start = scene_mid - seq_length // 2
        seq_end = seq_start + seq_length

        cap.set(cv2.CAP_PROP_POS_FRAMES, seq_start)
        frame_in_seq = 0
        for fidx in range(seq_start, seq_end):
            ret, frame = cap.read()
            if not ret:
                break
            filename = f"frame_{frame_in_seq:03d}.jpg"
            cv2.imwrite(str(seq_dir / filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_in_seq += 1

        metadata["sequences"].append({
            "dir": f"seq_{sequence_count:02d}",
            "frame_count": frame_in_seq,
            "start_frame": seq_start,
            "end_frame": seq_start + frame_in_seq,
            "start_time": seq_start / fps,
            "end_time": (seq_start + frame_in_seq) / fps,
            "duration": frame_in_seq / fps,
        })
        sequence_count += 1

    cap.release()

    # Save metadata
    with open(output_dir / "extraction.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Extracted {keyframe_count} keyframes, {sequence_count} sequences")
    return metadata


def match_id_from_entry(entry: dict) -> str:
    """Generate a match_id from manifest entry."""
    home = entry["home_team"].replace(" ", "_")
    away = entry["away_team"].replace(" ", "_")
    date = entry["date"]
    return f"{home}_vs_{away}_{date}"


def main():
    parser = argparse.ArgumentParser(description="Extract frames from UCL highlight videos")
    parser.add_argument("--match", type=str, help="Process single match (substring match on match_id)")
    parser.add_argument("--limit", type=int, default=0, help="Max videos to process (0=all)")
    parser.add_argument("--force", action="store_true", help="Re-extract even if extraction.json exists")
    args = parser.parse_args()

    manifest = load_manifest()
    if not manifest:
        print("ERROR: manifest is empty. Run build_manifest.py first.")
        sys.exit(1)

    print(f"Loaded manifest: {len(manifest)} videos")

    # Filter to target entries
    targets = []
    for entry in manifest:
        match_id = match_id_from_entry(entry)
        if args.match and args.match.lower() not in match_id.lower():
            continue
        video_path = HIGHLIGHTS_DIR / entry["file"]
        if not video_path.exists():
            continue
        if not args.force and (FRAMES_DIR / match_id / "extraction.json").exists():
            continue
        targets.append((match_id, video_path, entry))

    if not targets:
        print("No videos to process (all already extracted or no matches found).")
        return

    if args.limit:
        targets = targets[:args.limit]

    print(f"Processing {len(targets)} videos")
    start_time = time.time()

    for idx, (match_id, video_path, entry) in enumerate(targets):
        print(f"\n[{idx+1}/{len(targets)}] {match_id}")
        extract_match(video_path, match_id)

    elapsed = time.time() - start_time
    print(f"\nDone. {len(targets)} videos processed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
