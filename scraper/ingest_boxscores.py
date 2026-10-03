#!/usr/bin/env python3
"""
College Grid Scraper - Crawls ESPN College Football box scores
to build a player-school-season database.

Usage:
    python ingest_boxscores.py [start_date] [end_date]
    
    Example:
    python ingest_boxscores.py 20240907 20241005
    
    If no dates provided, crawls the last 30 days.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Configuration
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football"
RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed")
CHECKPOINT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".checkpoint.json")

# User-Agent to avoid being blocked
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def ensure_dirs():
    """Create necessary directories if they don't exist."""
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)

def load_checkpoint():
    """Load the checkpoint file to resume crawling."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {"processed_events": [], "last_run": None}

def save_checkpoint(processed_events, last_run=None):
    """Save the checkpoint file."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({
            "processed_events": processed_events,
            "last_run": last_run or datetime.datetime.now().isoformat()
        }, f, indent=2)

def fetch_json(url, retries=3, delay=2):
    """Fetch JSON from a URL with retry logic."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json"
            })
            with urllib.request.urlopen(req, timeout=20) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
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
    """Generate dates between start and end dates."""
    start = datetime.datetime.strptime(start_date, "%Y%m%d")
    end = datetime.datetime.strptime(end_date, "%Y%m%d")
    current = start
    while current <= end:
        yield current.strftime("%Y%m%d")
        current += datetime.timedelta(days=1)

def crawl_scoreboard(date_str):
    """Crawl the scoreboard for a specific date."""
    print(f"--- Crawling Scoreboard: {date_str} ---")
    sb_url = f"{BASE_URL}/scoreboard?dates={date_str}&limit=300&groups=80"
    sb = fetch_json(sb_url)
    
    if not sb:
        print(f"  [!] Failed to fetch scoreboard for {date_str}")
        return []
    
    events = sb.get('events', [])
    print(f"  Found {len(events)} events.")
    return events

def process_game(event):
    """Process a single game's box score."""
    eid = event.get('id')
    ename = event.get('name', 'Unknown Event')
    
    if not eid:
        return None, None
    
    # Check if already processed
    checkpoint = load_checkpoint()
    if eid in checkpoint['processed_events']:
        print(f"    [✓] Already processed: {eid}")
        return eid, None
    
    print(f"    [>] Processing game: {eid} - {ename}")
    
    summary_url = f"{BASE_URL}/summary?event={eid}"
    data = fetch_json(summary_url)
    
    if not data or 'boxscore' not in data:
        print(f"    [!] No boxscore data for {eid}")
        return None, None
    
    # Save raw box score
    filepath = os.path.join(RAW_DATA_DIR, f"{eid}.json")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return eid, data

def build_player_database():
    """Build a comprehensive player database from raw box scores."""
    print("\n--- Building Player Database ---")
    
    players = {}
    player_schools = defaultdict(set)  # player_id -> set of schools
    player_seasons = defaultdict(lambda: defaultdict(dict))  # player_id -> year -> {stat: value}
    player_transfers = defaultdict(set)  # player_id -> set of team_ids (for transfer detection)
    
    # Load all raw box scores
    if not os.path.exists(RAW_DATA_DIR):
        print("[!] No raw data directory found.")
        return {}, {}, {}
    
    boxscore_files = [f for f in os.listdir(RAW_DATA_DIR) if f.endswith('.json')]
    print(f"Found {len(boxscore_files)} box score files.")
    
    for filename in boxscore_files:
        filepath = os.path.join(RAW_DATA_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [!] Error reading {filename}: {e}")
            continue
        
        boxscore = data.get('boxscore', {})
        for team_data in boxscore.get('players', []):
            team_info = team_data.get('team', {})
            team_id = team_info.get('id')
            team_name = team_info.get('displayName', team_info.get('name', ''))
            
            for stat_category in team_data.get('statistics', []):
                category_name = stat_category.get('name', '')
                athletes = stat_category.get('athletes', [])
                
                for athlete_data in athletes:
                    athlete = athlete_data.get('athlete', {})
                    stats = athlete_data.get('stats', [])
                    
                    player_id = athlete.get('id')
                    player_name = athlete.get('displayName', '')
                    
                    if not player_id or not player_name:
                        continue
                    
                    # Initialize player record if needed
                    if player_id not in players:
                        players[player_id] = {
                            "id": player_id,
                            "name": player_name,
                            "schools": [],
                            "conferences": [],
                            "season_stats": {},
                            "career_stats": {},
                            "awards": [],
                            "transferred": False
                        }
                    
                    # Track schools
                    if team_name and team_name not in players[player_id]["schools"]:
                        players[player_id]["schools"].append(team_name)
                    
                    # Track transfers
                    if team_id:
                        player_transfers[player_id].add(team_id)
                    
                    # Accumulate stats
                    if category_name == 'passing' and len(stats) >= 6:
                        players[player_id]["season_stats"].setdefault("passing_yards", 0)
                        # stats[1] is usually passing yards
                        if len(stats) > 1 and stats[1]:
                            try:
                                players[player_id]["season_stats"]["passing_yards"] += int(stats[1])
                            except (ValueError, TypeError):
                                pass
                    
                    elif category_name == 'rushing' and len(stats) >= 5:
                        players[player_id]["season_stats"].setdefault("rushing_yards", 0)
                        # stats[1] is usually rushing yards
                        if len(stats) > 1 and stats[1]:
                            try:
                                players[player_id]["rushing_yards"] += int(stats[1])
                            except (ValueError, TypeError):
                                pass
                    
                    elif category_name == 'receiving' and len(stats) >= 5:
                        players[player_id]["season_stats"].setdefault("receiving_yards", 0)
                        # stats[1] is usually receiving yards
                        if len(stats) > 1 and stats[1]:
                            try:
                                players[player_id]["receiving_yards"] += int(stats[1])
                            except (ValueError, TypeError):
                                pass
        
        # Update transfer status
        for player_id, teams in player_transfers.items():
            if len(teams) > 1:
                players[player_id]["transferred"] = True
    
    # Save player database
    players_file = os.path.join(PROCESSED_DIR, "players.json")
    with open(players_file, 'w') as f:
        json.dump(players, f, indent=2)
    
    print(f"  [✓] Built player database with {len(players)} players")
    return players, player_schools, player_seasons

def main():
    """Main function to run the scraper."""
    ensure_dirs()
    
    # Parse command line arguments
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    else:
        # Default: last 30 days
        today = datetime.datetime.now()
        end_date = today.strftime("%Y%m%d")
        start_date = (today - datetime.timedelta(days=30)).strftime("%Y%m%d")
    
    print(f"Starting scraper for dates: {start_date} to {end_date}")
    
    checkpoint = load_checkpoint()
    processed_so_far = set(checkpoint['processed_events'])
    
    # Get all dates in range
    dates = list(get_date_range(start_date, end_date))
    print(f"Total dates to process: {len(dates)}")
    
    total_processed = 0
    
    for date_str in dates:
        events = crawl_scoreboard(date_str)
        
        if not events:
            continue
        
        # Process games in parallel
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
        
        # Update checkpoint
        checkpoint = load_checkpoint()
        checkpoint['processed_events'] = list(processed_so_far)
        save_checkpoint(checkpoint)
        
        print(f"  [✓] Processed {len(newly_processed)} new games. Total: {total_processed}")
        time.sleep(1)  # Polite delay between dates
    
    # Build player database
    players, player_schools, player_seasons = build_player_database()
    
    print(f"\n[✓] Scraper complete. Total games processed: {total_processed}")

if __name__ == "__main__":
    main()
