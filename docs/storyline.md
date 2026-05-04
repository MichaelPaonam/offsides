# Offsides — Project Story

## The Problem

Sports prediction markets are considered among the most efficient markets in the world. Billions of dollars flow through them, priced by sophisticated traders with access to rich statistical models. Yet they have a blind spot: **they can't watch the game.**

Market odds are built on structured data — xG, possession stats, recent form, head-to-head records. What they miss is the visual, tactical reality of how a team actually plays:

- A defensive line that's 5 meters higher than usual (pressing trap or vulnerability?)
- A midfield that's lost its compactness over the last 3 matches
- Set piece routines that have changed shape since the group stage
- A team's transition speed visibly declining across a congested fixture run

These are things a football analyst sees on screen but that never appear in a spreadsheet. Until now, there's been no scalable way to extract this visual intelligence and feed it into a pricing model.

## The Insight

**What if we could give a prediction market the ability to "see"?**

Multimodal AI models (vision-language models like Llama 3.2 Vision) can now interpret images and video frames — describing what they see, answering tactical questions, identifying patterns. Combine that with traditional statistical features, and you have a system that processes information the market currently ignores.

The edge isn't in having better stats. It's in having a modality the market doesn't use at all.

## Why This Matters Beyond Sports

This isn't really a sports betting project. It's a proof of concept for a broader thesis:

**Prediction markets systematically underprice visual information.**

The same approach applies to:
- Geopolitical events (satellite imagery + event contracts)
- Corporate earnings (visual signals from public company behavior)
- Weather markets (real-time imagery vs. lagging forecast models)
- Commodity markets (port/factory activity visible before reported)

Sports is the ideal testbed because outcomes are frequent, unambiguous, and data is public.

## What We Built

**Offsides** — a multimodal AI pipeline that analyzes UCL match footage alongside statistical data to identify when prediction market odds are mispriced.

### How It Works

```
Video highlights ──→ Frame extraction ──→ Tactical analysis (Vision LLM)
                                                    ↓
Match stats ──────→ Feature engineering ──→ Combined signal
                                                    ↓
Historical odds ──→ Market price ────────→ Edge detection
                                                    ↓
                                          "Market says 35% — we say 52%"
```

### The Pipeline

1. **Ingest**: Pull match highlight clips + structured stats (xG, pressing data, form, fitness proxies) + historical market odds for the same fixture
2. **Extract**: Sample key frames from video — moments that reveal tactical shape, defensive structure, pressing intensity
3. **Analyze**: Feed frames to Llama 3.2 Vision running on AMD MI300X GPUs. Ask targeted tactical questions: "Describe the defensive line shape", "How compact is the midfield?", "What's the pressing structure?"
4. **Aggregate**: Combine visual tactical insights with statistical features into a unified match assessment
5. **Price**: Generate our own win/draw/loss probability
6. **Compare**: Overlay against what the market was pricing pre-match — flag discrepancies as potential edges

### Tech Stack

- **Compute**: AMD Instinct MI300X via AMD Developer Cloud
- **Model**: Llama 3.2 Vision (11B or 90B) on ROCm
- **Serving**: vLLM or Hugging Face Transformers + Accelerate
- **Data**: StatsBomb (event-level), FBref (match stats), API-Football (fixtures/lineups), Odds-portal (historical odds)
- **Video**: YouTube UEFA highlights (legal, citable)
- **Framework**: Python, OpenCV (frame extraction), pytest

## Why AMD / ROCm

- MI300X's 192GB HBM3 memory fits the 90B vision model in a single device — no model sharding needed
- ROCm provides native PyTorch support — our pipeline runs without code changes vs. CUDA
- AMD Developer Cloud gives on-demand access without hardware ownership — ideal for a hackathon prototype that needs heavy inference but not 24/7 uptime

## How We Chose This Direction

We started from a constraint: **Track 3 requires multimodal input.** Rather than building another generic image captioning tool, we asked: *where does visual information have economic value that isn't being captured?*

Prediction markets are priced on text and numbers. They've never had eyes. That gap is the entire project.

We chose football/UCL specifically because:
- Match data is abundantly public (stats, video highlights, historical odds)
- Outcomes are binary and unambiguous (win/draw/loss)
- The market is liquid enough to be meaningful but not so efficient that no edge exists
- The domain is relatable — judges understand football

## Key Decisions

| Decision | What we chose | Why |
|----------|--------------|-----|
| Video source | YouTube highlights (not full matches) | Legal, available, sufficient for tactical snapshots |
| Stats source | StatsBomb + FBref | Event-level granularity + broad coverage |
| Fitness assessment | Stats-derived (minutes, pressing dropoff) not video | Highlights don't show off-ball fatigue |
| Model size | Start with 11B, scale to 90B if time allows | 11B fits easily, faster iteration during development |
| Demo scope | 3-5 historical matches | Enough to prove concept without data collection overhead |
| Fine-tuning | No — use base model + prompt engineering | No labeled tactical data available; fine-tuning a vision model would consume most of the hackathon timeline; prompt engineering is sufficient for frame-level Q&A |
| Player/ball tracking | No — use vision-language model for holistic scene interpretation | Direct tracking is a solved problem (StatsBomb, Second Spectrum) with proprietary setups; our value-add is tactical *interpretation*, not object detection |

## Results

*(To be filled after UAT — May 8)*

| Match | Market odds (pre-match) | Our probability | Actual outcome | Edge identified? |
|-------|------------------------|-----------------|----------------|-----------------|
| TBD | | | | |
| TBD | | | | |
| TBD | | | | |

## Limitations (Honest Assessment)

- Highlights are cherry-picked moments — we're not seeing the full tactical picture
- Vision-language models aren't trained specifically for football analysis — they describe what they see but may miss nuance a coach would catch
- 3-5 matches isn't statistically significant — this is a concept demo, not a backtested strategy
- Market efficiency means even real edges are small and fleeting

## What's Next (If We Continue)

- Full match video analysis (with proper licensing)
- Fine-tuned vision model specifically for tactical football analysis (Track 2 crossover)
- Real-time pre-match predictions for upcoming fixtures
- Expansion to other sports / prediction market categories
- Backtesting against full seasons to validate statistical significance
