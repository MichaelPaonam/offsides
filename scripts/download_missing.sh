#!/bin/bash
# Download 32 missing 2024-25 UCL highlights
# Phase 1: yt-dlp for 8 matches with unique YouTube URLs
# Phase 2: UEFA API for 24 matches with duplicate/missing URLs

echo "=== Phase 1: YouTube downloads (8 unique URLs) ==="
echo ""

echo "[1/8] Shakhtar_Donetsk_vs_Man_City_2024-11-06"
yt-dlp -f "best[height<=720]" --no-playlist -o "data/highlights/2024-25/League_Phase/Shakhtar_Donetsk_vs_Man_City_2024-11-06.mp4" "https://www.youtube.com/watch?v=YUxHXnLKjzU" || echo "  FAILED"

echo "[2/8] Red_Star_Belgrade_vs_Young_Boys_2024-12-11"
yt-dlp -f "best[height<=720]" --no-playlist -o "data/highlights/2024-25/League_Phase/Red_Star_Belgrade_vs_Young_Boys_2024-12-11.mp4" "https://www.youtube.com/watch?v=vwVWkNeqBtE" || echo "  FAILED"

echo "[3/8] AC_Milan_vs_Bayern_Munich_2024-12-11"
yt-dlp -f "best[height<=720]" --no-playlist -o "data/highlights/2024-25/League_Phase/AC_Milan_vs_Bayern_Munich_2024-12-11.mp4" "https://www.youtube.com/watch?v=S_B2qOFc-1U" || echo "  FAILED"

echo "[4/8] AC_Milan_vs_Inter_Milan_2025-03-05"
yt-dlp -f "best[height<=720]" --no-playlist -o "data/highlights/2024-25/Round_of_16/AC_Milan_vs_Inter_Milan_2025-03-05.mp4" "https://www.youtube.com/watch?v=Jij75iUvDig" || echo "  FAILED"

echo "[5/8] Bayern_Munich_vs_Benfica_2025-03-05"
yt-dlp -f "best[height<=720]" --no-playlist -o "data/highlights/2024-25/Round_of_16/Bayern_Munich_vs_Benfica_2025-03-05.mp4" "https://www.youtube.com/watch?v=u4JVV8-mj7E" || echo "  FAILED"

echo "[6/8] Benfica_vs_Bayern_Munich_2025-03-12"
yt-dlp -f "best[height<=720]" --no-playlist -o "data/highlights/2024-25/Round_of_16/Benfica_vs_Bayern_Munich_2025-03-12.mp4" "https://www.youtube.com/watch?v=tALyzOvpD70" || echo "  FAILED"

echo "[7/8] Bayern_Munich_vs_Inter_Milan_2025-04-15"
yt-dlp -f "best[height<=720]" --no-playlist -o "data/highlights/2024-25/Quarter-final/Bayern_Munich_vs_Inter_Milan_2025-04-15.mp4" "https://www.youtube.com/watch?v=79xxN25DIxw" || echo "  FAILED"

echo "[8/8] Inter_Milan_vs_Atletico_Madrid_2025-04-30"
yt-dlp -f "best[height<=720]" --no-playlist -o "data/highlights/2024-25/Semi-final/Inter_Milan_vs_Atletico_Madrid_2025-04-30.mp4" "https://www.youtube.com/watch?v=nuyuCSRx8sI" || echo "  FAILED"

echo ""
echo "=== Phase 2: UEFA API downloads (24 matches with duplicate/missing YouTube URLs) ==="
echo "These need per-match highlights from UEFA's CDN."
echo ""

python3 scripts/download_uefa_highlights.py --all --delay 8

echo ""
echo "=== Done ==="
echo "Next steps:"
echo "  1. python3 scripts/extract_frames.py   (extract keyframes + sequences)"
echo "  2. Upload to GPU droplet for YOLO detection"
echo "  3. python3 scripts/annotate_frames.py   (team colors + metrics)"
