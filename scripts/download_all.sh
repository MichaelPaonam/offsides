#!/bin/bash
# Download all UCL highlights from UEFA.com in batches of 30.
# Sequential with conservative delays to avoid rate limits.
# Safe to interrupt and re-run — skips already-downloaded files.
#
# Total: ~277 videos, ~10 batches, ~3-4 hours unattended.

set -e

BATCH=1

while true; do
    echo "=========================================="
    echo "Batch $BATCH — $(date)"
    echo "=========================================="

    python3 scripts/download_uefa_highlights.py --all --limit 30 --delay 15

    # Check if there's anything left to download
    if grep -q "Downloaded: 0" data/highlights/uefa_download_log.txt 2>/dev/null; then
        echo "No more videos to download. Done!"
        break
    fi

    BATCH=$((BATCH + 1))
    echo "Sleeping 2 minutes before next batch..."
    sleep 120
done

echo "=========================================="
echo "All batches complete. Building manifest..."
echo "=========================================="
python3 scripts/build_manifest.py
