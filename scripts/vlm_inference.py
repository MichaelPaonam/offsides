#!/usr/bin/env python3
"""VLM tactical reasoning over annotated frames + stats + odds.

Sends multimodal prompts to Qwen-VL via vLLM's OpenAI-compatible API.
Produces structured tactical assessments and edge signals for demo matches.

Usage:
    python3 scripts/vlm_inference.py                           # all demo matches
    python3 scripts/vlm_inference.py --match "Dortmund_vs_PSG" # single match
    python3 scripts/vlm_inference.py --dry-run                 # print prompts, skip API
"""

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from manifest import load_manifest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRAMES_DIR = PROJECT_ROOT / "data" / "frames"
DEMO_PATH = PROJECT_ROOT / "data" / "demo_matches.json"
RESULTS_DIR = PROJECT_ROOT / "data" / "vlm_results"

VLM_BASE_URL = os.environ.get("VLM_BASE_URL", "http://localhost:8000/v1")
VLM_MODEL = os.environ.get("VLM_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct")
VLM_API_KEY = os.environ.get("VLM_API_KEY", "EMPTY")
MAX_IMAGE_WIDTH = 720

SYSTEM_PROMPT = """You are a tactical football analyst specializing in UEFA Champions League.

You will receive annotated match frames showing:
- Player positions (bounding boxes colored by team: RED = home, BLUE = away)
- Defensive line height (lines connecting back 4 per team)
- Team compactness (ellipse overlay per team)
- Ball position (yellow circle)

You also receive structured tactical metrics and match statistics.

Your job: reason over what you SEE in these frames + the statistics to assess match probabilities and identify where prediction markets may be mispriced.

When analyzing:
1. Reference specific visual evidence from the frames ("I can see the defensive line is very high in frame 3...")
2. Identify tactical trends across multiple frames from recent matches
3. Compare tactical shape against what the market price implies
4. Provide a probability estimate for home_win / draw / away_win
5. Explain your reasoning with specific data points

Output your response in this exact JSON format:
{
  "probabilities": {"home": 0.XX, "draw": 0.XX, "away": 0.XX},
  "confidence": "low|medium|high",
  "reasoning": "2-3 sentence tactical assessment",
  "visual_evidence": ["observation 1", "observation 2", "observation 3"],
  "edge_signal": "which outcome the market underprices and why"
}"""


def load_demo_matches() -> list:
    with open(DEMO_PATH) as f:
        return json.load(f)


def encode_image(image_path: Path, max_width: int = MAX_IMAGE_WIDTH) -> str:
    """Read image, resize if needed, return base64 string."""
    import cv2
    img = cv2.imread(str(image_path))
    if img is None:
        return ""
    h, w = img.shape[:2]
    if w > max_width:
        scale = max_width / w
        img = cv2.resize(img, (max_width, int(h * scale)))
    _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buffer).decode("utf-8")


def select_form_frames(match_id: str, team: str, demo_date: str, n_matches: int = 3) -> list[Path]:
    """Find the team's most recent N matches before demo_date, pick best annotated frames."""
    team_pattern = team.replace(" ", "_")
    form_matches = []
    for d in sorted(FRAMES_DIR.iterdir()):
        if not d.is_dir():
            continue
        name = d.name
        if team_pattern not in name:
            continue
        date_part = name.rsplit("_", 1)[-1]
        if date_part >= demo_date:
            continue
        annotated_dir = d / "annotated"
        if not annotated_dir.exists():
            continue
        ann_files = sorted(annotated_dir.glob("*.jpg"))
        if not ann_files:
            continue
        form_matches.append((name, date_part, ann_files))

    form_matches.sort(key=lambda x: x[1], reverse=True)
    form_matches = form_matches[:n_matches]

    selected_frames = []
    for match_name, _, ann_files in form_matches:
        det_path = FRAMES_DIR / match_name / "detections.json"
        if det_path.exists():
            with open(det_path) as f:
                dets = json.load(f)
            tactical = dets.get("tactical_keyframes", [])
            scored = []
            for af in ann_files:
                n_players = 0
                if af.name in dets.get("keyframes", {}):
                    n_players = len(dets["keyframes"][af.name].get("players", []))
                scored.append((af, n_players))
            scored.sort(key=lambda x: x[1], reverse=True)
            selected_frames.extend([s[0] for s in scored[:2]])
        else:
            selected_frames.extend(ann_files[:2])

    return selected_frames


def build_metrics_context(team: str, demo_date: str, n_matches: int = 3) -> dict:
    """Aggregate metrics from recent form matches for a team."""
    team_pattern = team.replace(" ", "_")
    form_metrics = []
    for d in sorted(FRAMES_DIR.iterdir()):
        if not d.is_dir():
            continue
        if team_pattern not in d.name:
            continue
        date_part = d.name.rsplit("_", 1)[-1]
        if date_part >= demo_date:
            continue
        metrics_path = d / "metrics.json"
        if not metrics_path.exists():
            continue
        with open(metrics_path) as f:
            m = json.load(f)
        if m.get("aggregated"):
            form_metrics.append((date_part, d.name, m["aggregated"]))

    form_metrics.sort(key=lambda x: x[0], reverse=True)
    form_metrics = form_metrics[:n_matches]

    if not form_metrics:
        return {}

    import numpy as np
    keys = ["avg_pressing_speed", "avg_def_line_movement", "avg_compactness_delta", "avg_transition_speed"]
    aggregated = {}
    for key in keys:
        values = [m[2][key] for m in form_metrics if key in m[2]]
        if values:
            aggregated[key] = round(float(np.mean(values)), 4)

    return {
        "team": team,
        "matches_analyzed": [m[1] for m in form_metrics],
        "metrics": aggregated,
    }


def build_context_text(demo_match: dict, home_metrics: dict, away_metrics: dict) -> str:
    """Build the structured text context for the VLM prompt."""
    lines = []
    lines.append(f"=== MATCH: {demo_match['home_team']} vs {demo_match['away_team']} ===")
    lines.append(f"Stage: {demo_match['stage']}")
    lines.append(f"Date: {demo_match['date']}")
    if demo_match.get("first_leg"):
        lines.append(f"First leg result: {demo_match['first_leg']}")
    lines.append("")

    lines.append("=== TACTICAL METRICS (from YOLO tracking, last 3 matches) ===")
    for label, metrics in [("Home", home_metrics), ("Away", away_metrics)]:
        team = metrics.get("team", "Unknown")
        m = metrics.get("metrics", {})
        lines.append(f"{label} ({team}):")
        lines.append(f"  Matches: {', '.join(metrics.get('matches_analyzed', []))}")
        if m.get("avg_pressing_speed"):
            lines.append(f"  Pressing speed: {m['avg_pressing_speed']:.4f} (normalized)")
        if m.get("avg_def_line_movement"):
            lines.append(f"  Defensive line movement: {m['avg_def_line_movement']:.4f}")
        if m.get("avg_compactness_delta"):
            lines.append(f"  Compactness delta: {m['avg_compactness_delta']:.3f}")
        if m.get("avg_transition_speed"):
            lines.append(f"  Transition speed: {m['avg_transition_speed']:.4f}")
        lines.append("")

    lines.append("=== STATISTICS (last 5 matches) ===")
    for side in ["home", "away"]:
        s = demo_match["stats"][side]
        lines.append(f"{s['team']}:")
        lines.append(f"  xG/match: {s['xg_last5']}, xGA/match: {s['xga_last5']}")
        lines.append(f"  PPDA: {s['ppda']}, Possession: {s['possession_pct']}%")
        lines.append(f"  Form: {s['form']}, Goals: {s['goals_scored_last5']}F/{s['goals_conceded_last5']}A")
        lines.append("")

    lines.append("=== MARKET ODDS (pre-match) ===")
    odds = demo_match["odds"]
    prob = demo_match["implied_prob"]
    lines.append(f"  {demo_match['home_team']} win: {odds['home']} (implied {prob['home']*100:.0f}%)")
    lines.append(f"  Draw: {odds['draw']} (implied {prob['draw']*100:.0f}%)")
    lines.append(f"  {demo_match['away_team']} win: {odds['away']} (implied {prob['away']*100:.0f}%)")

    return "\n".join(lines)


def build_messages(frames: list[Path], context_text: str, query: str) -> list[dict]:
    """Build OpenAI-compatible multimodal message list."""
    content = []

    for i, frame_path in enumerate(frames):
        b64 = encode_image(frame_path)
        if not b64:
            continue
        content.append({
            "type": "text",
            "text": f"[Frame {i+1}: {frame_path.parent.parent.name} — {frame_path.name}]"
        })
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    content.append({"type": "text", "text": context_text})
    content.append({"type": "text", "text": f"\n=== QUERY ===\n{query}"})

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def call_vlm(messages: list[dict]) -> str:
    """Call vLLM's OpenAI-compatible API."""
    from openai import OpenAI

    client = OpenAI(base_url=VLM_BASE_URL, api_key=VLM_API_KEY)
    response = client.chat.completions.create(
        model=VLM_MODEL,
        messages=messages,
        max_tokens=1024,
        temperature=0.3,
    )
    return response.choices[0].message.content


def parse_assessment(raw_text: str) -> dict:
    """Extract structured assessment from VLM response."""
    try:
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw_text[start:end])
    except json.JSONDecodeError:
        pass

    return {
        "probabilities": {"home": 0.33, "draw": 0.33, "away": 0.33},
        "confidence": "low",
        "reasoning": raw_text[:500],
        "visual_evidence": [],
        "edge_signal": "Unable to parse structured response",
        "raw_response": raw_text,
    }


def compute_edge(vlm_probs: dict, market_probs: dict) -> dict:
    """Compute edge: VLM probability minus market implied probability."""
    return {
        outcome: round(vlm_probs.get(outcome, 0.33) - market_probs.get(outcome, 0.33), 3)
        for outcome in ["home", "draw", "away"]
    }


def process_match(demo_match: dict, dry_run: bool = False) -> dict:
    """Run VLM inference on a single demo match."""
    match_id = demo_match["match_id"]
    home_team = demo_match["home_team"]
    away_team = demo_match["away_team"]
    demo_date = demo_match["date"]

    print(f"  Selecting form frames...")
    home_frames = select_form_frames(match_id, home_team, demo_date)
    away_frames = select_form_frames(match_id, away_team, demo_date)
    all_frames = home_frames[:4] + away_frames[:4]
    print(f"  Frames: {len(home_frames)} home + {len(away_frames)} away → {len(all_frames)} total")

    print(f"  Building metrics context...")
    home_metrics = build_metrics_context(home_team, demo_date)
    away_metrics = build_metrics_context(away_team, demo_date)

    context_text = build_context_text(demo_match, home_metrics, away_metrics)
    query = (
        f"Assess the pre-match win probabilities for {home_team} vs {away_team}. "
        f"The market prices {home_team} at {demo_match['implied_prob']['home']*100:.0f}%, "
        f"draw at {demo_match['implied_prob']['draw']*100:.0f}%, "
        f"and {away_team} at {demo_match['implied_prob']['away']*100:.0f}%. "
        f"Based on the tactical patterns visible in these recent form frames and the metrics, "
        f"do you see evidence that the market is mispriced? Provide your probability assessment."
    )

    # Deduplicate frames (same match can appear for both teams)
    seen = set()
    deduped = []
    for f in all_frames:
        if str(f) not in seen:
            seen.add(str(f))
            deduped.append(f)
    all_frames = deduped

    messages = build_messages(all_frames, context_text, query)

    if dry_run:
        print(f"\n  --- DRY RUN: Prompt Preview ---")
        print(f"  System prompt: {len(SYSTEM_PROMPT)} chars")
        print(f"  Images: {sum(1 for c in messages[1]['content'] if isinstance(c, dict) and c.get('type') == 'image_url')}")
        print(f"  Context text:\n")
        for line in context_text.split("\n")[:20]:
            print(f"    {line}")
        print(f"    ...")
        print(f"  Query: {query}")
        print(f"  Frame paths:")
        for f in all_frames:
            print(f"    {f.relative_to(PROJECT_ROOT)}")
        return {"match_id": match_id, "status": "dry_run"}

    print(f"  Calling VLM ({VLM_MODEL})...")
    start = time.time()
    raw_response = call_vlm(messages)
    elapsed = time.time() - start
    print(f"  Response received ({elapsed:.1f}s)")

    assessment = parse_assessment(raw_response)
    edge = compute_edge(
        assessment.get("probabilities", {}),
        demo_match["implied_prob"],
    )

    return {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "date": demo_date,
        "stage": demo_match["stage"],
        "market_odds": demo_match["implied_prob"],
        "actual_result": demo_match["actual_result"],
        "actual_score": demo_match["actual_score"],
        "vlm_assessment": {
            "probabilities": assessment.get("probabilities", {}),
            "edge": edge,
            "reasoning": assessment.get("reasoning", ""),
            "visual_evidence": assessment.get("visual_evidence", []),
            "confidence": assessment.get("confidence", "unknown"),
            "edge_signal": assessment.get("edge_signal", ""),
        },
        "frames_used": [str(f.relative_to(PROJECT_ROOT)) for f in all_frames],
        "metrics_context": {
            "home": home_metrics,
            "away": away_metrics,
        },
        "stats": demo_match["stats"],
        "inference_time_s": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description="VLM tactical inference on demo matches")
    parser.add_argument("--match", type=str, help="Process single match (substring)")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling API")
    args = parser.parse_args()

    demo_matches = load_demo_matches()

    if args.match:
        demo_matches = [m for m in demo_matches if args.match.lower() in m["match_id"].lower()]

    if not demo_matches:
        print("No matching demo matches found.")
        return

    print(f"VLM Inference — {len(demo_matches)} matches")
    print(f"Model: {VLM_MODEL}")
    print(f"Endpoint: {VLM_BASE_URL}")
    print(f"Dry run: {args.dry_run}\n")

    results = []
    for idx, match in enumerate(demo_matches):
        print(f"[{idx+1}/{len(demo_matches)}] {match['match_id']}")
        result = process_match(match, dry_run=args.dry_run)
        results.append(result)
        print()

    if not args.dry_run:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        output = {
            "generated_at": datetime.utcnow().isoformat(),
            "model": VLM_MODEL,
            "matches": results,
        }
        output_path = RESULTS_DIR / "results.json"
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Results saved to {output_path}")

        # Copy used frames to results dir for HF Space
        frames_out = RESULTS_DIR / "frames"
        frames_out.mkdir(exist_ok=True)
        import shutil
        for r in results:
            for fp in r.get("frames_used", []):
                src = PROJECT_ROOT / fp
                if src.exists():
                    dest = frames_out / src.parent.parent.name / src.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)


if __name__ == "__main__":
    main()
