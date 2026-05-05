# Offsides

<p align="center">
  <img src="offsides-logo.png" alt="Offsides Logo" width="400">
</p>

A multimodal conversational assistant for sports prediction markets. Ask about any upcoming UEFA Champions League match — Offsides analyzes recent footage of both teams using YOLO + Qwen-VL on AMD MI300X GPUs, extracts tactical signals the market hasn't priced in (defensive shape deterioration, pressing intensity trends, transition vulnerabilities), and tells you where it disagrees with the odds.

**Track 3: Vision & Multimodal AI** | AMD Developer Hackathon 2026

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
| Reasoning Model | Qwen-VL on ROCm (7B dev / 72B final) |
| Model Serving | vLLM on ROCm |
| Demo | Hugging Face Spaces (Gradio) |
| Stats data | StatsBomb (event-level), FBref (aggregate) |
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
pip install yt-dlp
# pip install -r requirements.txt  (TODO: add during development)
```

### Download Match Highlights

```bash
# 1. Generate fixture list (313 UCL matches across 2023-24 and 2024-25 seasons)
python scripts/generate_match_list.py

# 2. Auto-fill YouTube URLs (~16 min unattended)
python scripts/autofill_urls.py

# 3. Spot-check the CSV, then download videos (~2-4 hrs unattended)
python scripts/download_highlights.py
```

See [scripts/README.md](scripts/README.md) for full details.

### GPU Cloud Setup

```bash
# Install CLI
brew install doctl
doctl auth init  # paste your API token

# Create GPU droplet (single MI300X, vLLM pre-installed)
doctl compute droplet create offsides-gpu \
  --size gpu-mi300x1-192gb \
  --image amddeveloperclou-vllm0171 \
  --region atl1 \
  --ssh-keys <your-fingerprint>

# SSH in
ssh -i ~/.ssh/id_ed25519_amd root@<droplet-ip>

# On the droplet: download model and serve
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct
vllm serve Qwen/Qwen2.5-VL-7B-Instruct --dtype auto
```

### Run the Pipeline

```bash
# Ask about an upcoming match
python offsides.py "How does Barcelona vs PSG look for Tuesday?"

# Ask about a past match (retrospective validation)
python offsides.py "Was the market wrong on Inter vs Atletico, March 2024?"

# Interactive conversation mode
python offsides.py --chat
> How does Barcelona vs PSG look?
> What's wrong with PSG's defense specifically?
> Show me the pressing data from their last 3 matches
```

## Project Structure

```
.
├── scripts/                    # Data collection scripts
│   ├── generate_match_list.py  # Generate UCL fixture CSV
│   ├── autofill_urls.py        # Auto-fill YouTube URLs via yt-dlp search
│   ├── download_highlights.py  # Download highlight videos at 720p
│   └── README.md               # Script usage docs
├── data/
│   ├── match_urls/             # Fixture CSVs with YouTube URLs
│   └── highlights/             # Downloaded videos (gitignored)
├── offsides-logo.png           # Project logo
└── venv/                       # Python virtual environment (gitignored)
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
| [StatsBomb Open Data](https://github.com/statsbomb/open-data) | Event-level match data (passes, shots, pressures with x/y coords) | Free (GitHub) |
| [FBref](https://fbref.com) | Aggregate match stats, xG, pressing data | Free (web) |
| [API-Football](https://www.api-football.com) | Fixtures, lineups for upcoming matches | Free tier (100 req/day) — optional, not on critical path |
| [Odds-portal](https://www.oddsportal.com) | Historical betting odds | Free (web) |
| [UEFA YouTube](https://www.youtube.com/@ChampionsLeague) | Official highlight clips | Free |

## Contributing

1. Run scripts locally — GPU inference happens on AMD Developer Cloud only
2. Download highlights locally, upload only extracted frames to cloud VM

## Why AMD

The MI300X's 192GB unified HBM3 memory fits Qwen-VL 72B on a single device — no model sharding required. This enables real-time multimodal conversation: the VLM processes annotated frames (4-6 images per team) alongside stats in a single context window, and users can ask follow-up questions without latency from cross-device communication. ROCm provides native PyTorch compatibility — our pipeline runs identically to CUDA with zero code changes (just a different pip install URL).

## License

MIT
