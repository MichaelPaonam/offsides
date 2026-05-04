# Offsides

<p align="center">
  <img src="offsides-logo.png" alt="Offsides Logo" width="400">
</p>

A multimodal AI system that analyzes UEFA Champions League match footage alongside statistical data to detect when sports prediction markets are mispriced. Using Llama 3.2 Vision running on AMD MI300X GPUs, it extracts tactical signals from video frames — defensive shape, pressing intensity, transition patterns — that traditional stats-based models miss, then compares its probability estimates against market odds to surface edges the crowd hasn't priced in yet.

**Track 3: Vision & Multimodal AI** | AMD Developer Hackathon 2026

## Architecture

```mermaid
flowchart LR
    YT[YouTube Highlights] --> FE[Frame Extraction]
    FE --> YOLO[YOLO Detection]
    YOLO --> Struct[Player/Ball Positions\nFormations, Distances]

    Stats[Stats API\nStatsBomb / FBref] --> Feat[Feature Engineering]

    Struct --> VLM[Qwen-VL\nTactical Reasoning\non AMD MI300X]
    Feat --> VLM

    VLM --> Prob[Match Probability\nEstimate]

    Odds[Historical Odds] --> Edge[Edge Detection]
    Prob --> Edge

    Edge --> Out["Market says 35%\nWe say 52%"]
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Compute | AMD Instinct MI300X (192GB HBM3) via AMD Developer Cloud |
| Object Detection | YOLO (player/ball tracking, formations) |
| Reasoning Model | Qwen-VL on ROCm |
| Serving | vLLM / Hugging Face Transformers + Accelerate |
| Demo | Hugging Face Spaces (Gradio) |
| Stats data | StatsBomb (event-level), FBref (aggregate), API-Football |
| Odds data | Historical betting odds via Odds-portal |
| Video | YouTube UEFA Champions League highlights |
| Frame extraction | OpenCV |
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

### Run the Pipeline

```bash
# TODO: implement during development phase
python offsides.py --match "Barcelona vs PSG" --date "2024-04-10"
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

1. **Ingest** — Pull match highlight clips + structured stats (xG, pressing data, form, fitness proxies) + historical market odds
2. **Extract** — Sample key frames from video
3. **Detect** — Run YOLO on frames to get precise player/ball positions, formation shapes, defensive line height
4. **Map** — Convert YOLO detections into tactical metrics (compactness, pressing distances, transition speed)
5. **Reason** — Feed structured YOLO data + stats to Qwen-VL for tactical interpretation ("Is this team's midfield being bypassed?")
6. **Price** — Generate win/draw/loss probability
7. **Compare** — Overlay against market odds, flag discrepancies as potential edges

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Two-stage architecture | YOLO (perception) + VLM (reasoning) | VLMs are bad at precise tracking; YOLO is bad at interpretation. Use each for its strength |
| Qwen-VL over Llama Vision | Qwen-based VLAs for reasoning | Stronger reasoning support, mentor-recommended, ROCm compatible |
| No fine-tuning | Base model + prompt engineering | No labeled tactical data; fine-tuning would consume the entire timeline |
| Highlights not full matches | YouTube highlights are legal and sufficient | Tactical shape visible in frames; full matches are copyrighted |
| Stats for fitness | Minutes played, pressing dropoff, rotation patterns | Highlights don't show off-ball fatigue |
| HF Space as demo | Gradio app on Hugging Face Spaces | Prize opportunity (most likes wins), interactive, shareable URL for judges |
| CLI + chatbot | Terminal output + natural language queries | Judges can ask "Was Barcelona struggling in midfield?" and get reasoned answers |

## Data Sources

| Source | What it provides | Access |
|--------|-----------------|--------|
| [StatsBomb Open Data](https://github.com/statsbomb/open-data) | Event-level match data (passes, shots, pressures with x/y coords) | Free (GitHub) |
| [FBref](https://fbref.com) | Aggregate match stats, xG, pressing data | Free (web) |
| [API-Football](https://www.api-football.com) | Fixtures, lineups, live stats | Free tier (100 req/day) |
| [Odds-portal](https://www.oddsportal.com) | Historical betting odds | Free (web) |
| [UEFA YouTube](https://www.youtube.com/@ChampionsLeague) | Official highlight clips | Free |

## Contributing

1. Run scripts locally — GPU inference happens on AMD Developer Cloud only
2. Download highlights locally, upload only extracted frames to cloud VM

## Why AMD

The MI300X's 192GB unified HBM3 memory fits the 90B parameter Llama 3.2 Vision model on a single device — no model sharding required. ROCm provides native PyTorch compatibility, so the pipeline runs without CUDA-specific rewrites.

## License

MIT
