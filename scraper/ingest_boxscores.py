#!/usr/bin/env python3
"""
College Grid Scraper - Crawls ESPN College Football box scores
to build a player-school-season database.

Usage:
    python ingest_boxscores.py [start_date] [end_date]
    
    Example:
    python ingest_boxscores.py 20240907 20241005
    
    If no dates provided, crawls the last 30 days.

Output:
    web/data/players.json  - Player records with schools, conferences, stats
    web/data/boxscores/    - Raw box score JSON files
    scraper/.checkpoint.json - Resume point for resuming crawls
"""

import json
import os
import sys
import time
import urllib.request
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Configuration
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football"
# Write directly to the web data directory the site reads
BOXSCORE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "data", "boxscores")
PLAYER_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "data", "players.json")
CHECKPOINT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".checkpoint.json")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def ensure_dirs():
    os.makedirs(BOXSCORE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {"processed_events": [], "last_run": None}


def save_checkpoint(processed_events, last_run=None):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({
            "processed_events": processed_events,
            "last_run": last_run or datetime.datetime.now().isoformat(),
        }, f, indent=2)


def fetch_json(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=20) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
                else:
                    print(f"  [!] HTTP {response.status} for {url}")
                    return None
        except urllib.error.HTTPError as e:
            print(f"  [!] HTTP Error {e.code} for {url}: {e.reason}")
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
        except urllib.error.URLError as e:
            print(f"  [!] URL Error for {url}: {e.reason}")
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
        except Exception as e:
            print(f"  [!] Unexpected error for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    return None


def get_date_range(start_date, end_date):
    start = datetime.datetime.strptime(start_date, "%Y%m%d")
    end = datetime.datetime.strptime(end_date, "%Y%m%d")
    current = start
    while current <= end:
        yield current.strftime("%Y%m%d")
        current += datetime.timedelta(days=1)


def crawl_scoreboard(date_str):
    print(f"--- Crawling Scoreboard: {date_str} ---")
    sb_url = f"{BASE_URL}/scoreboard?dates={date_str}&limit=300&groups=80"
    sb = fetch_json(sb_url)
    if not sb:
        print(f"  [!] Failed to fetch scoreboard for {date_str}")
        return []
    events = sb.get("events", [])
    print(f"  Found {len(events)} events.")
    return events


# ---------------------------------------------------------------------------
# School ID mapping from ESPN teams endpoint
# ---------------------------------------------------------------------------

SCHOOL_ID_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".school_ids.json")

def load_school_id_cache():
    if os.path.exists(SCHOOL_ID_CACHE):
        with open(SCHOOL_ID_CACHE, "r") as f:
            return json.load(f)
    return {}

def save_school_id_cache(cache):
    with open(SCHOOL_ID_CACHE, "w") as f:
        json.dump(cache, f, indent=2)

def build_school_id_map():
    """Fetch all FBS teams from ESPN and build school_name -> school_id mapping."""
    cache = load_school_id_cache()
    if len(cache) > 50:  # Already populated
        return cache

    print("\n--- Building School ID Map ---")
    teams_url = f"{BASE_URL}/teams"
    data = fetch_json(teams_url)
    if not data:
        print("  [!] Failed to fetch teams endpoint")
        return cache

    teams_list = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
    count = 0
    for team_entry in teams_list:
        team = team_entry.get("team", {})
        name = team.get("displayName", "")
        tid = team.get("id")
        if name and tid:
            cache[name] = str(tid)
            count += 1
    save_school_id_cache(cache)
    print(f"  [✓] Mapped {count} teams")
    return cache


def process_game(event):
    eid = event.get("id")
    ename = event.get("name", "Unknown Event")
    if not eid:
        return None, None

    checkpoint = load_checkpoint()
    if eid in checkpoint["processed_events"]:
        print(f"    [✓] Already processed: {eid}")
        return eid, None

    print(f"    [>] Processing game: {eid} - {ename}")
    summary_url = f"{BASE_URL}/summary?event={eid}"
    data = fetch_json(summary_url)

    if not data or "boxscore" not in data:
        print(f"    [!] No boxscore data for {eid}")
        return None, None

    filepath = os.path.join(BOXSCORE_DIR, f"{eid}.json")
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return eid, data


# ---------------------------------------------------------------------------
# Conference resolution from team name
# ---------------------------------------------------------------------------

# Known conference mappings from ESPN team names
CONFERENCE_MAP = {
    # SEC
    "Alabama": "SEC", "Auburn": "SEC", "Arkansas": "SEC", "Florida": "SEC",
    "Georgia": "SEC", "Kentucky": "SEC", "LSU": "SEC", "Mississippi State": "SEC",
    "Missouri": "SEC", "Ole Miss": "SEC", "South Carolina": "SEC",
    "Tennessee": "SEC", "Texas A&M": "SEC", "Vanderbilt": "SEC",
    # Big Ten
    "Illinois": "Big Ten", "Indiana": "Big Ten", "Iowa": "Big Ten",
    "Maryland": "Big Ten", "Michigan": "Big Ten", "Michigan State": "Big Ten",
    "Minnesota": "Big Ten", "Nebraska": "Big Ten", "Northwestern": "Big Ten",
    "Ohio State": "Big Ten", "Penn State": "Big Ten", "Purdue": "Big Ten",
    "Rutgers": "Big Ten", "Wisconsin": "Big Ten",
    # ACC
    "Boston College": "ACC", "Clemson": "ACC", "Duke": "ACC", "Florida State": "ACC",
    "Georgia Tech": "ACC", "California": "ACC", "Colorado": "ACC",
    "Houston": "ACC", "Indiana": "ACC", "Iowa State": "ACC",
    "Louisville": "ACC", "Miami": "ACC", "NC State": "ACC", "Notre Dame": "ACC",
    "North Carolina": "ACC", "Pittsburgh": "ACC", "Syracuse": "ACC",
    "Wake Forest": "ACC", "Virginia": "ACC", "Virginia Tech": "ACC",
    # Big 12
    "Arizona": "Big 12", "Arizona State": "Big 12", "Baylor": "Big 12",
    "BYU": "Big 12", "Cincinnati": "Big 12", "Colorado": "Big 12",
    "Iowa State": "Big 12", "Kansas": "Big 12", "Kansas State": "Big 12",
    "Oklahoma": "Big 12", "Oklahoma State": "Big 12", "TCU": "Big 12",
    "Texas": "Big 12", "Texas A&M": "Big 12", "Texas Tech": "Big 12",
    "UCF": "Big 12", "Utah": "Big 12", "West Virginia": "Big 12",
    # Pac-12 (legacy / partial)
    "Oregon": "Pac-12", "Oregon State": "Pac-12", "Stanford": "Pac-12",
    "UCLA": "Pac-12", "USC": "Pac-12", "Washington": "Pac-12",
    "Washington State": "Pac-12",
    # American Athletic Conference
    "Charlotte": "AAC", "FAU": "AAC", "FIU": "AAC", "Memphis": "AAC",
    "Navy": "AAC", "North Texas": "AAC", "Rice": "AAC", "SMU": "AAC",
    "Temple": "AAC", "Tulane": "AAC", "Tulsa": "AAC", "UTSA": "AAC",
    "UConn": "AAC", "UCF": "AAC",
    # Mountain West
    "Air Force": "MWC", "Boise State": "MWC", "Colorado State": "MWC",
    "Fresno State": "MWC", "Hawaii": "MWC", "New Mexico": "MWC",
    "Nevada": "MWC", "San Diego State": "MWC", "San Jose State": "MWC",
    "UNLV": "MWC", "Utah State": "MWC", "Wyoming": "MWC",
    # Sun Belt
    "App State": "Sun Belt", "Arkansas State": "Sun Belt", "Georgia Southern": "Sun Belt",
    "Georgia State": "Sun Belt", "James Madison": "Sun Belt",
    "Louisiana": "Sun Belt", "Marshall": "Sun Belt", "Old Dominion": "Sun Belt",
    "South Alabama": "Sun Belt", "Southern Miss": "Sun Belt",
    "Troy": "Sun Belt", "Texas State": "Sun Belt", "UAB": "Sun Belt",
    "UTEP": "Sun Belt", "UMass": "Sun Belt", "Western Kentucky": "Sun Belt",
    # MAC
    "Akron": "MAC", "Ball State": "MAC", "Bowling Green": "MAC",
    "Buffalo": "MAC", "Central Michigan": "MAC", "Eastern Michigan": "MAC",
    "Kent State": "MAC", "Miami (OH)": "MAC", "Northern Illinois": "MAC",
    "Ohio": "MAC", "Toledo": "MAC", "Western Michigan": "MAC",
}


def resolve_conference(team_name):
    """Return conference for a team display name, or 'Independent'."""
    if not team_name:
        return "Independent"
    for key, conf in CONFERENCE_MAP.items():
        if key.lower() in team_name.lower():
            return conf
    return "Independent"


# ---------------------------------------------------------------------------
# Build player database from raw box scores
# ---------------------------------------------------------------------------

def build_player_database():
    """Build player records from raw box score JSON files."""
    print("\n--- Building Player Database ---")

    # Build school name -> ID map
    school_id_map = build_school_id_map()

    players = {}  # id -> player record
    # Track which (team, year) combos each player appeared in
    player_school_years = defaultdict(set)  # player_id -> set of (team_name, year)

    if not os.path.exists(BOXSCORE_DIR):
        print("[!] No boxscore directory found.")
        return {}, {}

    boxscore_files = [f for f in os.listdir(BOXSCORE_DIR) if f.endswith(".json")]
    print(f"Found {len(boxscore_files)} box score files.")

    for filename in boxscore_files:
        filepath = os.path.join(BOXSCORE_DIR, filename)
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [!] Error reading {filename}: {e}")
            continue

        boxscore = data.get("boxscore", {})
        for team_data in boxscore.get("players", []):
            team_info = team_data.get("team", {})
            team_id = team_info.get("id")
            team_name = team_info.get("displayName") or team_info.get("name", "")

            for stat_category in team_data.get("statistics", []):
                category_name = stat_category.get("name", "")
                athletes = stat_category.get("athletes", [])

                for athlete_data in athletes:
                    athlete = athlete_data.get("athlete", {})
                    stats = athlete_data.get("stats", [])
                    player_id = athlete.get("id")
                    player_name = athlete.get("displayName", "")

                    if not player_id or not player_name:
                        continue

                    # Initialize player record if needed
                    if player_id not in players:
                        players[player_id] = {
                            "id": player_id,
                            "name": player_name,
                            "schools": [],
                            "school_ids": {},  # school_name -> espn_team_id
                            "conferences": [],
                            "season_stats": {},
                            "career_stats": {},
                            "awards": [],
                            "transferred": False,
                        }

                    # Track unique schools and their ESPN IDs
                    if team_name and team_name not in players[player_id]["schools"]:
                        players[player_id]["schools"].append(team_name)
                        # Look up ESPN team ID
                        espn_id = school_id_map.get(team_name)
                        if espn_id:
                            players[player_id]["school_ids"][team_name] = espn_id

                    # Track school+year combos for transfer detection
                    event_date = data.get("header", {}).get("date", "")
                    if event_date:
                        year = event_date[:4]
                    else:
                        year = filename.replace(".json", "")[:4]
                    if year and len(year) == 4:
                        player_school_years[player_id].add((team_name, year))

                    # Accumulate stats per season
                    season_key = year if year and len(year) == 4 else "unknown"
                    season_stats = players[player_id]["season_stats"].setdefault(season_key, {})

                    if category_name == "passing" and len(stats) >= 6:
                        try:
                            season_stats["passing_yards"] = season_stats.get("passing_yards", 0) + int(stats[1])
                            if "/" in stats[0]:
                                parts = stats[0].split("/")
                                season_stats["passing_attempts"] = season_stats.get("passing_attempts", 0) + int(parts[1])
                                season_stats["passing_completions"] = season_stats.get("passing_completions", 0) + int(parts[0])
                            season_stats["passing_tds"] = season_stats.get("passing_tds", 0) + int(stats[3])
                            season_stats["passing_ints"] = season_stats.get("passing_ints", 0) + int(stats[4])
                        except (ValueError, TypeError, IndexError):
                            pass

                    elif category_name == "rushing" and len(stats) >= 5:
                        try:
                            season_stats["rushing_yards"] = season_stats.get("rushing_yards", 0) + int(stats[1])
                            season_stats["rushing_attempts"] = season_stats.get("rushing_attempts", 0) + int(stats[0])
                            season_stats["rushing_tds"] = season_stats.get("rushing_tds", 0) + int(stats[3])
                        except (ValueError, TypeError, IndexError):
                            pass

                    elif category_name == "receiving" and len(stats) >= 5:
                        try:
                            season_stats["receiving_yards"] = season_stats.get("receiving_yards", 0) + int(stats[1])
                            season_stats["receiving_receptions"] = season_stats.get("receiving_receptions", 0) + int(stats[0])
                            season_stats["receiving_tds"] = season_stats.get("receiving_tds", 0) + int(stats[3])
                        except (ValueError, TypeError, IndexError):
                            pass

                    elif category_name == "defensive" and len(stats) >= 5:
                        try:
                            season_stats["tackles"] = season_stats.get("tackles", 0) + int(stats[0])
                            season_stats["solo_tackles"] = season_stats.get("solo_tackles", 0) + int(stats[1]) if len(stats) > 1 else 0
                            season_stats["assisted_tackles"] = season_stats.get("assisted_tackles", 0) + int(stats[2]) if len(stats) > 2 else 0
                            season_stats["sacks"] = season_stats.get("sacks", 0) + int(stats[3]) if len(stats) > 3 else 0
                        except (ValueError, TypeError, IndexError):
                            pass

                    elif category_name == "interceptions" and len(stats) >= 3:
                        try:
                            season_stats["interceptions"] = season_stats.get("interceptions", 0) + int(stats[0])
                        except (ValueError, TypeError):
                            pass

                    elif category_name == "kicking" and len(stats) >= 3:
                        try:
                            season_stats["field_goals_made"] = season_stats.get("field_goals_made", 0) + int(stats[0])
                            season_stats["field_goals_attempted"] = season_stats.get("field_goals_attempted", 0) + int(stats[1])
                        except (ValueError, TypeError):
                            pass

                    elif category_name == "punting" and len(stats) >= 3:
                        try:
                            season_stats["punts"] = season_stats.get("punts", 0) + int(stats[0])
                            season_stats["punt_yards"] = season_stats.get("punt_yards", 0) + int(stats[1])
                        except (ValueError, TypeError):
                            pass

                    elif category_name == "kickReturns" and len(stats) >= 3:
                        try:
                            season_stats["kick_returns"] = season_stats.get("kick_returns", 0) + int(stats[0])
                            season_stats["kick_return_yards"] = season_stats.get("kick_return_yards", 0) + int(stats[1])
                        except (ValueError, TypeError):
                            pass

                    elif category_name == "puntReturns" and len(stats) >= 3:
                        try:
                            season_stats["punt_returns"] = season_stats.get("punt_returns", 0) + int(stats[0])
                            season_stats["punt_return_yards"] = season_stats.get("punt_return_yards", 0) + int(stats[1])
                        except (ValueError, TypeError):
                            pass

                    elif category_name == "fumbles" and len(stats) >= 3:
                        try:
                            season_stats["fumbles_lost"] = season_stats.get("fumbles_lost", 0) + int(stats[0])
                        except (ValueError, TypeError):
                            pass

    # Update conferences for each player
    for player_id, player in players.items():
        conferences = set()
        for school in player["schools"]:
            conf = resolve_conference(school)
            conferences.add(conf)
        player["conferences"] = sorted(conferences)

    # Update transfer status: player played for 2+ schools in the same season
    for player_id, school_years in player_school_years.items():
        year_schools = defaultdict(set)
        for team, year in school_years:
            year_schools[year].add(team)
        for year, teams in year_schools.items():
            if len(teams) > 1:
                players[player_id]["transferred"] = True
                break

    # Save player database
    with open(PLAYER_FILE, "w") as f:
        json.dump(players, f, indent=2)

    print(f"  [✓] Built player database with {len(players)} players")
    return players, player_school_years


def main():
    ensure_dirs()

    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    else:
        today = datetime.datetime.now()
        end_date = today.strftime("%Y%m%d")
        start_date = (today - datetime.timedelta(days=30)).strftime("%Y%m%d")

    print(f"Starting scraper for dates: {start_date} to {end_date}")

    checkpoint = load_checkpoint()
    processed_so_far = set(checkpoint["processed_events"])

    dates = list(get_date_range(start_date, end_date))
    print(f"Total dates to process: {len(dates)}")

    total_processed = 0

    for date_str in dates:
        events = crawl_scoreboard(date_str)
        if not events:
            continue

        newly_processed = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(process_game, event): event for event in events}
            for future in as_completed(futures):
                try:
                    eid, data = future.result()
                    if eid and eid not in processed_so_far:
                        processed_so_far.add(eid)
                        newly_processed.append(eid)
                        total_processed += 1
                except Exception as e:
                    print(f"  [!] Error processing game: {e}")

        checkpoint = load_checkpoint()
        checkpoint["processed_events"] = list(processed_so_far)
        save_checkpoint(checkpoint)

        print(f"  [✓] Processed {len(newly_processed)} new games. Total: {total_processed}")
        time.sleep(1)

    build_player_database()
    print(f"\n[✓] Scraper complete. Total games processed: {total_processed}")


if __name__ == "__main__":
    main()