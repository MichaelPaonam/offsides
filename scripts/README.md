# Highlights Download Scripts

## Setup

```bash
# From project root
source venv/bin/activate
```

## Step 1: Generate match list CSV

```bash
python scripts/generate_match_list.py
```

This creates `data/match_urls/ucl_highlights.csv` with all UCL fixtures (URLs blank).

**What's included:**
- 2023-24: Full season (96 group stage + 29 knockout = 125 matches)
- 2024-25: League phase (144 matches) + knockouts (44 matches)
- Total: **313 matches**

## Step 2: Auto-fill YouTube URLs

```bash
# Preview what will be searched (no changes made):
python scripts/autofill_urls.py --dry-run

# Run the auto-filler (leave it running — ~15-20 min at 3s delay):
python scripts/autofill_urls.py

# Resume from a specific row if interrupted:
python scripts/autofill_urls.py --start-row 150

# Adjust delay between searches (default 3s):
python scripts/autofill_urls.py --delay 5
```

The script:
- Searches YouTube via yt-dlp for each match with no URL
- Writes the top result back into the CSV
- Saves progress after each find (safe to interrupt and resume)
- Logs to `data/match_urls/autofill_log.txt`

**Time estimate:** 313 matches × 3s delay = ~16 minutes

## Step 3: Spot-check the CSV (~10 min)

Open `data/match_urls/ucl_highlights.csv` and verify:
- URLs point to actual highlights (not fan compilations, pre-match shows, etc.)
- Delete rows with wrong/missing videos
- The official UEFA Champions League channel uploads are preferred

## Step 4: Download highlights

```bash
python scripts/download_highlights.py
```

Leave it running. The script:
- Downloads at 720p (mp4)
- Skips already-downloaded videos (safe to re-run)
- Logs progress to `data/highlights/download_log.txt`
- Retries failed downloads 3 times
- Timeout: 10 minutes per video

## Storage Requirements

| Quality | Per clip (~10 min) | 100 matches | 200 matches | 313 matches |
|---------|-------------------|-------------|-------------|-------------|
| 720p | ~50-100 MB | ~8 GB | ~15 GB | ~20-25 GB |

**Recommended: Allocate 25 GB** for all highlights at 720p.

## Directory Structure After Download

```
data/
├── match_urls/
│   ├── ucl_highlights.csv      (fixture list with YouTube URLs)
│   └── autofill_log.txt        (URL search log)
└── highlights/
    ├── download_log.txt
    ├── 2023-24/
    │   ├── Group_A/
    │   ├── ...
    │   ├── Round_of_16/
    │   ├── Quarter-final/
    │   ├── Semi-final/
    │   └── Final/
    └── 2024-25/
        ├── League_Phase/
        ├── Knockout_Playoff/
        ├── Round_of_16/
        ├── Quarter-final/
        └── Semi-final/
```

## Troubleshooting

**"Video unavailable"** — UEFA sometimes removes highlights. Find an alternative upload and update the CSV URL.

**Slow downloads** — yt-dlp respects rate limits. Don't run multiple instances.

**Resume after interruption** — Just re-run the script. It skips videos already on disk.

**Auto-fill got wrong video** — Edit the CSV manually for that row, then re-run the downloader.
