# Offsides — Project Plan

UCL multimodal prediction market project on AMD GPUs (Track 3: Vision & Multimodal AI).

**Submission deadline: May 9, 2026**

---

## Timeline Overview

| Phase | Duration | Date | Key Deliverable |
|-------|----------|------|-----------------|
| Research | 1 day | May 4 (today) | Go/No-Go decision |
| Design + Test First | 1 day | May 5 | Architecture + test skeleton |
| Develop | 2 days | May 6–7 | Working pipeline end-to-end |
| UAT + Polish | 0.5 day | May 8 (morning) | Validated against known matches |
| Deployment + Submission | 0.5 day | May 8 (afternoon)–May 9 | Deployed, video recorded, submitted |

**Total: 5 days**

---

## Phase 1: Research (May 4 — today)

See `research-plan.md` for detailed breakdown. Compressed to 1 day — focus on essentials only.

### Milestones

- [ ] M1.1 — Data sources validated (StatsBomb, FBref, odds APIs confirmed accessible)
- [ ] M1.2 — AMD Developer Cloud account active
- [ ] M1.3 — Llama 3.2 Vision feasibility confirmed (can it extract tactical info from frames?)
- [ ] M1.4 — Go/No-Go decision made

### Checkpoint (End of May 4)

**Gate criteria:**
- Can we get video + stats + historical odds for the same matches? → YES/NO
- Does the vision model add signal beyond stats alone? → YES/NO
- Is our model stack compatible with ROCm? → YES/NO

If any answer is NO, pivot or abort (see research-plan.md for pivot options).

---

## Phase 2: Design + Test First (May 5)

### Milestones

- [ ] M2.1 — System architecture finalized (keep it minimal)
- [ ] M2.2 — Data schemas defined (what a "match" looks like in our system)
- [ ] M2.3 — Prompt templates for vision model drafted
- [ ] M2.4 — Tech stack locked (Python version, key libraries, model size)
- [ ] M2.5 — Test framework set up (pytest)
- [ ] M2.6 — Key tests written: data ingestion, frame extraction, end-to-end pipeline
- [ ] M2.7 — Test fixtures prepared: sample stats, sample frames, sample odds for 3 matches

### Deliverables

- Architecture diagram (components + data flow)
- Prompt templates for vision model
- Test suite with failing tests that define expected behavior
- 3 target demo matches identified (UCL matches where outcome surprised the market)

### Checkpoint (End of May 5)

**Gate criteria:**
- Is the architecture simple enough to build in 2 days?
- Do we have test fixtures for at least 3 historical matches?
- Is the demo story clear?

---

## Phase 3: Develop (May 6–7)

### Milestones

- [ ] M3.1 — Data ingestion pipeline working (stats + odds fetched and normalized)
- [ ] M3.2 — Video/frame extraction pipeline working (YouTube → frames)
- [ ] M3.3 — Vision model inference working on AMD GPU (frames → tactical descriptions)
- [ ] M3.4 — Aggregation logic working (frame insights + stats → match probability)
- [ ] M3.5 — Comparison engine working (our probability vs market odds → edge signal)
- [ ] M3.6 — End-to-end pipeline passing for at least 1 match

### Daily Goals

| Day | Focus | Target |
|-----|-------|--------|
| May 6 | Data + frames | Fetch stats/odds for 3-5 matches, extract frames from highlights |
| May 7 | Model + integration | Run vision model on AMD GPU, build aggregation, wire end-to-end |

### Checkpoint (End of May 7)

**Gate criteria:**
- Can we run the full pipeline for at least 3 matches end-to-end?
- Does the output make intuitive sense?
- Are critical tests passing?

---

## Phase 4: UAT + Polish (May 8 morning — 4 hrs)

### Milestones

- [ ] M4.1 — Run pipeline against 5+ historical UCL matches with known outcomes
- [ ] M4.2 — Validate: at least 2 matches where system correctly flagged mispricing
- [ ] M4.3 — Edge cases tested (missing data, low-quality frames)
- [ ] M4.4 — Demo script written (narrative walkthrough of 2-3 compelling examples)
- [ ] M4.5 — Performance benchmarks noted (inference time per match on AMD GPU)

### Checkpoint (End of morning May 8)

- Does the demo tell a compelling story?
- Is the system stable enough to show?

---

## Phase 5: Deployment + Submission (May 8 afternoon – May 9)

### Milestones

- [ ] M5.1 — Application deployed on AMD Developer Cloud
- [ ] M5.2 — README written (problem statement, architecture, how to run, results)
- [ ] M5.3 — Demo video recorded (3-5 minutes)
- [ ] M5.4 — Submission package assembled per hackathon guidelines
- [ ] M5.5 — Submitted on lablab.ai before deadline

### Submission Checklist

- [ ] Working demo (live or recorded)
- [ ] Source code (GitHub repo)
- [ ] README with: problem statement, architecture, how to run, results
- [ ] Demo video (required by lablab.ai)
- [ ] Team info

### Checkpoint (May 9 — Submission)

- [ ] Everything submitted before deadline
- [ ] Demo video plays correctly
- [ ] Repo is clean and documented

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Llama 3.2 Vision can't extract tactical info from frames | High | Pivot: use stats + text (news/pressers) as multimodal input instead of video |
| StatsBomb doesn't cover recent UCL | Medium | Fall back to FBref + API-Football; use StatsBomb for other comps during prototyping |
| vLLM doesn't support vision models on ROCm | High | Fall back to Hugging Face transformers + accelerate |
| $100 AMD credits run out during development | Medium | Develop/test locally where possible; use cloud only for GPU inference |
| No prediction market covers UCL specifically | Low | Use historical betting odds from Odds-portal as proxy |
| Highlight clips too short for meaningful analysis | Medium | Supplement with more frames per clip + lean heavier on stats |

---

## Success Criteria

**Minimum viable demo:**
- Pipeline processes at least 3 UCL matches end-to-end
- Shows at least 1 clear example where multimodal signal identified market mispricing
- Runs on AMD GPU infrastructure
- CLI interface: user inputs a match, gets probability vs market odds + edge detection

**Stretch goals:**
- Streamlit web dashboard (match selector, visual results, annotated frames)
- Real-time mode: feed upcoming match data → output probability before kickoff
- Backtested against full UCL 2024-25 season
