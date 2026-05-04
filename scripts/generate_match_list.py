#!/usr/bin/env python3
"""
Offsides — Generate UCL match fixture list as CSV

Generates a CSV template with all UEFA Champions League matches
for specified seasons. YouTube URLs are left blank for manual curation.

Usage:
    source venv/bin/activate
    python scripts/generate_match_list.py

Output:
    data/match_urls/ucl_highlights.csv

After running, fill in the youtube_url column manually by searching
for each match on YouTube (UEFA official channel or verified uploaders).
"""

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "match_urls" / "ucl_highlights.csv"

# UCL 2023-24 fixtures (Group Stage → Final)
# Source: UEFA.com official results
UCL_2023_24 = [
    # Group A
    ("2023-24", "Group A", "MD1", "Bayern Munich", "Manchester United", "2023-09-20"),
    ("2023-24", "Group A", "MD1", "FC Copenhagen", "Galatasaray", "2023-09-19"),
    ("2023-24", "Group A", "MD2", "Galatasaray", "Bayern Munich", "2023-10-03"),
    ("2023-24", "Group A", "MD2", "Manchester United", "FC Copenhagen", "2023-10-03"),
    ("2023-24", "Group A", "MD3", "Manchester United", "Galatasaray", "2023-10-24"),
    ("2023-24", "Group A", "MD3", "FC Copenhagen", "Bayern Munich", "2023-10-25"),
    ("2023-24", "Group A", "MD4", "Galatasaray", "Manchester United", "2023-11-07"),
    ("2023-24", "Group A", "MD4", "Bayern Munich", "FC Copenhagen", "2023-11-08"),
    ("2023-24", "Group A", "MD5", "FC Copenhagen", "Manchester United", "2023-12-13"),
    ("2023-24", "Group A", "MD5", "Galatasaray", "FC Copenhagen", "2023-12-12"),
    ("2023-24", "Group A", "MD6", "Manchester United", "Bayern Munich", "2023-12-12"),
    ("2023-24", "Group A", "MD6", "Bayern Munich", "Galatasaray", "2023-12-13"),

    # Group B
    ("2023-24", "Group B", "MD1", "Sevilla", "Lens", "2023-09-20"),
    ("2023-24", "Group B", "MD1", "PSV", "Arsenal", "2023-09-20"),
    ("2023-24", "Group B", "MD2", "Arsenal", "Sevilla", "2023-10-03"),
    ("2023-24", "Group B", "MD2", "Lens", "PSV", "2023-10-04"),
    ("2023-24", "Group B", "MD3", "Sevilla", "PSV", "2023-10-24"),
    ("2023-24", "Group B", "MD3", "Lens", "Arsenal", "2023-10-24"),
    ("2023-24", "Group B", "MD4", "PSV", "Sevilla", "2023-11-08"),
    ("2023-24", "Group B", "MD4", "Arsenal", "Lens", "2023-11-07"),
    ("2023-24", "Group B", "MD5", "Lens", "Sevilla", "2023-12-13"),
    ("2023-24", "Group B", "MD5", "Arsenal", "PSV", "2023-12-12"),
    ("2023-24", "Group B", "MD6", "Sevilla", "Arsenal", "2023-12-13"),
    ("2023-24", "Group B", "MD6", "PSV", "Lens", "2023-12-12"),

    # Group C
    ("2023-24", "Group C", "MD1", "Real Madrid", "Union Berlin", "2023-09-20"),
    ("2023-24", "Group C", "MD1", "Braga", "Napoli", "2023-09-20"),
    ("2023-24", "Group C", "MD2", "Napoli", "Real Madrid", "2023-10-03"),
    ("2023-24", "Group C", "MD2", "Union Berlin", "Braga", "2023-10-04"),
    ("2023-24", "Group C", "MD3", "Braga", "Real Madrid", "2023-10-24"),
    ("2023-24", "Group C", "MD3", "Napoli", "Union Berlin", "2023-10-24"),
    ("2023-24", "Group C", "MD4", "Real Madrid", "Braga", "2023-11-08"),
    ("2023-24", "Group C", "MD4", "Union Berlin", "Napoli", "2023-11-07"),
    ("2023-24", "Group C", "MD5", "Real Madrid", "Napoli", "2023-11-29"),
    ("2023-24", "Group C", "MD5", "Braga", "Union Berlin", "2023-11-29"),
    ("2023-24", "Group C", "MD6", "Napoli", "Braga", "2023-12-12"),
    ("2023-24", "Group C", "MD6", "Union Berlin", "Real Madrid", "2023-12-12"),

    # Group D
    ("2023-24", "Group D", "MD1", "Real Sociedad", "Inter Milan", "2023-09-20"),
    ("2023-24", "Group D", "MD1", "Salzburg", "Benfica", "2023-09-20"),
    ("2023-24", "Group D", "MD2", "Benfica", "Real Sociedad", "2023-10-03"),
    ("2023-24", "Group D", "MD2", "Inter Milan", "Salzburg", "2023-10-04"),
    ("2023-24", "Group D", "MD3", "Real Sociedad", "Salzburg", "2023-10-24"),
    ("2023-24", "Group D", "MD3", "Inter Milan", "Benfica", "2023-10-24"),
    ("2023-24", "Group D", "MD4", "Salzburg", "Real Sociedad", "2023-11-08"),
    ("2023-24", "Group D", "MD4", "Benfica", "Inter Milan", "2023-11-07"),
    ("2023-24", "Group D", "MD5", "Inter Milan", "Real Sociedad", "2023-12-12"),
    ("2023-24", "Group D", "MD5", "Benfica", "Salzburg", "2023-12-12"),
    ("2023-24", "Group D", "MD6", "Real Sociedad", "Benfica", "2023-12-13"),
    ("2023-24", "Group D", "MD6", "Salzburg", "Inter Milan", "2023-12-13"),

    # Group E
    ("2023-24", "Group E", "MD1", "Feyenoord", "Celtic", "2023-09-19"),
    ("2023-24", "Group E", "MD1", "Lazio", "Atletico Madrid", "2023-09-19"),
    ("2023-24", "Group E", "MD2", "Atletico Madrid", "Feyenoord", "2023-10-04"),
    ("2023-24", "Group E", "MD2", "Celtic", "Lazio", "2023-10-04"),
    ("2023-24", "Group E", "MD3", "Feyenoord", "Lazio", "2023-10-25"),
    ("2023-24", "Group E", "MD3", "Atletico Madrid", "Celtic", "2023-10-25"),
    ("2023-24", "Group E", "MD4", "Lazio", "Feyenoord", "2023-11-07"),
    ("2023-24", "Group E", "MD4", "Celtic", "Atletico Madrid", "2023-11-07"),
    ("2023-24", "Group E", "MD5", "Feyenoord", "Atletico Madrid", "2023-12-12"),
    ("2023-24", "Group E", "MD5", "Lazio", "Celtic", "2023-12-12"),
    ("2023-24", "Group E", "MD6", "Atletico Madrid", "Lazio", "2023-12-13"),
    ("2023-24", "Group E", "MD6", "Celtic", "Feyenoord", "2023-12-13"),

    # Group F
    ("2023-24", "Group F", "MD1", "AC Milan", "Newcastle", "2023-09-19"),
    ("2023-24", "Group F", "MD1", "PSG", "Dortmund", "2023-09-19"),
    ("2023-24", "Group F", "MD2", "Dortmund", "AC Milan", "2023-10-04"),
    ("2023-24", "Group F", "MD2", "Newcastle", "PSG", "2023-10-04"),
    ("2023-24", "Group F", "MD3", "PSG", "AC Milan", "2023-10-25"),
    ("2023-24", "Group F", "MD3", "Newcastle", "Dortmund", "2023-10-25"),
    ("2023-24", "Group F", "MD4", "AC Milan", "PSG", "2023-11-07"),
    ("2023-24", "Group F", "MD4", "Dortmund", "Newcastle", "2023-11-07"),
    ("2023-24", "Group F", "MD5", "AC Milan", "Dortmund", "2023-11-28"),
    ("2023-24", "Group F", "MD5", "PSG", "Newcastle", "2023-11-28"),
    ("2023-24", "Group F", "MD6", "Dortmund", "PSG", "2023-12-13"),
    ("2023-24", "Group F", "MD6", "Newcastle", "AC Milan", "2023-12-13"),

    # Group G
    ("2023-24", "Group G", "MD1", "Man City", "Crvena Zvezda", "2023-09-19"),
    ("2023-24", "Group G", "MD1", "RB Leipzig", "Young Boys", "2023-09-19"),
    ("2023-24", "Group G", "MD2", "Young Boys", "Man City", "2023-10-03"),
    ("2023-24", "Group G", "MD2", "Crvena Zvezda", "RB Leipzig", "2023-10-03"),
    ("2023-24", "Group G", "MD3", "Man City", "Young Boys", "2023-10-25"),
    ("2023-24", "Group G", "MD3", "RB Leipzig", "Crvena Zvezda", "2023-10-25"),
    ("2023-24", "Group G", "MD4", "Young Boys", "RB Leipzig", "2023-11-07"),
    ("2023-24", "Group G", "MD4", "Crvena Zvezda", "Man City", "2023-11-07"),
    ("2023-24", "Group G", "MD5", "Man City", "RB Leipzig", "2023-11-28"),
    ("2023-24", "Group G", "MD5", "Crvena Zvezda", "Young Boys", "2023-11-28"),
    ("2023-24", "Group G", "MD6", "RB Leipzig", "Man City", "2023-12-13"),
    ("2023-24", "Group G", "MD6", "Young Boys", "Crvena Zvezda", "2023-12-13"),

    # Group H
    ("2023-24", "Group H", "MD1", "Barcelona", "Antwerp", "2023-09-19"),
    ("2023-24", "Group H", "MD1", "Shakhtar Donetsk", "Porto", "2023-09-19"),
    ("2023-24", "Group H", "MD2", "Porto", "Barcelona", "2023-10-04"),
    ("2023-24", "Group H", "MD2", "Antwerp", "Shakhtar Donetsk", "2023-10-04"),
    ("2023-24", "Group H", "MD3", "Barcelona", "Shakhtar Donetsk", "2023-10-25"),
    ("2023-24", "Group H", "MD3", "Porto", "Antwerp", "2023-10-25"),
    ("2023-24", "Group H", "MD4", "Shakhtar Donetsk", "Barcelona", "2023-11-07"),
    ("2023-24", "Group H", "MD4", "Antwerp", "Porto", "2023-11-07"),
    ("2023-24", "Group H", "MD5", "Barcelona", "Porto", "2023-11-28"),
    ("2023-24", "Group H", "MD5", "Shakhtar Donetsk", "Antwerp", "2023-11-28"),
    ("2023-24", "Group H", "MD6", "Porto", "Shakhtar Donetsk", "2023-12-13"),
    ("2023-24", "Group H", "MD6", "Antwerp", "Barcelona", "2023-12-13"),

    # Knockout Round (Ro16)
    ("2023-24", "Round of 16", "Leg 1", "Porto", "Arsenal", "2024-02-21"),
    ("2023-24", "Round of 16", "Leg 1", "Napoli", "Barcelona", "2024-02-21"),
    ("2023-24", "Round of 16", "Leg 1", "PSG", "Real Sociedad", "2024-02-14"),
    ("2023-24", "Round of 16", "Leg 1", "Inter Milan", "Atletico Madrid", "2024-02-20"),
    ("2023-24", "Round of 16", "Leg 1", "PSV", "Dortmund", "2024-02-20"),
    ("2023-24", "Round of 16", "Leg 1", "Lazio", "Bayern Munich", "2024-02-14"),
    ("2023-24", "Round of 16", "Leg 1", "FC Copenhagen", "Man City", "2024-02-13"),
    ("2023-24", "Round of 16", "Leg 1", "RB Leipzig", "Real Madrid", "2024-02-13"),
    ("2023-24", "Round of 16", "Leg 2", "Arsenal", "Porto", "2024-03-12"),
    ("2023-24", "Round of 16", "Leg 2", "Barcelona", "Napoli", "2024-03-12"),
    ("2023-24", "Round of 16", "Leg 2", "Real Sociedad", "PSG", "2024-03-05"),
    ("2023-24", "Round of 16", "Leg 2", "Atletico Madrid", "Inter Milan", "2024-03-13"),
    ("2023-24", "Round of 16", "Leg 2", "Dortmund", "PSV", "2024-03-13"),
    ("2023-24", "Round of 16", "Leg 2", "Bayern Munich", "Lazio", "2024-03-05"),
    ("2023-24", "Round of 16", "Leg 2", "Man City", "FC Copenhagen", "2024-03-06"),
    ("2023-24", "Round of 16", "Leg 2", "Real Madrid", "RB Leipzig", "2024-03-06"),

    # Quarter-finals
    ("2023-24", "Quarter-final", "Leg 1", "Arsenal", "Bayern Munich", "2024-04-09"),
    ("2023-24", "Quarter-final", "Leg 1", "Real Madrid", "Man City", "2024-04-09"),
    ("2023-24", "Quarter-final", "Leg 1", "Atletico Madrid", "Dortmund", "2024-04-10"),
    ("2023-24", "Quarter-final", "Leg 1", "Barcelona", "PSG", "2024-04-10"),
    ("2023-24", "Quarter-final", "Leg 2", "Bayern Munich", "Arsenal", "2024-04-17"),
    ("2023-24", "Quarter-final", "Leg 2", "Man City", "Real Madrid", "2024-04-17"),
    ("2023-24", "Quarter-final", "Leg 2", "Dortmund", "Atletico Madrid", "2024-04-16"),
    ("2023-24", "Quarter-final", "Leg 2", "PSG", "Barcelona", "2024-04-16"),

    # Semi-finals
    ("2023-24", "Semi-final", "Leg 1", "Bayern Munich", "Real Madrid", "2024-04-30"),
    ("2023-24", "Semi-final", "Leg 1", "PSG", "Dortmund", "2024-05-01"),
    ("2023-24", "Semi-final", "Leg 2", "Real Madrid", "Bayern Munich", "2024-05-08"),
    ("2023-24", "Semi-final", "Leg 2", "Dortmund", "PSG", "2024-05-07"),

    # Final
    ("2023-24", "Final", "Final", "Dortmund", "Real Madrid", "2024-06-01"),
]

# UCL 2024-25 uses new Swiss-model league phase (36 teams, 8 matches each)
# League phase: 144 matches across 8 matchdays (Sep 2024 - Jan 2025)
UCL_2024_25_LEAGUE = [
    # Matchday 1 (Sep 17-19, 2024)
    ("2024-25", "League Phase", "MD1", "Juventus", "PSV", "2024-09-17"),
    ("2024-25", "League Phase", "MD1", "Young Boys", "Aston Villa", "2024-09-17"),
    ("2024-25", "League Phase", "MD1", "Bayern Munich", "Dinamo Zagreb", "2024-09-17"),
    ("2024-25", "League Phase", "MD1", "Real Madrid", "Stuttgart", "2024-09-17"),
    ("2024-25", "League Phase", "MD1", "Sporting CP", "Lille", "2024-09-17"),
    ("2024-25", "League Phase", "MD1", "AC Milan", "Liverpool", "2024-09-17"),
    ("2024-25", "League Phase", "MD1", "Celtic", "Slovan Bratislava", "2024-09-18"),
    ("2024-25", "League Phase", "MD1", "Club Brugge", "Dortmund", "2024-09-18"),
    ("2024-25", "League Phase", "MD1", "Man City", "Inter Milan", "2024-09-18"),
    ("2024-25", "League Phase", "MD1", "PSG", "Girona", "2024-09-18"),
    ("2024-25", "League Phase", "MD1", "Feyenoord", "Bayer Leverkusen", "2024-09-19"),
    ("2024-25", "League Phase", "MD1", "Red Star Belgrade", "Benfica", "2024-09-19"),
    ("2024-25", "League Phase", "MD1", "Monaco", "Barcelona", "2024-09-19"),
    ("2024-25", "League Phase", "MD1", "Atalanta", "Arsenal", "2024-09-19"),
    ("2024-25", "League Phase", "MD1", "Atletico Madrid", "RB Leipzig", "2024-09-19"),
    ("2024-25", "League Phase", "MD1", "Brest", "Sturm Graz", "2024-09-19"),
    ("2024-25", "League Phase", "MD1", "Shakhtar Donetsk", "Bologna", "2024-09-18"),
    ("2024-25", "League Phase", "MD1", "Sparta Prague", "Salzburg", "2024-09-18"),

    # Matchday 2 (Oct 1-2, 2024)
    ("2024-25", "League Phase", "MD2", "Arsenal", "PSG", "2024-10-01"),
    ("2024-25", "League Phase", "MD2", "Bayer Leverkusen", "AC Milan", "2024-10-01"),
    ("2024-25", "League Phase", "MD2", "Dortmund", "Celtic", "2024-10-01"),
    ("2024-25", "League Phase", "MD2", "Barcelona", "Young Boys", "2024-10-01"),
    ("2024-25", "League Phase", "MD2", "Inter Milan", "Red Star Belgrade", "2024-10-01"),
    ("2024-25", "League Phase", "MD2", "Liverpool", "Bologna", "2024-10-02"),
    ("2024-25", "League Phase", "MD2", "PSV", "Sporting CP", "2024-10-01"),
    ("2024-25", "League Phase", "MD2", "Slovan Bratislava", "Man City", "2024-10-01"),
    ("2024-25", "League Phase", "MD2", "Salzburg", "Brest", "2024-10-01"),
    ("2024-25", "League Phase", "MD2", "Stuttgart", "Sparta Prague", "2024-10-01"),
    ("2024-25", "League Phase", "MD2", "Benfica", "Atletico Madrid", "2024-10-02"),
    ("2024-25", "League Phase", "MD2", "Dinamo Zagreb", "Monaco", "2024-10-02"),
    ("2024-25", "League Phase", "MD2", "Girona", "Feyenoord", "2024-10-02"),
    ("2024-25", "League Phase", "MD2", "Aston Villa", "Bayern Munich", "2024-10-02"),
    ("2024-25", "League Phase", "MD2", "Lille", "Real Madrid", "2024-10-02"),
    ("2024-25", "League Phase", "MD2", "RB Leipzig", "Juventus", "2024-10-02"),
    ("2024-25", "League Phase", "MD2", "Sturm Graz", "Club Brugge", "2024-10-01"),
    ("2024-25", "League Phase", "MD2", "Shakhtar Donetsk", "Atalanta", "2024-10-02"),

    # Matchday 3 (Oct 22-23, 2024)
    ("2024-25", "League Phase", "MD3", "Atalanta", "Celtic", "2024-10-23"),
    ("2024-25", "League Phase", "MD3", "Brest", "Bayer Leverkusen", "2024-10-23"),
    ("2024-25", "League Phase", "MD3", "Red Star Belgrade", "Barcelona", "2024-10-23"),
    ("2024-25", "League Phase", "MD3", "Man City", "Sparta Prague", "2024-10-23"),
    ("2024-25", "League Phase", "MD3", "Juventus", "Stuttgart", "2024-10-22"),
    ("2024-25", "League Phase", "MD3", "Arsenal", "Shakhtar Donetsk", "2024-10-22"),
    ("2024-25", "League Phase", "MD3", "Aston Villa", "Bologna", "2024-10-22"),
    ("2024-25", "League Phase", "MD3", "Girona", "Slovan Bratislava", "2024-10-22"),
    ("2024-25", "League Phase", "MD3", "Bayern Munich", "Benfica", "2024-10-22"),
    ("2024-25", "League Phase", "MD3", "AC Milan", "Club Brugge", "2024-10-22"),
    ("2024-25", "League Phase", "MD3", "PSG", "PSV", "2024-10-22"),
    ("2024-25", "League Phase", "MD3", "Real Madrid", "Dortmund", "2024-10-22"),
    ("2024-25", "League Phase", "MD3", "Atletico Madrid", "Lille", "2024-10-23"),
    ("2024-25", "League Phase", "MD3", "RB Leipzig", "Liverpool", "2024-10-23"),
    ("2024-25", "League Phase", "MD3", "Salzburg", "Dinamo Zagreb", "2024-10-23"),
    ("2024-25", "League Phase", "MD3", "Sporting CP", "Sturm Graz", "2024-10-23"),
    ("2024-25", "League Phase", "MD3", "Monaco", "Red Star Belgrade", "2024-10-22"),
    ("2024-25", "League Phase", "MD3", "Feyenoord", "Young Boys", "2024-10-23"),

    # Matchday 4 (Nov 5-6, 2024)
    ("2024-25", "League Phase", "MD4", "Barcelona", "Brest", "2024-11-06"),
    ("2024-25", "League Phase", "MD4", "Dortmund", "Sturm Graz", "2024-11-05"),
    ("2024-25", "League Phase", "MD4", "Inter Milan", "Arsenal", "2024-11-06"),
    ("2024-25", "League Phase", "MD4", "Liverpool", "Bayer Leverkusen", "2024-11-05"),
    ("2024-25", "League Phase", "MD4", "PSV", "Girona", "2024-11-05"),
    ("2024-25", "League Phase", "MD4", "Young Boys", "Atalanta", "2024-11-06"),
    ("2024-25", "League Phase", "MD4", "Benfica", "Feyenoord", "2024-11-06"),
    ("2024-25", "League Phase", "MD4", "Bologna", "Monaco", "2024-11-05"),
    ("2024-25", "League Phase", "MD4", "Celtic", "RB Leipzig", "2024-11-05"),
    ("2024-25", "League Phase", "MD4", "Club Brugge", "Aston Villa", "2024-11-06"),
    ("2024-25", "League Phase", "MD4", "Dinamo Zagreb", "Slovan Bratislava", "2024-11-05"),
    ("2024-25", "League Phase", "MD4", "Lille", "Juventus", "2024-11-05"),
    ("2024-25", "League Phase", "MD4", "Real Madrid", "AC Milan", "2024-11-05"),
    ("2024-25", "League Phase", "MD4", "Salzburg", "Sporting CP", "2024-11-06"),
    ("2024-25", "League Phase", "MD4", "Sparta Prague", "Atletico Madrid", "2024-11-06"),
    ("2024-25", "League Phase", "MD4", "Stuttgart", "Red Star Belgrade", "2024-11-06"),
    ("2024-25", "League Phase", "MD4", "Shakhtar Donetsk", "Man City", "2024-11-06"),
    ("2024-25", "League Phase", "MD4", "PSG", "Bayern Munich", "2024-11-06"),

    # Matchday 5 (Nov 26-27, 2024)
    ("2024-25", "League Phase", "MD5", "Brest", "Barcelona", "2024-11-26"),
    ("2024-25", "League Phase", "MD5", "Bayer Leverkusen", "Salzburg", "2024-11-26"),
    ("2024-25", "League Phase", "MD5", "Red Star Belgrade", "Stuttgart", "2024-11-27"),
    ("2024-25", "League Phase", "MD5", "Inter Milan", "RB Leipzig", "2024-11-26"),
    ("2024-25", "League Phase", "MD5", "Sporting CP", "Arsenal", "2024-11-26"),
    ("2024-25", "League Phase", "MD5", "Young Boys", "Atalanta", "2024-11-26"),
    ("2024-25", "League Phase", "MD5", "Bayern Munich", "PSG", "2024-11-26"),
    ("2024-25", "League Phase", "MD5", "Sparta Prague", "Atletico Madrid", "2024-11-26"),
    ("2024-25", "League Phase", "MD5", "Man City", "Feyenoord", "2024-11-26"),
    ("2024-25", "League Phase", "MD5", "Juventus", "Man City", "2024-11-27"),
    ("2024-25", "League Phase", "MD5", "Liverpool", "Real Madrid", "2024-11-27"),
    ("2024-25", "League Phase", "MD5", "Dinamo Zagreb", "Dortmund", "2024-11-27"),
    ("2024-25", "League Phase", "MD5", "AC Milan", "Slovan Bratislava", "2024-11-26"),
    ("2024-25", "League Phase", "MD5", "Celtic", "Club Brugge", "2024-11-27"),
    ("2024-25", "League Phase", "MD5", "Bologna", "Lille", "2024-11-27"),
    ("2024-25", "League Phase", "MD5", "PSV", "Shakhtar Donetsk", "2024-11-27"),
    ("2024-25", "League Phase", "MD5", "Sturm Graz", "Girona", "2024-11-27"),
    ("2024-25", "League Phase", "MD5", "Monaco", "Benfica", "2024-11-27"),

    # Matchday 6 (Dec 10-11, 2024)
    ("2024-25", "League Phase", "MD6", "Atletico Madrid", "Slovan Bratislava", "2024-12-11"),
    ("2024-25", "League Phase", "MD6", "Bayer Leverkusen", "Inter Milan", "2024-12-10"),
    ("2024-25", "League Phase", "MD6", "Club Brugge", "Sporting CP", "2024-12-11"),
    ("2024-25", "League Phase", "MD6", "RB Leipzig", "Aston Villa", "2024-12-10"),
    ("2024-25", "League Phase", "MD6", "Liverpool", "Girona", "2024-12-10"),
    ("2024-25", "League Phase", "MD6", "Salzburg", "PSG", "2024-12-10"),
    ("2024-25", "League Phase", "MD6", "Atalanta", "Real Madrid", "2024-12-10"),
    ("2024-25", "League Phase", "MD6", "Brest", "PSV", "2024-12-10"),
    ("2024-25", "League Phase", "MD6", "Dortmund", "Barcelona", "2024-12-11"),
    ("2024-25", "League Phase", "MD6", "Feyenoord", "Sparta Prague", "2024-12-11"),
    ("2024-25", "League Phase", "MD6", "Juventus", "Man City", "2024-12-11"),
    ("2024-25", "League Phase", "MD6", "Benfica", "Bologna", "2024-12-11"),
    ("2024-25", "League Phase", "MD6", "Red Star Belgrade", "Young Boys", "2024-12-11"),
    ("2024-25", "League Phase", "MD6", "Dinamo Zagreb", "Celtic", "2024-12-10"),
    ("2024-25", "League Phase", "MD6", "Monaco", "Arsenal", "2024-12-10"),
    ("2024-25", "League Phase", "MD6", "Stuttgart", "Shakhtar Donetsk", "2024-12-10"),
    ("2024-25", "League Phase", "MD6", "Sturm Graz", "Lille", "2024-12-11"),
    ("2024-25", "League Phase", "MD6", "AC Milan", "Bayern Munich", "2024-12-11"),

    # Matchday 7 (Jan 21-22, 2025)
    ("2024-25", "League Phase", "MD7", "Atalanta", "Sturm Graz", "2025-01-21"),
    ("2024-25", "League Phase", "MD7", "Atletico Madrid", "Bayer Leverkusen", "2025-01-21"),
    ("2024-25", "League Phase", "MD7", "Bologna", "Dortmund", "2025-01-21"),
    ("2024-25", "League Phase", "MD7", "Club Brugge", "Juventus", "2025-01-21"),
    ("2024-25", "League Phase", "MD7", "Liverpool", "Lille", "2025-01-21"),
    ("2024-25", "League Phase", "MD7", "Monaco", "Aston Villa", "2025-01-21"),
    ("2024-25", "League Phase", "MD7", "PSV", "Red Star Belgrade", "2025-01-21"),
    ("2024-25", "League Phase", "MD7", "Benfica", "Barcelona", "2025-01-21"),
    ("2024-25", "League Phase", "MD7", "Feyenoord", "Bayern Munich", "2025-01-22"),
    ("2024-25", "League Phase", "MD7", "AC Milan", "Girona", "2025-01-22"),
    ("2024-25", "League Phase", "MD7", "Real Madrid", "Salzburg", "2025-01-22"),
    ("2024-25", "League Phase", "MD7", "Celtic", "Young Boys", "2025-01-22"),
    ("2024-25", "League Phase", "MD7", "Inter Milan", "Monaco", "2025-01-22"),
    ("2024-25", "League Phase", "MD7", "Man City", "Club Brugge", "2025-01-22"),
    ("2024-25", "League Phase", "MD7", "PSG", "Man City", "2025-01-22"),
    ("2024-25", "League Phase", "MD7", "Sparta Prague", "Inter Milan", "2025-01-22"),
    ("2024-25", "League Phase", "MD7", "Stuttgart", "Slovan Bratislava", "2025-01-22"),
    ("2024-25", "League Phase", "MD7", "Sporting CP", "Bologna", "2025-01-22"),

    # Matchday 8 (Jan 29, 2025)
    ("2024-25", "League Phase", "MD8", "Barcelona", "Atalanta", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Bayern Munich", "Slovan Bratislava", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Dortmund", "Shakhtar Donetsk", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Inter Milan", "Monaco", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Juventus", "Benfica", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Lille", "Feyenoord", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Man City", "Club Brugge", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "PSG", "Stuttgart", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Salzburg", "Atletico Madrid", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Sporting CP", "Bologna", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Brest", "Real Madrid", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Dinamo Zagreb", "AC Milan", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Girona", "Arsenal", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Bayer Leverkusen", "Sparta Prague", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Aston Villa", "Celtic", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "RB Leipzig", "Sturm Graz", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Red Star Belgrade", "Young Boys", "2025-01-29"),
    ("2024-25", "League Phase", "MD8", "Young Boys", "Red Star Belgrade", "2025-01-29"),
]

UCL_2024_25_KNOCKOUTS = [
    # Knockout playoff round
    ("2024-25", "Knockout Playoff", "Leg 1", "Juventus", "PSV", "2025-02-11"),
    ("2024-25", "Knockout Playoff", "Leg 1", "Feyenoord", "AC Milan", "2025-02-11"),
    ("2024-25", "Knockout Playoff", "Leg 1", "Club Brugge", "Atalanta", "2025-02-11"),
    ("2024-25", "Knockout Playoff", "Leg 1", "Sporting CP", "Dortmund", "2025-02-11"),
    ("2024-25", "Knockout Playoff", "Leg 1", "Man City", "Real Madrid", "2025-02-11"),
    ("2024-25", "Knockout Playoff", "Leg 1", "Celtic", "Bayern Munich", "2025-02-11"),
    ("2024-25", "Knockout Playoff", "Leg 1", "Monaco", "Benfica", "2025-02-11"),
    ("2024-25", "Knockout Playoff", "Leg 1", "Brest", "PSG", "2025-02-11"),
    ("2024-25", "Knockout Playoff", "Leg 2", "PSV", "Juventus", "2025-02-18"),
    ("2024-25", "Knockout Playoff", "Leg 2", "AC Milan", "Feyenoord", "2025-02-18"),
    ("2024-25", "Knockout Playoff", "Leg 2", "Atalanta", "Club Brugge", "2025-02-18"),
    ("2024-25", "Knockout Playoff", "Leg 2", "Dortmund", "Sporting CP", "2025-02-18"),
    ("2024-25", "Knockout Playoff", "Leg 2", "Real Madrid", "Man City", "2025-02-18"),
    ("2024-25", "Knockout Playoff", "Leg 2", "Bayern Munich", "Celtic", "2025-02-18"),
    ("2024-25", "Knockout Playoff", "Leg 2", "Benfica", "Monaco", "2025-02-18"),
    ("2024-25", "Knockout Playoff", "Leg 2", "PSG", "Brest", "2025-02-18"),

    # Round of 16
    ("2024-25", "Round of 16", "Leg 1", "Atalanta", "Barcelona", "2025-03-04"),
    ("2024-25", "Round of 16", "Leg 1", "Dortmund", "Liverpool", "2025-03-04"),
    ("2024-25", "Round of 16", "Leg 1", "Real Madrid", "Atletico Madrid", "2025-03-04"),
    ("2024-25", "Round of 16", "Leg 1", "Juventus", "Arsenal", "2025-03-04"),
    ("2024-25", "Round of 16", "Leg 1", "AC Milan", "Inter Milan", "2025-03-05"),
    ("2024-25", "Round of 16", "Leg 1", "Bayern Munich", "Benfica", "2025-03-05"),
    ("2024-25", "Round of 16", "Leg 1", "PSG", "Lille", "2025-03-05"),
    ("2024-25", "Round of 16", "Leg 1", "Feyenoord", "Bayer Leverkusen", "2025-03-05"),
    ("2024-25", "Round of 16", "Leg 2", "Barcelona", "Atalanta", "2025-03-11"),
    ("2024-25", "Round of 16", "Leg 2", "Liverpool", "Dortmund", "2025-03-11"),
    ("2024-25", "Round of 16", "Leg 2", "Atletico Madrid", "Real Madrid", "2025-03-11"),
    ("2024-25", "Round of 16", "Leg 2", "Arsenal", "Juventus", "2025-03-11"),
    ("2024-25", "Round of 16", "Leg 2", "Inter Milan", "AC Milan", "2025-03-12"),
    ("2024-25", "Round of 16", "Leg 2", "Benfica", "Bayern Munich", "2025-03-12"),
    ("2024-25", "Round of 16", "Leg 2", "Lille", "PSG", "2025-03-12"),
    ("2024-25", "Round of 16", "Leg 2", "Bayer Leverkusen", "Feyenoord", "2025-03-12"),

    # Quarter-finals
    ("2024-25", "Quarter-final", "Leg 1", "Barcelona", "Liverpool", "2025-04-08"),
    ("2024-25", "Quarter-final", "Leg 1", "Inter Milan", "Bayern Munich", "2025-04-08"),
    ("2024-25", "Quarter-final", "Leg 1", "Arsenal", "PSG", "2025-04-09"),
    ("2024-25", "Quarter-final", "Leg 1", "Atletico Madrid", "Bayer Leverkusen", "2025-04-09"),
    ("2024-25", "Quarter-final", "Leg 2", "Liverpool", "Barcelona", "2025-04-15"),
    ("2024-25", "Quarter-final", "Leg 2", "Bayern Munich", "Inter Milan", "2025-04-15"),
    ("2024-25", "Quarter-final", "Leg 2", "PSG", "Arsenal", "2025-04-16"),
    ("2024-25", "Quarter-final", "Leg 2", "Bayer Leverkusen", "Atletico Madrid", "2025-04-16"),

    # Semi-finals
    ("2024-25", "Semi-final", "Leg 1", "Arsenal", "Barcelona", "2025-04-29"),
    ("2024-25", "Semi-final", "Leg 1", "Inter Milan", "Atletico Madrid", "2025-04-30"),
    ("2024-25", "Semi-final", "Leg 2", "Barcelona", "Arsenal", "2025-05-06"),
    ("2024-25", "Semi-final", "Leg 2", "Atletico Madrid", "Inter Milan", "2025-05-07"),

    # Final (TBD — May 31, 2025 in Munich)
    # ("2024-25", "Final", "Final", "TBD", "TBD", "2025-05-31"),
]


def main():
    all_matches = UCL_2023_24 + UCL_2024_25_LEAGUE + UCL_2024_25_KNOCKOUTS

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["season", "stage", "matchday", "home_team", "away_team", "date", "youtube_url"])

        for match in all_matches:
            writer.writerow(list(match) + [""])

    total = len(all_matches)
    league_phase = len(UCL_2024_25_LEAGUE)
    knockouts = len(UCL_2024_25_KNOCKOUTS)
    print(f"Generated {OUTPUT_PATH}")
    print(f"Total matches: {total}")
    print(f"  2023-24: {len(UCL_2023_24)} (group stage + knockouts)")
    print(f"  2024-25 league phase: {league_phase}")
    print(f"  2024-25 knockouts: {knockouts}")
    print()
    print("NEXT STEPS:")
    print("  1. Run: python scripts/autofill_urls.py --dry-run   (preview searches)")
    print("  2. Run: python scripts/autofill_urls.py             (fill URLs)")
    print("  3. Spot-check the CSV")
    print("  4. Run: python scripts/download_highlights.py       (download videos)")


if __name__ == "__main__":
    main()
