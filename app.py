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
    frames = get_frame_images(match)
    edge_text = format_edge_badge(match)
    reasoning_text = format_reasoning(match)
    metrics_text = format_metrics(match)
    stats_text = format_stats(match)
    info_text = format_match_info(match)

    return chart, frames, edge_text, reasoning_text, metrics_text, stats_text, info_text


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

with gr.Blocks(title="Offsides — Tactical Edge Detection") as demo:
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

            with gr.Row():
                with gr.Column(scale=1):
                    prob_chart = gr.Plot(label="Probability Comparison")
                    edge_badge = gr.Markdown()
                    reasoning_box = gr.Markdown(label="VLM Assessment")

                with gr.Column(scale=1):
                    frame_gallery = gr.Gallery(
                        label="Annotated Frames (analyzed by VLM)",
                        columns=2,
                        height=400,
                    )
                    with gr.Accordion("Tactical Metrics", open=False):
                        metrics_box = gr.Markdown()
                    with gr.Accordion("Match Statistics", open=False):
                        stats_box = gr.Markdown()

            with gr.Row():
                info_box = gr.Markdown()

            match_dropdown.change(
                fn=on_match_select,
                inputs=[match_dropdown],
                outputs=[prob_chart, frame_gallery, edge_badge, reasoning_box, metrics_box, stats_box, info_box],
            )

            demo.load(
                fn=on_match_select,
                inputs=[match_dropdown],
                outputs=[prob_chart, frame_gallery, edge_badge, reasoning_box, metrics_box, stats_box, info_box],
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

        with gr.TabItem("Tactical Clips"):
            gr.Markdown("""
**Annotated video clips** showing YOLO detections, team colors, defensive lines, and compactness ellipses
rendered on tracked player sequences from recent matches.
""")

            # Precompute initial clip data
            _init_clips = get_match_clips(MATCHES[0])
            _init_labels = []
            for _c in _init_clips:
                _p = Path(_c)
                _mn = _p.parent.name.replace("_", " ").rsplit(" ", 1)[0]
                _init_labels.append(f"{_mn} — {_p.stem.replace('_', ' ').title()}")

            video_match = gr.Dropdown(
                choices=get_match_choices(),
                value=get_match_choices()[0],
                label="Select Match",
                interactive=True,
            )
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

            def update_video_tab(match_choice):
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

            def select_clip(clip_label, match_choice):
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

            video_match.change(
                fn=update_video_tab,
                inputs=[video_match],
                outputs=[video_player, clip_dropdown, video_info],
            )
            clip_dropdown.change(
                fn=select_clip,
                inputs=[clip_dropdown, video_match],
                outputs=[video_player],
            )

    gr.Markdown("""
---
**Architecture:** YouTube highlights → Frame extraction → YOLO detection → Annotation (OpenCV) → Qwen-VL 72B reasoning (AMD MI300X via vLLM on ROCm)

**How it works:** For each upcoming match, the system analyzes the most recent 3 matches for both teams. YOLO detects player positions and ball location. OpenCV renders tactical overlays (defensive lines, compactness ellipses, team colors). Qwen-VL reasons over these annotated frames alongside stats and market odds to identify where the market may be mispriced.

Built for the AMD Developer Hackathon 2026 (Track 3: Vision & Multimodal AI)
""")


if __name__ == "__main__":
    demo.launch()
