"""Offsides — Tactical Edge Detection Demo.

Gradio app displaying pre-computed Qwen-VL 72B tactical assessments
of UEFA Champions League matches on AMD MI300X.
"""

import base64
import json
import os
from pathlib import Path

import gradio as gr
import plotly.graph_objects as go

APP_DIR = Path(__file__).resolve().parent
RESULTS_PATH = APP_DIR / "data" / "vlm_results" / "results.json"
DEMO_PATH = APP_DIR / "data" / "demo_matches.json"
FRAMES_DIR = APP_DIR / "data" / "vlm_results" / "frames"
CLIPS_DIR = APP_DIR / "data" / "vlm_results" / "clips"
INDEX_PATH = APP_DIR / "data" / "frames_index.json"
ALL_FRAMES_DIR = APP_DIR / "data" / "frames"

VLM_BASE_URL = os.environ.get("VLM_BASE_URL", "")
VLM_MODEL = os.environ.get("VLM_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")
VLM_API_KEY = os.environ.get("VLM_API_KEY", "EMPTY")


def load_results():
    with open(RESULTS_PATH) as f:
        results = json.load(f)
    with open(DEMO_PATH) as f:
        demos = json.load(f)
    demo_lookup = {d["match_id"]: d for d in demos}
    for m in results["matches"]:
        demo = demo_lookup.get(m["match_id"], {})
        m["first_leg"] = demo.get("first_leg", "")
        m["odds"] = demo.get("odds", {})
        m["narrative"] = demo.get("narrative", "")
    return results


RESULTS = load_results()
MATCHES = RESULTS["matches"]


def result_key(actual_result: str) -> str:
    if actual_result == "home_win":
        return "home"
    if actual_result == "away_win":
        return "away"
    return "draw"


def get_match_choices():
    choices = []
    for m in MATCHES:
        label = f"{m['home_team']} vs {m['away_team']} — {m['stage']} ({m['date']})"
        choices.append(label)
    return choices


def get_scorecard():
    correct = 0
    for m in MATCHES:
        edge = m["vlm_assessment"]["edge"]
        actual = result_key(m["actual_result"])
        best = max(edge.items(), key=lambda x: x[1])
        if best[0] == actual:
            correct += 1
    return correct, len(MATCHES)


def make_prob_chart(match):
    market = match["market_odds"]
    vlm = match["vlm_assessment"]["probabilities"]

    categories = ["Home", "Draw", "Away"]
    market_vals = [market["home"] * 100, market["draw"] * 100, market["away"] * 100]
    vlm_vals = [vlm.get("home", 0) * 100, vlm.get("draw", 0) * 100, vlm.get("away", 0) * 100]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Market Implied",
        x=categories,
        y=market_vals,
        marker_color="#6366f1",
        text=[f"{v:.0f}%" for v in market_vals],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="VLM Assessment",
        x=categories,
        y=vlm_vals,
        marker_color="#10b981",
        text=[f"{v:.0f}%" for v in vlm_vals],
        textposition="outside",
    ))
    fig.update_layout(
        barmode="group",
        title="Probability Comparison: Market vs VLM",
        yaxis_title="Probability (%)",
        yaxis_range=[0, 75],
        template="plotly_dark",
        height=350,
        margin=dict(t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def make_formation_plot(match):
    """Generate a pitch plot showing player positions from tactical keyframes."""
    import numpy as np

    home_team = match["home_team"]
    away_team = match["away_team"]
    match_id = match["match_id"]

    # Find detection data
    det_path = ALL_FRAMES_DIR / match_id / "detections.json"
    if not det_path.exists():
        # Try finding from metrics_context
        ctx = match.get("metrics_context", {})
        for side in ["home", "away"]:
            analyzed = ctx.get(side, {}).get("matches_analyzed", [])
            for m in analyzed:
                p = ALL_FRAMES_DIR / m / "detections.json"
                if p.exists():
                    det_path = p
                    break
            if det_path.exists():
                break

    if not det_path.exists():
        return None

    import json as _json
    with open(det_path) as f:
        detections = _json.load(f)

    tactical = detections.get("tactical_keyframes", [])
    if not tactical:
        return None

    # Use the first tactical keyframe (most players visible)
    best_frame = None
    best_count = 0
    for kf_name in tactical:
        kf_data = detections["keyframes"].get(kf_name, {})
        count = len(kf_data.get("players", []))
        if count > best_count:
            best_count = count
            best_frame = kf_name
            best_data = kf_data

    if best_frame is None or best_count < 8:
        return None

    players = best_data["players"]
    centers = []
    for p in players:
        bbox = p["bbox"]
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        centers.append([cx, cy])

    centers = np.array(centers)

    # Normalize to pitch coordinates (0-105 x 0-68)
    x_min, x_max = centers[:, 0].min(), centers[:, 0].max()
    y_min, y_max = centers[:, 1].min(), centers[:, 1].max()
    x_range = x_max - x_min if x_max - x_min > 0 else 1
    y_range = y_max - y_min if y_max - y_min > 0 else 1

    pitch_x = (centers[:, 0] - x_min) / x_range * 100 + 2.5
    pitch_y = (centers[:, 1] - y_min) / y_range * 64 + 2

    # KMeans to split into two teams
    from sklearn.cluster import KMeans
    kmeans = KMeans(n_clusters=2, random_state=0, n_init=10).fit(centers)
    labels = kmeans.labels_

    # Left cluster = home, right = away
    avg_x_0 = pitch_x[labels == 0].mean()
    avg_x_1 = pitch_x[labels == 1].mean()
    home_cluster = 0 if avg_x_0 < avg_x_1 else 1

    home_x = pitch_x[labels == home_cluster]
    home_y = pitch_y[labels == home_cluster]
    away_x = pitch_x[labels != home_cluster]
    away_y = pitch_y[labels != home_cluster]

    # Build Plotly pitch figure
    fig = go.Figure()

    # Pitch outline
    pitch_shapes = [
        dict(type="rect", x0=0, y0=0, x1=105, y1=68, line=dict(color="#555", width=2)),
        dict(type="line", x0=52.5, y0=0, x1=52.5, y1=68, line=dict(color="#555", width=1)),
        dict(type="circle", x0=52.5-9.15, y0=34-9.15, x1=52.5+9.15, y1=34+9.15, line=dict(color="#555", width=1)),
        # Penalty areas
        dict(type="rect", x0=0, y0=13.84, x1=16.5, y1=54.16, line=dict(color="#555", width=1)),
        dict(type="rect", x0=88.5, y0=13.84, x1=105, y1=54.16, line=dict(color="#555", width=1)),
        # Goal areas
        dict(type="rect", x0=0, y0=24.84, x1=5.5, y1=43.16, line=dict(color="#555", width=1)),
        dict(type="rect", x0=99.5, y0=24.84, x1=105, y1=43.16, line=dict(color="#555", width=1)),
    ]

    fig.add_trace(go.Scatter(
        x=home_x, y=home_y, mode="markers",
        marker=dict(size=14, color="#3b82f6", line=dict(width=2, color="white")),
        name=home_team,
    ))
    fig.add_trace(go.Scatter(
        x=away_x, y=away_y, mode="markers",
        marker=dict(size=14, color="#ef4444", line=dict(width=2, color="white")),
        name=away_team,
    ))

    # Ball position
    ball = best_data.get("ball")
    if ball:
        ball_cx = (ball["bbox"][0] + ball["bbox"][2]) / 2
        ball_cy = (ball["bbox"][1] + ball["bbox"][3]) / 2
        ball_px = (ball_cx - x_min) / x_range * 100 + 2.5
        ball_py = (ball_cy - y_min) / y_range * 64 + 2
        fig.add_trace(go.Scatter(
            x=[ball_px], y=[ball_py], mode="markers",
            marker=dict(size=10, color="#fbbf24", symbol="circle",
                        line=dict(width=2, color="white")),
            name="Ball",
        ))

    fig.update_layout(
        plot_bgcolor="#1a1a1a",
        paper_bgcolor="#111111",
        font_color="white",
        shapes=pitch_shapes,
        xaxis=dict(range=[-2, 107], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[-2, 70], showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x"),
        margin=dict(l=10, r=10, t=40, b=10),
        height=350,
        title=dict(text=f"Formation — {best_frame}", font=dict(size=13)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def get_frame_images(match):
    images = []
    for fp in match.get("frames_used", []):
        parts = Path(fp).parts
        match_dir = parts[2]
        frame_name = parts[-1]
        local_path = FRAMES_DIR / match_dir / frame_name
        if local_path.exists():
            images.append(str(local_path))
    return images


def get_match_clips(match):
    """Get annotated video clips for a match's source matches."""
    clips = []
    for fp in match.get("frames_used", []):
        parts = Path(fp).parts
        if len(parts) >= 3:
            match_dir = parts[2]
            clip_dir = CLIPS_DIR / match_dir
            if clip_dir.exists():
                for mp4 in sorted(clip_dir.glob("*.mp4")):
                    if str(mp4) not in clips:
                        clips.append(str(mp4))
    return clips


def load_frame_index():
    """Load the pre-built frame index for team comparison."""
    if not INDEX_PATH.exists():
        return {"teams": [], "matches": {}}
    with open(INDEX_PATH) as f:
        return json.load(f)


FRAME_INDEX = load_frame_index()


def get_team_list():
    """Return sorted list of team names formatted for display."""
    return [t.replace("_", " ") for t in FRAME_INDEX.get("teams", [])]


def get_team_form(team: str, n: int = 3) -> tuple[list[str], dict]:
    """Get last N matches for a team: frames + averaged metrics."""
    team_pat = team.replace(" ", "_")
    team_matches = []
    for match_name, data in FRAME_INDEX.get("matches", {}).items():
        if team_pat in (data["home"], data["away"]):
            team_matches.append((match_name, data))

    team_matches.sort(key=lambda x: x[1]["date"], reverse=True)
    team_matches = team_matches[:n]

    frames = []
    metrics_list = []
    for match_name, data in team_matches:
        ann_dir = ALL_FRAMES_DIR / match_name / "annotated"
        for fname in data["frames"][:2]:
            fpath = ann_dir / fname
            if fpath.exists():
                frames.append(str(fpath))
        if data.get("metrics"):
            metrics_list.append(data["metrics"])

    avg_metrics = {}
    if metrics_list:
        keys = ["avg_pressing_speed", "avg_def_line_movement", "avg_compactness_delta", "avg_transition_speed"]
        for key in keys:
            values = [m[key] for m in metrics_list if key in m]
            if values:
                avg_metrics[key] = round(sum(values) / len(values), 4)

    return frames, avg_metrics


def get_h2h(team_a: str, team_b: str) -> tuple[list[str], dict]:
    """Get head-to-head frames and metrics between two teams."""
    pat_a = team_a.replace(" ", "_")
    pat_b = team_b.replace(" ", "_")
    h2h_matches = []

    for match_name, data in FRAME_INDEX.get("matches", {}).items():
        if pat_a in (data["home"], data["away"]) and pat_b in (data["home"], data["away"]):
            h2h_matches.append((match_name, data))

    h2h_matches.sort(key=lambda x: x[1]["date"], reverse=True)

    frames = []
    metrics_list = []
    for match_name, data in h2h_matches[:3]:
        ann_dir = ALL_FRAMES_DIR / match_name / "annotated"
        for fname in data["frames"][:2]:
            fpath = ann_dir / fname
            if fpath.exists():
                frames.append(str(fpath))
        if data.get("metrics"):
            metrics_list.append(data["metrics"])

    avg_metrics = {}
    if metrics_list:
        keys = ["avg_pressing_speed", "avg_def_line_movement", "avg_compactness_delta", "avg_transition_speed"]
        for key in keys:
            values = [m[key] for m in metrics_list if key in m]
            if values:
                avg_metrics[key] = round(sum(values) / len(values), 4)

    return frames, avg_metrics


def format_metrics_md(metrics: dict, team_name: str) -> str:
    """Format metrics dict as markdown."""
    if not metrics:
        return f"*No metrics available for {team_name}*"
    lines = [f"**{team_name}** (avg last 3 matches):"]
    labels = {
        "avg_pressing_speed": "Pressing Speed",
        "avg_def_line_movement": "Defensive Line Movement",
        "avg_compactness_delta": "Compactness Delta",
        "avg_transition_speed": "Transition Speed",
    }
    for key, label in labels.items():
        if key in metrics:
            lines.append(f"- {label}: `{metrics[key]:.4f}`")
    return "\n".join(lines)


def compare_teams(team_a: str, team_b: str):
    """Main comparison function — returns all outputs for the Compare tab."""
    if not team_a or not team_b:
        empty = [], "", [], "", [], ""
        return empty

    frames_a, metrics_a = get_team_form(team_a)
    frames_b, metrics_b = get_team_form(team_b)
    h2h_frames, h2h_metrics = get_h2h(team_a, team_b)

    metrics_a_md = format_metrics_md(metrics_a, team_a)
    metrics_b_md = format_metrics_md(metrics_b, team_b)

    if h2h_frames:
        h2h_md = f"**{len(h2h_frames)//2} prior matchups found**\n\n" + format_metrics_md(h2h_metrics, f"{team_a} vs {team_b} H2H")
    else:
        h2h_md = f"*No head-to-head matches found between {team_a} and {team_b} in the dataset.*"

    return frames_a, metrics_a_md, frames_b, metrics_b_md, h2h_frames, h2h_md


def predict_matchup(team_a: str, team_b: str):
    """Run live VLM inference on a custom matchup."""
    if not VLM_BASE_URL:
        return "**GPU Offline** — Connect AMD MI300X to enable live predictions. Set `VLM_BASE_URL` as a Space secret."

    if not team_a or not team_b or team_a == team_b:
        return "Select two different teams to predict."

    try:
        from openai import OpenAI

        frames_a, metrics_a = get_team_form(team_a)
        frames_b, metrics_b = get_team_form(team_b)
        h2h_frames, h2h_metrics = get_h2h(team_a, team_b)

        content = []
        if frames_a:
            content.append({"type": "text", "text": f"--- {team_a.upper()} RECENT FORM ---"})
            for fp in frames_a[:4]:
                b64 = encode_frame(fp)
                if b64:
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

        if frames_b:
            content.append({"type": "text", "text": f"--- {team_b.upper()} RECENT FORM ---"})
            for fp in frames_b[:4]:
                b64 = encode_frame(fp)
                if b64:
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

        if h2h_frames:
            content.append({"type": "text", "text": f"--- HEAD-TO-HEAD ---"})
            for fp in h2h_frames[:4]:
                b64 = encode_frame(fp)
                if b64:
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

        context_lines = [
            f"=== MATCHUP: {team_a} vs {team_b} ===",
            f"\n{team_a} tactical metrics (last 3 matches):",
        ]
        for k, v in metrics_a.items():
            context_lines.append(f"  {k}: {v}")
        context_lines.append(f"\n{team_b} tactical metrics (last 3 matches):")
        for k, v in metrics_b.items():
            context_lines.append(f"  {k}: {v}")
        if h2h_metrics:
            context_lines.append(f"\nHead-to-head metrics:")
            for k, v in h2h_metrics.items():
                context_lines.append(f"  {k}: {v}")

        content.append({"type": "text", "text": "\n".join(context_lines)})
        content.append({"type": "text", "text": (
            f"Based on {team_a}'s recent form, {team_b}'s recent form, and their head-to-head history, "
            f"which team has the tactical advantage? Provide your assessment as: "
            f"probabilities (home/draw/away), confidence, and 2-3 sentence reasoning."
        )})

        system_msg = (
            "You are a tactical football analyst. Analyze the annotated frames showing "
            "player positions, defensive lines, and team compactness. Compare the tactical "
            "patterns of both teams and assess who has the advantage."
        )

        client = OpenAI(base_url=VLM_BASE_URL, api_key=VLM_API_KEY)
        response = client.chat.completions.create(
            model=VLM_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": content},
            ],
            max_tokens=512,
            temperature=0.3,
        )
        return f"**VLM Prediction ({VLM_MODEL}):**\n\n{response.choices[0].message.content}"

    except Exception as e:
        return f"**Error:** {str(e)}"


def format_edge_badge(match):
    edge = match["vlm_assessment"]["edge"]
    actual = result_key(match["actual_result"])
    best = max(edge.items(), key=lambda x: x[1])
    best_outcome, best_val = best

    correct = best_outcome == actual
    outcome_label = {"home": match["home_team"], "draw": "Draw", "away": match["away_team"]}
    badge = f"**Edge: +{best_val*100:.0f}pp on {outcome_label[best_outcome]}**"

    if correct:
        return f"### {badge}\n\nActual result: **{match['actual_score']}** ({match['actual_result'].replace('_', ' ')}) — CORRECT"
    else:
        return f"### {badge}\n\nActual result: **{match['actual_score']}** ({match['actual_result'].replace('_', ' ')})"


def format_reasoning(match):
    a = match["vlm_assessment"]
    lines = []
    lines.append(f"**Confidence:** {a['confidence']}")
    lines.append("")
    lines.append(f"**Reasoning:** {a['reasoning']}")
    lines.append("")
    lines.append("**Visual Evidence:**")
    for ev in a.get("visual_evidence", []):
        lines.append(f"- {ev}")
    lines.append("")
    lines.append(f"**Edge Signal:** {a['edge_signal']}")
    return "\n".join(lines)


def format_metrics(match):
    ctx = match.get("metrics_context", {})
    lines = []
    for side, label in [("home", match["home_team"]), ("away", match["away_team"])]:
        data = ctx.get(side, {})
        metrics = data.get("metrics", {})
        if not metrics:
            continue
        lines.append(f"**{label}** (last 3 matches):")
        matches_analyzed = data.get("matches_analyzed", [])
        if matches_analyzed:
            lines.append(f"- Matches: {', '.join(m.replace('_', ' ') for m in matches_analyzed)}")
        if "avg_pressing_speed" in metrics:
            lines.append(f"- Pressing speed: {metrics['avg_pressing_speed']:.4f}")
        if "avg_def_line_movement" in metrics:
            lines.append(f"- Defensive line movement: {metrics['avg_def_line_movement']:.4f}")
        if "avg_compactness_delta" in metrics:
            lines.append(f"- Compactness delta: {metrics['avg_compactness_delta']:.3f}")
        if "avg_transition_speed" in metrics:
            lines.append(f"- Transition speed: {metrics['avg_transition_speed']:.4f}")
        lines.append("")
    return "\n".join(lines)


def format_metrics_side(match, side):
    ctx = match.get("metrics_context", {})
    data = ctx.get(side, {})
    metrics = data.get("metrics", {})
    label = match["home_team"] if side == "home" else match["away_team"]
    lines = []
    lines.append(f"**{label}** (last 3 matches):")
    lines.append("")
    matches_analyzed = data.get("matches_analyzed", [])
    if matches_analyzed:
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        if "avg_pressing_speed" in metrics:
            lines.append(f"| Pressing Speed | {metrics['avg_pressing_speed']:.4f} |")
        if "avg_def_line_movement" in metrics:
            lines.append(f"| Defensive Line Movement | {metrics['avg_def_line_movement']:.4f} |")
        if "avg_compactness_delta" in metrics:
            lines.append(f"| Compactness Delta | {metrics['avg_compactness_delta']:.3f} |")
        if "avg_transition_speed" in metrics:
            lines.append(f"| Transition Speed | {metrics['avg_transition_speed']:.4f} |")
        lines.append("")
        lines.append("*Matches analyzed:*")
        for m in matches_analyzed:
            lines.append(f"- {m.replace('_', ' ')}")
    else:
        lines.append("*No tactical data available*")
    return "\n".join(lines)


def format_stats(match):
    stats = match.get("stats", {})
    lines = []
    for side in ["home", "away"]:
        s = stats.get(side, {})
        if not s:
            continue
        lines.append(f"**{s.get('team', side.title())}:**")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| xG/match | {s.get('xg_last5', '-')} |")
        lines.append(f"| xGA/match | {s.get('xga_last5', '-')} |")
        lines.append(f"| PPDA | {s.get('ppda', '-')} |")
        lines.append(f"| Possession | {s.get('possession_pct', '-')}% |")
        lines.append(f"| Form | {s.get('form', '-')} |")
        lines.append(f"| Goals (last 5) | {s.get('goals_scored_last5', '-')}F / {s.get('goals_conceded_last5', '-')}A |")
        lines.append("")
    return "\n".join(lines)


def format_stats_side(match, side):
    stats = match.get("stats", {})
    s = stats.get(side, {})
    label = match["home_team"] if side == "home" else match["away_team"]
    lines = []
    lines.append(f"**{label}:**")
    lines.append("")
    if not s:
        lines.append("*No stats available*")
        return "\n".join(lines)
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| xG — Expected Goals/match | {s.get('xg_last5', '-')} |")
    lines.append(f"| xGA — Expected Goals Against/match | {s.get('xga_last5', '-')} |")
    lines.append(f"| PPDA — Passes Per Defensive Action | {s.get('ppda', '-')} |")
    lines.append(f"| Possession | {s.get('possession_pct', '-')}% |")
    lines.append(f"| Form (last 5) | {s.get('form', '-')} |")
    lines.append(f"| Goals (last 5) | {s.get('goals_scored_last5', '-')}F / {s.get('goals_conceded_last5', '-')}A |")
    return "\n".join(lines)


def format_match_info(match):
    lines = []
    lines.append(f"**{match['home_team']}** vs **{match['away_team']}**")
    lines.append(f"- Stage: {match['stage']}")
    lines.append(f"- Date: {match['date']}")
    if match.get("first_leg"):
        lines.append(f"- First leg: {match['first_leg']}")
    odds = match.get("odds", {})
    if odds:
        lines.append(f"- Decimal odds: {match['home_team']} {odds.get('home', '-')} / Draw {odds.get('draw', '-')} / {match['away_team']} {odds.get('away', '-')}")
    market = match["market_odds"]
    lines.append(f"- Implied probability: {match['home_team']} {market['home']*100:.0f}% / Draw {market['draw']*100:.0f}% / {match['away_team']} {market['away']*100:.0f}%")
    if match.get("narrative"):
        lines.append(f"\n*{match['narrative']}*")
    return "\n".join(lines)


def on_match_select(choice):
    idx = get_match_choices().index(choice)
    match = MATCHES[idx]

    chart = make_prob_chart(match)
    formation = make_formation_plot(match)
    frames = get_frame_images(match)
    edge_text = format_edge_badge(match)
    reasoning_text = format_reasoning(match)
    metrics_home = format_metrics_side(match, "home")
    metrics_away = format_metrics_side(match, "away")
    stats_home = format_stats_side(match, "home")
    stats_away = format_stats_side(match, "away")
    info_text = format_match_info(match)

    return chart, formation, frames, edge_text, reasoning_text, metrics_home, metrics_away, stats_home, stats_away, info_text


def update_video_for_match(match_choice):
    idx = get_match_choices().index(match_choice)
    match = MATCHES[idx]
    clips = get_match_clips(match)
    labels = []
    for clip in clips:
        p = Path(clip)
        match_name = p.parent.name.replace("_", " ").rsplit(" ", 1)[0]
        seq = p.stem.replace("_", " ").title()
        labels.append(f"{match_name} — {seq}")
    first_clip = clips[0] if clips else None
    info = f"**{len(clips)} clips** from recent matches of {match['home_team']} and {match['away_team']}" if clips else "No clips available."
    return (
        first_clip,
        gr.update(choices=labels, value=labels[0] if labels else None),
        info,
    )


def select_clip_for_match(clip_label, match_choice):
    idx = get_match_choices().index(match_choice)
    match = MATCHES[idx]
    clips = get_match_clips(match)
    labels = []
    for clip in clips:
        p = Path(clip)
        match_name = p.parent.name.replace("_", " ").rsplit(" ", 1)[0]
        seq = p.stem.replace("_", " ").title()
        labels.append(f"{match_name} — {seq}")
    if clip_label in labels:
        return clips[labels.index(clip_label)]
    return clips[0] if clips else None


def build_live_context(match_idx: int) -> str:
    match = MATCHES[match_idx]
    lines = []
    lines.append(f"Match: {match['home_team']} vs {match['away_team']} ({match['stage']}, {match['date']})")
    market = match["market_odds"]
    lines.append(f"Market implied: {match['home_team']} {market['home']*100:.0f}% / Draw {market['draw']*100:.0f}% / {match['away_team']} {market['away']*100:.0f}%")
    stats = match.get("stats", {})
    for side in ["home", "away"]:
        s = stats.get(side, {})
        if s:
            lines.append(f"{s['team']}: xG={s.get('xg_last5')}, PPDA={s.get('ppda')}, Poss={s.get('possession_pct')}%, Form={s.get('form')}")
    ctx = match.get("metrics_context", {})
    for side in ["home", "away"]:
        data = ctx.get(side, {})
        metrics = data.get("metrics", {})
        if metrics:
            lines.append(f"{data.get('team', side)} tactical: pressing={metrics.get('avg_pressing_speed', 0):.4f}, def_line={metrics.get('avg_def_line_movement', 0):.4f}, compactness={metrics.get('avg_compactness_delta', 0):.3f}, transition={metrics.get('avg_transition_speed', 0):.4f}")
    a = match["vlm_assessment"]
    lines.append(f"VLM assessment: H={a['probabilities']['home']:.0%} D={a['probabilities']['draw']:.0%} A={a['probabilities']['away']:.0%}")
    lines.append(f"Edge: {a['edge']}")
    lines.append(f"Reasoning: {a['reasoning']}")
    return "\n".join(lines)


def encode_frame(path: str, max_width: int = 512) -> str:
    try:
        import cv2
        img = cv2.imread(path)
        if img is None:
            return ""
        h, w = img.shape[:2]
        if w > max_width:
            scale = max_width / w
            img = cv2.resize(img, (max_width, int(h * scale)))
        _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return base64.b64encode(buffer).decode("utf-8")
    except ImportError:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


def live_query(match_choice: str, user_question: str, history: list):
    if not VLM_BASE_URL:
        history.append({"role": "assistant", "content": "Live inference is not available — no VLM endpoint configured. Set VLM_BASE_URL as a Space secret."})
        return history, history

    if not user_question.strip():
        return history, history

    history.append({"role": "user", "content": user_question})

    try:
        from openai import OpenAI

        idx = get_match_choices().index(match_choice)
        match = MATCHES[idx]
        context = build_live_context(idx)

        frames = get_frame_images(match)
        content = []
        for frame_path in frames[:4]:
            b64 = encode_frame(frame_path)
            if b64:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

        content.append({"type": "text", "text": f"Match context:\n{context}\n\nUser question: {user_question}"})

        system_msg = (
            "You are a tactical football analyst for UEFA Champions League. "
            "You have access to annotated match frames showing player positions (colored bounding boxes), "
            "defensive lines, and compactness ellipses. You also have tactical metrics and match statistics. "
            "Answer the user's question with specific references to what you observe in the frames and data. "
            "Be concise but specific."
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": content},
        ]

        client = OpenAI(base_url=VLM_BASE_URL, api_key=VLM_API_KEY)
        response = client.chat.completions.create(
            model=VLM_MODEL,
            messages=messages,
            max_tokens=512,
            temperature=0.3,
        )
        answer = response.choices[0].message.content
        history.append({"role": "assistant", "content": answer})

    except Exception as e:
        history.append({"role": "assistant", "content": f"Error: {str(e)}"})

    return history, history


correct, total = get_scorecard()
live_available = bool(VLM_BASE_URL)

with gr.Blocks(
    title="Offsides — Tactical Edge Detection",
) as demo:
    gr.Markdown(f"""
# Offsides — Tactical Edge Detection

**Where the market gets it wrong.** Multimodal AI analyzes UEFA Champions League footage using YOLO + Qwen-VL 72B on AMD MI300X to detect mispriced prediction markets.

**Scorecard: {correct}/{total} correct edge calls** | Model: {RESULTS['model']} | Generated: {RESULTS['generated_at'][:10]}
""")

    with gr.Tabs():
        with gr.TabItem("Pre-computed Results"):
            with gr.Row():
                match_dropdown = gr.Dropdown(
                    choices=get_match_choices(),
                    value=get_match_choices()[0],
                    label="Select Match",
                    interactive=True,
                )

            # Video Player
            _init_clips = get_match_clips(MATCHES[0])
            _init_labels = []
            for _c in _init_clips:
                _p = Path(_c)
                _mn = _p.parent.name.replace("_", " ").rsplit(" ", 1)[0]
                _init_labels.append(f"{_mn} — {_p.stem.replace('_', ' ').title()}")

            with gr.Row():
                with gr.Column(scale=2):
                    video_player = gr.Video(
                        value=_init_clips[0] if _init_clips else None,
                        label="Tactical Overlay Clip",
                        height=400,
                        autoplay=True,
                        loop=True,
                    )
                with gr.Column(scale=1):
                    clip_dropdown = gr.Dropdown(
                        choices=_init_labels,
                        value=_init_labels[0] if _init_labels else None,
                        label="Select Clip",
                        interactive=True,
                    )
                    video_info = gr.Markdown(
                        f"**{len(_init_clips)} clips** from recent matches of {MATCHES[0]['home_team']} and {MATCHES[0]['away_team']}"
                        if _init_clips else "No clips available."
                    )

            # Annotated Frames Gallery
            frame_gallery = gr.Gallery(
                label="Annotated Frames (analyzed by VLM)",
                columns=2,
                height=350,
            )

            # Formation Plot
            formation_plot = gr.Plot(label="Formation Map")

            # Tactical Metrics (side-by-side)
            gr.Markdown("### Tactical Metrics", elem_classes=["section-heading"])
            with gr.Row():
                with gr.Column():
                    metrics_home_box = gr.Markdown(elem_classes=["center-content"])
                with gr.Column():
                    metrics_away_box = gr.Markdown(elem_classes=["center-content"])

            # Match Statistics (side-by-side)
            gr.Markdown("### Match Statistics", elem_classes=["section-heading"])
            with gr.Row():
                with gr.Column():
                    stats_home_box = gr.Markdown(elem_classes=["center-content"])
                with gr.Column():
                    stats_away_box = gr.Markdown(elem_classes=["center-content"])

            # Probability Comparison
            with gr.Row():
                gr.Column(scale=1)
                with gr.Column(scale=2):
                    prob_chart = gr.Plot(label="Probability Comparison")
                gr.Column(scale=1)

            # Edge + Reasoning + Info
            edge_badge = gr.Markdown()
            reasoning_box = gr.Markdown()
            info_box = gr.Markdown()

            match_dropdown.change(
                fn=on_match_select,
                inputs=[match_dropdown],
                outputs=[prob_chart, formation_plot, frame_gallery, edge_badge, reasoning_box, metrics_home_box, metrics_away_box, stats_home_box, stats_away_box, info_box],
            )
            match_dropdown.change(
                fn=update_video_for_match,
                inputs=[match_dropdown],
                outputs=[video_player, clip_dropdown, video_info],
            )
            clip_dropdown.change(
                fn=select_clip_for_match,
                inputs=[clip_dropdown, match_dropdown],
                outputs=[video_player],
            )

            demo.load(
                fn=on_match_select,
                inputs=[match_dropdown],
                outputs=[prob_chart, formation_plot, frame_gallery, edge_badge, reasoning_box, metrics_home_box, metrics_away_box, stats_home_box, stats_away_box, info_box],
            )

        with gr.TabItem("Live Query" + (" (Active)" if live_available else " (Offline)")):
            if not live_available:
                gr.Markdown("""
**Live inference is currently offline.** The AMD MI300X GPU is not connected.

To enable live queries, set the `VLM_BASE_URL` Space secret to the vLLM endpoint
(e.g., `http://<droplet-ip>:8000/v1`).
""")
            else:
                gr.Markdown(f"""
**Live VLM connected** — Ask tactical questions about any match. The model ({VLM_MODEL}) will reason
over the annotated frames and tactical data in real time on AMD MI300X.
""")

            live_match = gr.Dropdown(
                choices=get_match_choices(),
                value=get_match_choices()[0],
                label="Match Context",
                interactive=True,
            )
            chatbot = gr.Chatbot(label="Tactical Q&A", height=400)
            chat_state = gr.State([])
            with gr.Row():
                user_input = gr.Textbox(
                    placeholder="Ask a tactical question (e.g., 'What's wrong with PSG's defensive line?')",
                    label="Your Question",
                    scale=4,
                )
                send_btn = gr.Button("Ask", variant="primary", scale=1)

            send_btn.click(
                fn=live_query,
                inputs=[live_match, user_input, chat_state],
                outputs=[chatbot, chat_state],
            ).then(fn=lambda: "", outputs=[user_input])

            user_input.submit(
                fn=live_query,
                inputs=[live_match, user_input, chat_state],
                outputs=[chatbot, chat_state],
            ).then(fn=lambda: "", outputs=[user_input])

        with gr.TabItem("Compare Teams"):
            gr.Markdown("""
**Pick any two teams** to compare their recent tactical form, head-to-head history, and optionally get a live VLM prediction.
50 UCL teams available with annotated frames from 273 matches.
""")
            with gr.Row():
                team_a_dd = gr.Dropdown(
                    choices=get_team_list(),
                    value="Dortmund",
                    label="Team A",
                    interactive=True,
                )
                team_b_dd = gr.Dropdown(
                    choices=get_team_list(),
                    value="PSG",
                    label="Team B",
                    interactive=True,
                )

            with gr.Row():
                compare_btn = gr.Button("Compare", variant="primary")

            with gr.Row():
                with gr.Column():
                    gallery_a = gr.Gallery(label="Team A — Recent Form", columns=3, height=250)
                    metrics_a_md = gr.Markdown()
                with gr.Column():
                    gallery_b = gr.Gallery(label="Team B — Recent Form", columns=3, height=250)
                    metrics_b_md = gr.Markdown()

            with gr.Row():
                with gr.Column():
                    h2h_gallery = gr.Gallery(label="Head-to-Head", columns=3, height=200)
                    h2h_md = gr.Markdown()

            with gr.Row():
                predict_btn = gr.Button(
                    "Predict Winner (Live VLM)" if live_available else "Predict Winner (GPU Offline)",
                    variant="secondary",
                )
            prediction_output = gr.Markdown()

            compare_btn.click(
                fn=compare_teams,
                inputs=[team_a_dd, team_b_dd],
                outputs=[gallery_a, metrics_a_md, gallery_b, metrics_b_md, h2h_gallery, h2h_md],
            )
            predict_btn.click(
                fn=predict_matchup,
                inputs=[team_a_dd, team_b_dd],
                outputs=[prediction_output],
            )

    gr.Markdown("""
---
**Architecture:** YouTube highlights → Frame extraction → YOLO detection → Annotation (OpenCV) → Qwen-VL 72B reasoning (AMD MI300X via vLLM on ROCm)

**How it works:** For each upcoming match, the system analyzes the most recent 3 matches for both teams. YOLO detects player positions and ball location. OpenCV renders tactical overlays (defensive lines, compactness ellipses, team colors). Qwen-VL reasons over these annotated frames alongside stats and market odds to identify where the market may be mispriced.

Built for the AMD Developer Hackathon 2026 (Track 3: Vision & Multimodal AI)
""")


if __name__ == "__main__":
    demo.launch(
        theme=gr.themes.Monochrome(font=gr.themes.GoogleFont("Inter")),
        js="() => { document.documentElement.classList.add('dark'); }",
        css="""
            .center-content { display: flex !important; flex-direction: column !important; align-items: center !important; }
            .center-content table { margin: 0 auto !important; }
            .center-content th, .center-content td { padding: 8px 12px !important; }
            .center-content th { text-align: left !important; font-weight: 600 !important; }
            .center-content ul { text-align: left !important; }
            .section-heading { text-align: center !important; }
        """,
    )
