# Offsides — Research Plan

UCL multimodal prediction market project.

2-day research phase before implementation begins.

---

## Day 1: Foundations & Data Landscape (6 hours)

### Concepts to Understand (~2.5 hrs)

**Multimodal AI — how it works under the hood (1 hr)**
- Vision-language models architecture: image encoder (ViT) + LLM decoder
- How Llama 3.2 Vision processes video (it doesn't natively — you feed frames)
- Frame sampling strategies: how many frames per second do you need to capture tactical info?
- Difference between: image captioning, visual Q&A, and video understanding

**Sports analytics fundamentals (1 hr)**
- xG (expected goals) — what it measures and its limitations
- Pre-match vs in-play models — what signals matter when
- What professional analysts look for in video that stats miss: pressing traps, defensive transitions, set piece routines, compactness

**Prediction markets mechanics (30 min)**
- How odds/prices move in response to information
- Market efficiency in sports — where are the known inefficiencies?
- Polymarket / betting exchange APIs — how to pull historical odds for past UCL matches

### Data Research (~2.5 hrs)

**Data source strategy:**

1. **StatsBomb open data (primary for deep analysis)** — Free on GitHub, event-level granularity (every pass, shot, carry, pressure, duel with x/y coordinates). Includes "freeze frames" (positions of all players at key moments). Use for demo matches and pipeline prototyping. Caveat: limited competition coverage — verify which UCL seasons are available.

2. **FBref (supplement for broad coverage)** — Covers every UCL match every season. Aggregate stats (xG, pressing, possession) and match-level summaries. Less granular than StatsBomb but no coverage gaps. Use for fitness/workload features across many matches.

3. **API-Football** — Programmatic access to fixtures, lineups, live stats. Free tier (100 req/day).

Day 1 action item: Check if StatsBomb open dataset includes recent UCL matches. If not, use StatsBomb data from other competitions (e.g., Champions League 2003/04, Euro 2020) for prototyping, and lean on FBref + API-Football for actual UCL data.

| What | Where to look | Time |
|------|--------------|------|
| StatsBomb open data | github.com/statsbomb/open-data — check UCL coverage | 45 min |
| FBref match stats (xG, possession, shots) | FBref.com | 30 min |
| Historical odds / market prices | Odds-portal.com, Betfair historical data, Polymarket API | 45 min |
| Video highlights | YouTube UEFA channel | 30 min |
| Player/team form data | Transfermarkt, FBref | 30 min |

### Day 1 Checkpoints (~1 hr)

Answer these before moving to Day 2:

1. Can you reliably get video highlights + corresponding stats + historical odds for the same set of matches?
2. How many frames from a 10-minute highlight reel are actually tactically informative?
3. What does Polymarket actually offer for UCL? (If not, which platform does?)
4. What's the typical highlight clip length and resolution on YouTube?

---

## Day 2: Technical Feasibility & Architecture (6 hours)

### AMD / ROCm Setup Research (~1.5 hrs)

- Sign up for AMD AI Developer Program (get $100 credits)
- Explore AMD Developer Cloud dashboard — what instance types are available?
- Read: how to run Llama 3.2 Vision on ROCm (Hugging Face + vLLM compatibility)
- Understand GPU memory requirements: Llama 3.2 11B Vision needs ~24GB VRAM, 90B needs ~180GB (MI300X has 192GB — it fits)

### Technical Concepts to Research (~2 hrs)

**Video processing pipeline (45 min)**
- `opencv-python` for frame extraction from video
- Frame sampling: every N seconds vs. scene-change detection
- Image preprocessing for vision models (resolution, aspect ratio)

**Model serving on AMD (45 min)**
- vLLM on ROCm — does it support Llama 3.2 Vision? (check compatibility matrix)
- Alternative: Hugging Face `transformers` + `accelerate` on ROCm
- Batch inference: sending multiple frames in one pass

**Prompt engineering for sports video (30 min)**
- What questions do you ask the model per frame?
- Examples: "Describe the defensive formation", "How many players are behind the ball?", "Is the pressing intensity high or low?"
- How to structure output for downstream aggregation

### Architecture Sketch (~1 hr)

```
[YouTube highlights] → [Frame extraction] → [Frame selection/sampling]
                                                      ↓
[Stats API] → [Pre-match data] ──────────→ [Multimodal LLM on AMD GPU]
                                                      ↓
                                          [Match assessment / probability]
                                                      ↓
[Historical odds API] ──────────────────→ [Compare: our prob vs market prob]
                                                      ↓
                                          [Edge detection / signal output]
```

### Note: Fitness/Fatigue — Use Stats, Not Video

YouTube highlights can't show player fitness (they skip the moments where tired players jog back). Use public stats as fitness proxies instead:

- Minutes played in last 7/14/30 days (fixture congestion) — Transfermarkt
- Injury history and return timelines — Transfermarkt
- Pressing intensity dropoff (first half vs second half pressures) — FBref
- Squad rotation patterns — did the manager rest them midweek?
- Age + minutes workload combination

Fitness is a **stats-derived feature**, not a visual one. Video covers tactical shape; stats cover workload/fatigue.

### Feasibility Validation (~1 hr)

The make-or-break question: **Can a vision-language model extract anything tactically meaningful from match footage that isn't already captured in stats?**

- Find a UCL match frame, describe what you see, and ask: "does this tell me anything xG doesn't?"
- If the answer is "not really" — pivot to: multimodal = stats + text (news, press conferences, injury reports, social media). Still Track 3, still multimodal, just different modalities.

### Day 2 Checkpoints (~30 min)

1. Can Llama 3.2 Vision actually extract useful tactical info from a single match frame?
2. What's the simplest viable pipeline: how few components can you get away with?
3. Is vLLM on ROCm production-ready for vision models, or do you need a fallback?
4. What's your demo story? Pick 3-5 past UCL matches where market odds were "wrong" — those become your test cases.

---

## Accounts & Tools to Set Up (do alongside research, ~1 hr total)

- [ ] AMD AI Developer Program signup
- [ ] AMD Developer Cloud account + explore dashboard
- [ ] Polymarket account (or identify which platform has UCL markets)
- [ ] FBref — bookmark UCL match reports for 2024-25 season
- [ ] API-Football free tier API key
- [ ] YouTube Data API key (for programmatic highlight retrieval)

---

## Total Time Budget

| Block | Hours |
|-------|-------|
| Day 1: Concepts | 2.5 |
| Day 1: Data research | 2.5 |
| Day 1: Checkpoints & review | 1 |
| Day 2: AMD/ROCm setup | 1.5 |
| Day 2: Technical research | 2 |
| Day 2: Architecture & feasibility | 2 |
| Account setup (spread across both days) | 1 |
| **Total** | **12.5 hrs** |

---

## Go / No-Go Decision

At the end of Day 2, decide:

- **GO** if: You can get video + stats + odds for the same matches, AND the vision model extracts at least one insight that stats alone don't capture.
- **PIVOT** if: Video analysis adds nothing useful — switch modalities to stats + text (news/press conferences/social media sentiment) instead of video.
- **ABORT** if: AMD Developer Cloud / ROCm doesn't support your model stack — switch to Track 1 (Agents) as backup.
