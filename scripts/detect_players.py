#!/usr/bin/env python3
"""YOLO detection + ByteTrack tracking on extracted frames.

Keyframes: single-frame detection (players + ball positions)
Sequences: multi-frame tracking (consistent player IDs across frames)

Usage:
    python3 scripts/detect_players.py                         # all extracted matches
    python3 scripts/detect_players.py --match "AC_Milan"      # single match
    python3 scripts/detect_players.py --limit 3               # first 3 matches
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRAMES_DIR = PROJECT_ROOT / "data" / "frames"

PERSON_CLASS = 0
BALL_CLASS = 32
PLAYER_CONF_THRESHOLD = 0.5
BALL_CONF_THRESHOLD = 0.3
MIN_PLAYERS_TACTICAL = 8  # frames with fewer players lack full formation data


DEVICE = "0" if __import__("torch").cuda.is_available() else "cpu"
BATCH_SIZE = 16
IMGSZ_KEYFRAMES = 1280
IMGSZ_TRACKING = 640


def load_model():
    from ultralytics import YOLO
    model = YOLO("yolov8m.pt")
    if DEVICE != "cpu":
        print(f"  Using GPU: {__import__('torch').cuda.get_device_name(0)}")
    else:
        print("  Using CPU")
    print(f"  Batch size: {BATCH_SIZE}, Keyframes: {IMGSZ_KEYFRAMES}px, Tracking: {IMGSZ_TRACKING}px")
    return model


def detect_keyframes(model, match_dir: Path) -> dict:
    """Run batched detection on all keyframes."""
    keyframes_dir = match_dir / "keyframes"
    if not keyframes_dir.exists():
        return {}

    img_paths = sorted(keyframes_dir.glob("*.jpg"))
    if not img_paths:
        return {}

    results = {}

    for batch_start in range(0, len(img_paths), BATCH_SIZE):
        batch_paths = img_paths[batch_start:batch_start + BATCH_SIZE]
        preds_list = model.predict(
            [str(p) for p in batch_paths],
            verbose=False,
            conf=BALL_CONF_THRESHOLD,
            device=DEVICE,
            imgsz=IMGSZ_KEYFRAMES,
            batch=len(batch_paths),
        )

        for img_path, pred in zip(batch_paths, preds_list):
            players = []
            ball = None

            for box in pred.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                bbox = box.xyxy[0].tolist()

                if cls == PERSON_CLASS and conf >= PLAYER_CONF_THRESHOLD:
                    players.append({"bbox": [round(v, 1) for v in bbox], "conf": round(conf, 3)})
                elif cls == BALL_CLASS and conf >= BALL_CONF_THRESHOLD:
                    if ball is None or conf > ball["conf"]:
                        ball = {"bbox": [round(v, 1) for v in bbox], "conf": round(conf, 3)}

            results[img_path.name] = {"players": players, "ball": ball}

    return results


def track_sequence(model, seq_dir: Path) -> dict:
    """Run ByteTrack on a sequence for consistent player IDs."""
    frame_files = sorted(seq_dir.glob("*.jpg"))
    if not frame_files:
        return {}

    tracks = {}
    ball_positions = []

    model.predictor = None  # reset tracker state

    for frame_idx, img_path in enumerate(frame_files):
        preds = model.track(
            str(img_path),
            verbose=False,
            conf=BALL_CONF_THRESHOLD,
            persist=True,
            tracker="bytetrack.yaml",
            device=DEVICE,
            imgsz=IMGSZ_TRACKING,
            stream=True,
        )

        for pred in preds:
            for box in pred.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                bbox = box.xyxy[0].tolist()

                if cls == PERSON_CLASS and conf >= PLAYER_CONF_THRESHOLD:
                    track_id = int(box.id[0]) if box.id is not None else -1
                    if track_id < 0:
                        continue
                    tid = str(track_id)
                    if tid not in tracks:
                        tracks[tid] = []
                    tracks[tid].append({
                        "frame": frame_idx,
                        "bbox": [round(v, 1) for v in bbox],
                        "conf": round(conf, 3),
                    })
                elif cls == BALL_CLASS and conf >= BALL_CONF_THRESHOLD:
                    ball_positions.append({
                        "frame": frame_idx,
                        "bbox": [round(v, 1) for v in bbox],
                        "conf": round(conf, 3),
                    })

    return {"tracks": tracks, "ball": ball_positions}


def detect_sequences(model, match_dir: Path) -> dict:
    """Run tracking on all sequences."""
    sequences_dir = match_dir / "sequences"
    if not sequences_dir.exists():
        return {}

    results = {}
    for seq_dir in sorted(sequences_dir.iterdir()):
        if not seq_dir.is_dir():
            continue
        results[seq_dir.name] = track_sequence(model, seq_dir)

    return results


def process_match(model, match_dir: Path, force: bool = False) -> bool:
    """Run detection on a single match. Returns True if processed."""
    det_path = match_dir / "detections.json"
    if det_path.exists() and not force:
        return False

    extraction_path = match_dir / "extraction.json"
    if not extraction_path.exists():
        return False

    keyframes = detect_keyframes(model, match_dir)
    sequences = detect_sequences(model, match_dir)

    # Quality filter: mark keyframes with full formations as tactical
    tactical_keyframes = {
        k: v for k, v in keyframes.items()
        if len(v["players"]) >= MIN_PLAYERS_TACTICAL
    }

    detections = {
        "keyframes": keyframes,
        "tactical_keyframes": list(tactical_keyframes.keys()),
        "sequences": sequences,
    }
    with open(det_path, "w") as f:
        json.dump(detections, f, indent=2)

    n_tactical = len(tactical_keyframes)
    n_players_avg = np.mean([len(kf["players"]) for kf in keyframes.values()]) if keyframes else 0
    ball_rate = sum(1 for kf in keyframes.values() if kf["ball"]) / len(keyframes) if keyframes else 0
    n_tracks = sum(len(seq.get("tracks", {})) for seq in sequences.values())

    print(f"  Keyframes: {len(keyframes)} total, {n_tactical} tactical (≥{MIN_PLAYERS_TACTICAL} players)")
    print(f"  Avg players: {n_players_avg:.0f}, ball in {ball_rate:.0%}")
    print(f"  Sequences: {len(sequences)} seqs, {n_tracks} total tracks")

    return True


def main():
    parser = argparse.ArgumentParser(description="YOLO detection + tracking on extracted frames")
    parser.add_argument("--match", type=str, help="Process single match (substring match)")
    parser.add_argument("--limit", type=int, default=0, help="Max matches to process (0=all)")
    parser.add_argument("--force", action="store_true", help="Re-detect even if detections.json exists")
    args = parser.parse_args()

    if not FRAMES_DIR.exists():
        print("ERROR: No frames directory. Run extract_frames.py first.")
        sys.exit(1)

    # Find matches with extraction data
    targets = []
    for match_dir in sorted(FRAMES_DIR.iterdir()):
        if not match_dir.is_dir():
            continue
        if not (match_dir / "extraction.json").exists():
            continue
        if args.match and args.match.lower() not in match_dir.name.lower():
            continue
        if not args.force and (match_dir / "detections.json").exists():
            continue
        targets.append(match_dir)

    if not targets:
        print("No matches to process (all detected or no matches found).")
        return

    if args.limit:
        targets = targets[:args.limit]

    print(f"Loading YOLO model...")
    model = load_model()

    print(f"Processing {len(targets)} matches\n")
    start_time = time.time()

    for idx, match_dir in enumerate(targets):
        print(f"[{idx+1}/{len(targets)}] {match_dir.name}")
        process_match(model, match_dir, force=args.force)

    elapsed = time.time() - start_time
    print(f"\nDone. {len(targets)} matches processed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
