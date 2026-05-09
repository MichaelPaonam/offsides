# Offsides

<p align="center">
  <img src="offsides-logo.png" alt="Offsides Logo" width="400">
</p>

A multimodal conversational assistant for sports prediction markets. Ask about any upcoming UEFA Champions League match — Offsides analyzes recent footage of both teams using YOLO + Qwen-VL on AMD MI300X GPUs, extracts tactical signals the market hasn't priced in (defensive shape deterioration, pressing intensity trends, transition vulnerabilities), and tells you where it disagrees with the odds.

**Track 3: Vision & Multimodal AI** | AMD Developer Hackathon 2026

**[Live Demo](https://lablab-ai-amd-developer-hackathon-offsides-socce-6e05641.hf.space)** | **[GitHub](https://github.com/MichaelPaonam/offsides)**

## Architecture

```mermaid
flowchart LR
    subgraph Input
        User[User Query\n'How does Barça vs PSG look?']
    end

    subgraph Perception
        YT[Recent Highlights\nBoth Teams] --> FE[Frame Extraction]
        FE --> YOLO[YOLO Detection]
        YOLO --> Ann[Annotated Frames\nOverlays via OpenCV]
    end

    subgraph Context
        Stats[Stats API\nxG, Form, Pressing] --> Feat[Feature Engineering]
        Odds[Market Odds] --> Ctx[Match Context]
    end

    subgraph Reasoning
        Ann --> VLM[Qwen-VL\nMultimodal Conversation\non AMD MI300X]
        Feat --> VLM
        Ctx --> VLM
        User --> VLM
    end

    VLM --> Resp["'Market says 42% Barça.\nWe say 55%. Edge: +13pts.\nPSG high line is vulnerable.'"]
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Compute | AMD Instinct MI300X (192GB HBM3) via AMD Developer Cloud |
| Cloud Image | vLLM 0.17.1 on ROCm (Ubuntu 24.04) |
| Object Detection | YOLO (player/ball tracking, formations) |
| Frame Annotation | OpenCV (render YOLO detections onto frames) |
| Reasoning Model | Qwen3-VL 32B on ROCm |
| Model Serving | vLLM on ROCm |
| Demo | Hugging Face Spaces (Gradio) |
| Stats data | football-data.co.uk (10 leagues, rolling xG/PPDA/form) |
| Odds data | Historical betting odds via Odds-portal |
| Video | YouTube UEFA Champions League highlights |
| Language | Python 3.12 |
| Tests | pytest |

## Getting Started

### Prerequisites

- Python 3.12+
- ~25 GB disk space (for highlight videos)
- AMD Developer Cloud account (for GPU inference)

### Setup

```bash
git clone https://github.com/MichaelPaonam/offsides.git
cd offsides

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Demo (local)

```bash
# Launch Gradio app (displays pre-computed results)
python app.py
# Open http://localhost:7860
```

### Run VLM Inference (requires AMD GPU)

See [docs/cloud_inference.md](docs/cloud_inference.md) for full setup.

```bash
# Quick start (with SSH tunnel to AMD MI300X droplet)
ssh -i ~/.ssh/id_ed25519_amd -f -N -L 8000:localhost:8000 root@<droplet-ip>
VLM_MODEL="Qwen/Qwen3-VL-32B-Instruct" python3 scripts/vlm_inference.py
```

### Download Match Highlights (full pipeline)

```bash
# 1. Generate fixture list (313 UCL matches across 2023-24 and 2024-25 seasons)
python scripts/generate_match_list.py

# 2. Auto-fill YouTube URLs (~16 min unattended)
python scripts/autofill_urls.py

# 3. Download videos (~2-4 hrs unattended)
python scripts/download_highlights.py

# 4. Extract frames, detect players, annotate
python scripts/extract_frames.py
python scripts/detect_players.py
python scripts/annotate_frames.py
```

### GPU Cloud Setup

See [docs/cloud_inference.md](docs/cloud_inference.md) for detailed instructions.

```bash
# SSH into AMD MI300X droplet
ssh -i ~/.ssh/id_ed25519_amd root@<droplet-ip>

# Start vLLM with Qwen3-VL 32B
docker run -d --name vllm-server \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8000:8000 --shm-size=16g \
  rocm/vllm:latest \
  vllm serve Qwen/Qwen3-VL-32B-Instruct --dtype auto --max-model-len 8192 --port 8000 --host 0.0.0.0
```

## Project Structure

```
.
├── app.py                         # Gradio demo app (HF Space)
├── scripts/
│   ├── generate_match_list.py     # Generate UCL fixture CSV
│   ├── autofill_urls.py           # Auto-fill YouTube URLs via yt-dlp search
│   ├── download_highlights.py     # Download highlight videos at 720p
│   ├── extract_frames.py          # Scene-detection frame extraction
│   ├── detect_players.py          # YOLO player/ball detection + ByteTrack
│   ├── annotate_frames.py         # Team color assignment + tactical overlays
│   ├── vlm_inference.py           # Qwen-VL multimodal inference via vLLM
│   └── manifest.py                # Video metadata helper
├── data/
│   ├── demo_matches.json          # 29 UCL knockout matches (R16–SF)
│   ├── team_kits.json             # HSV color definitions for 50 UCL teams
│   ├── match_stats.json           # League stats (xG, PPDA, form) for 51 teams
│   ├── frames_index.json          # Index of all 280 processed matches
│   ├── vlm_results/               # VLM inference output
│   │   ├── results.json           # Structured assessments (Qwen3-VL 32B)
│   │   └── frames/                # Annotated frames used by VLM
│   ├── frames/                    # Full pipeline output (280 matches, gitignored)
│   ├── league_stats/              # football-data.co.uk CSVs (10 leagues)
│   └── highlights/                # Downloaded videos (gitignored)
├── docs/
│   └── cloud_inference.md         # AMD GPU cloud runbook
├── notebooks/                     # Validation notebooks
├── requirements.txt
└── README.md
```

## How It Works

1. **Query** — User asks about a match ("How does Barcelona vs PSG look for Tuesday?")
2. **Ingest** — System pulls recent highlights for both teams (last 3-5 matches) + stats + market odds
3. **Extract** — Sample key frames from recent footage
4. **Detect** — YOLO extracts player/ball positions, formation shapes, defensive line height
5. **Annotate** — Render detections onto original frames (bounding boxes, defensive line, compactness ellipse, formation skeleton)
6. **Reason** — Qwen-VL receives annotated frames + stats + odds, produces tactical assessment via multimodal conversation
7. **Respond** — Natural language answer: probability, edge vs market, reasoning, visual evidence from frames

Users can ask follow-up questions ("What specifically is wrong with PSG's defense?") — the VLM references annotated frames in its responses.

## Technical Walkthrough

### 1. Match List Generation

`scripts/generate_match_list.py` builds a CSV of 313 UCL fixtures (2023-24, 2024-25 seasons) by scraping UEFA's fixture calendar. Output: `data/ucl_matches.csv` with columns for home/away teams, date, stage, and season.

### 2. Video Acquisition

`scripts/autofill_urls.py` uses yt-dlp search to find official highlight videos for each fixture on UEFA's YouTube channel. `scripts/download_highlights.py` downloads at 720p. Total: 283 videos (~25GB).

### 3. Frame Extraction

`scripts/extract_frames.py` uses PySceneDetect to identify shot boundaries, then applies a close-up filter (rejects frames where a single detection fills >40% of frame area) to keep only wide-angle tactical views. Outputs ~25 keyframes per match plus 5-frame sequences for tracking.

```python
# Scene detection with adaptive threshold
scene_list = detect(video_path, ContentDetector(threshold=27.0))
# Close-up filter using face/body ratio heuristic
if max_box_area / frame_area > 0.4:
    continue  # skip close-ups
```

### 4. Player Detection (YOLO)

`scripts/detect_players.py` runs YOLOv8m at 1280px resolution in batch mode (batch_size=16). Detects persons (class 0) and sports balls (class 32). For multi-frame sequences, ByteTrack assigns consistent player IDs across frames.

```bash
python scripts/detect_players.py  # processes all matches without existing detections.json
```

Output per match: `detections.json` with bounding boxes, confidence scores, track IDs, and class labels for every frame.

### 5. Annotation

`scripts/annotate_frames.py` performs:
- **Team color assignment**: KMeans clustering (k=2) on jersey pixel colors within bounding boxes, matched against known team kits via HSV distance (`data/team_kits.json`)
- **Tactical overlays**: Defensive line (lowest y-coordinate of back 4), team compactness ellipse, formation skeleton connecting players by proximity

```bash
python scripts/annotate_frames.py  # renders overlays on all detected frames
```

### 6. League Statistics

`scripts/build_stats.py` ingests football-data.co.uk CSVs (10 leagues, 6,547 domestic matches) and computes rolling metrics per team:
- **xG**: Approximated as shots on target * 0.32
- **PPDA**: Passes per defensive action (derived from fouls/possession proxy)
- **Form**: Points from last 5 league matches
- **Goals scored/conceded**: Rolling averages

Output: `data/match_stats.json` (51 UCL teams with latest domestic form).

### 7. VLM Inference

`scripts/vlm_inference.py` sends multimodal requests to Qwen3-VL 32B served via vLLM on AMD MI300X:

```bash
# Start vLLM server on AMD GPU
docker run -d --name vllm-server \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8000:8000 --shm-size=16g \
  rocm/vllm:latest \
  vllm serve Qwen/Qwen3-VL-32B-Instruct --dtype auto --max-model-len 8192

# Run inference (requires SSH tunnel or direct access to GPU)
VLM_MODEL="Qwen/Qwen3-VL-32B-Instruct" python scripts/vlm_inference.py
```

Each request includes:
- 8-12 annotated frames (4-6 per team from recent matches)
- League statistics context (xG, PPDA, form, goals)
- Market odds (when available)
- Structured prompt requesting probability estimates with tactical reasoning

The VLM returns JSON with win/draw/loss probabilities, confidence level, reasoning, edge signals, and references to specific frames as visual evidence.

### 8. Deployment

The Gradio app (`app.py`) serves pre-computed results from HF Buckets (22GB mounted at `/data` on HF Spaces) and supports live VLM queries via the remote vLLM API endpoint.

```bash
# Local development
python app.py  # http://localhost:7860

# HF Space deployment (auto-detects /data mount)
# Set secrets: VLM_BASE_URL, VLM_API_KEY, VLM_MODEL
```

## Results

Validated on 29 UCL knockout matches (Feb–Apr 2025 season), with 5 historical matches where we have actual outcomes for backtesting. The VLM correctly identified the edge on the actual winning outcome in **3 out of 5** backtested matches (60% on market upsets — matches where the favored team lost).

| Match | Stage | Market Favorite | VLM Edge | Actual Result | Correct? |
|-------|-------|----------------|----------|---------------|----------|
| Dortmund vs PSG | SF 2nd leg | PSG (56%) | **Dortmund +9pp** | Dortmund 1-0 | ✓ |
| Dortmund vs Atletico | QF 2nd leg | Atletico (1st leg lead) | **Dortmund +5pp** | Dortmund 4-2 | ✓ |
| PSG vs Barcelona | QF 2nd leg | Barcelona (agg lead) | **PSG +4pp** | PSG 4-1 | ✓ |
| Man City vs Real Madrid | QF 2nd leg | Man City (55%) | Man City +3pp | Draw (1-1, pens) | ✗ |
| Atletico vs Inter | R16 2nd leg | Inter (1st leg lead) | Draw +2pp | Atletico 2-1 | ✗ |

Additionally, 24 matches from the 2024-25 knockout stage (R16 through Semi-finals) have full VLM tactical assessments available in the demo — these show the system's probability estimates, reasoning, and visual evidence for each matchup.

**Key finding:** In the 3 correct cases, the VLM identified tactical signals (defensive compactness, transition speed, pressing intensity) that were visible in annotated frames but not captured in traditional stats — the exact kind of signal prediction markets discount.

**Model:** Qwen3-VL 32B on AMD MI300X (single GPU, 192GB HBM3) via vLLM on ROCm. Inference time: ~10s per match.

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Two-stage architecture | YOLO (perception) → Annotate → VLM (reasoning) | VLMs can't do precise tracking; YOLO can't interpret. Annotation bridges both — VLM sees the scene with spatial data overlaid |
| Prospective mode | Analyze recent form of both teams pre-match | Edge is only actionable before kickoff — this is how market users seek alpha |
| Conversational interface | Multi-turn natural language Q&A | Track 3 asks for multimodal conversational assistants; users ask tactical questions, get reasoned answers |
| Qwen-VL over Llama Vision | Qwen-based VLAs for reasoning | Stronger reasoning support, mentor-recommended, ROCm compatible |
| No fine-tuning | Base model + prompt engineering | No labeled tactical data; fine-tuning would consume the entire timeline |
| Highlights not full matches | YouTube highlights are legal and sufficient | Tactical shape visible in frames; full matches are copyrighted |
| Stats for fitness | Minutes played, pressing dropoff, rotation patterns | Highlights don't show off-ball fatigue |
| HF Space as submission | Gradio app on Hugging Face Spaces | Required deliverable (submit Space link on lablab.ai) + most likes wins HF Category Prize |
| CLI + chatbot | Terminal output + natural language queries | Judges can ask "Was Barcelona struggling in midfield?" and get reasoned answers |

## Data Sources

| Source | What it provides | Access |
|--------|-----------------|--------|
| [football-data.co.uk](https://www.football-data.co.uk) | Match results, shots, fouls, corners, cards for 10 European leagues (2023-25) | Free (CSV) |
| [Odds-portal](https://www.oddsportal.com) | Historical betting odds for UCL matches | Free (web) |
| [UEFA YouTube](https://www.youtube.com/@ChampionsLeague) | Official highlight clips | Free |

**Derived stats:** xG (approximated from shots on target × 0.32), PPDA (from fouls data), possession (from corner ratio), form (last 5 results).

## Contributing

1. Run scripts locally — GPU inference happens on AMD Developer Cloud only
2. Download highlights locally, upload only extracted frames to cloud VM

## Why AMD

The MI300X's 192GB unified HBM3 memory comfortably fits Qwen3-VL 32B on a single device with no model sharding required. This enables real-time multimodal conversation: the VLM processes annotated frames (4-6 images per team) alongside stats in a single context window, and users can ask follow-up questions without latency from cross-device communication. ROCm provides native PyTorch compatibility, and our pipeline runs identically to CUDA with zero code changes (just a different pip install URL).

## License

MIT
