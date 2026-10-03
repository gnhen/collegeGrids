#!/usr/bin/env python3
"""
College Grid Generator - Creates playable 3x3 grids from processed data.

Usage:
    python generate_grids.py [date]
    
    Example:
    python generate_grids.py 2025-10-03
    
    If no date provided, generates for today.
"""

import json
import os
import sys
import random
import datetime
from collections import defaultdict

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed")
GRIDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "data", "grids")
AWARDS_DIR = os.path.join(DATA_DIR, "awards")

def ensure_dirs():
    """Create necessary directories if they don't exist."""
    os.makedirs(GRIDS_DIR, exist_ok=True)

def load_player_data():
    """Load processed player data."""
    player_file = os.path.join(DATA_DIR, "players.json")
    if os.path.exists(player_file):
        with open(player_file, 'r') as f:
            return json.load(f)
    return {}

def load_awards(year):
    """Load awards data for a specific year."""
    awards_file = os.path.join(AWARDS_DIR, f"{year}_awards.json")
    if os.path.exists(awards_file):
        with open(awards_file, 'r') as f:
            return json.load(f)
    return {}

def generate_categories(players, awards, year):
    """Generate a diverse set of categories from real data."""
    categories = []
    
    # Category 1: Schools (pick 3 random schools with many players)
    school_players = defaultdict(list)
    for player_id, player_data in players.items():
        for school in player_data.get("schools", []):
            school_players[school].append(player_id)
    
    # Filter schools with at least 5 players
    valid_schools = {k: v for k, v in school_players.items() if len(v) >= 5}
    if valid_schools:
        top_schools = sorted(valid_schools.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        for school, player_ids in random.sample(list(top_schools), min(3, len(top_schools))):
            categories.append({
                "type": "school",
                "value": school,
                "player_ids": player_ids
            })
    
    # Category 2: Conferences
    conference_players = defaultdict(list)
    for player_id, player_data in players.items():
        for school in player_data.get("schools", []):
            # Determine conference from school name (simplified)
            if "SEC" in school or "Alabama" in school or "Georgia" in school or "LSU" in school:
                conference_players["SEC"].append(player_id)
            elif "Big Ten" in school or "Ohio State" in school or "Michigan" in school or "Penn State" in school:
                conference_players["Big Ten"].append(player_id)
            elif "ACC" in school or "Clemson" in school or "Florida State" in school or "Notre Dame" in school:
                conference_players["ACC"].append(player_id)
            elif "Big 12" in school or "Texas" in school or "Oklahoma" in school or "Kansas" in school:
                conference_players["Big 12"].append(player_id)
            elif "Pac-12" in school or "Oregon" in school or "Washington" in school or "USC" in school:
                conference_players["Pac-12"].append(player_id)
            else:
                conference_players["Other"].append(player_id)
    
    valid_conferences = {k: v for k, v in conference_players.items() if len(v) >= 5}
    if valid_conferences:
        top_conferences = sorted(valid_conferences.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        for conf, player_ids in top_conferences:
            categories.append({
                "type": "conference",
                "value": conf,
                "player_ids": player_ids
            })
    
    # Category 3: Season Stats (passing, rushing, receiving yards)
    passing_yards = defaultdict(int)
    rushing_yards = defaultdict(int)
    receiving_yards = defaultdict(int)
    
    for player_id, player_data in players.items():
        stats = player_data.get("season_stats", {})
        passing_yards[player_id] = stats.get("passing_yards", 0)
        rushing_yards[player_id] = stats.get("rushing_yards", 0)
        receiving_yards[player_id] = stats.get("receiving_yards", 0)
    
    # Add passing yards category
    passing_thresholds = [1000, 2000, 3000, 4000, 5000]
    for threshold in passing_thresholds:
        players_with = [pid for pid, yards in passing_yards.items() if yards >= threshold]
        if len(players_with) >= 3:
            categories.append({
                "type": "season_stat",
                "stat_type": "passing_yards",
                "threshold": threshold,
                "season": year,
                "player_ids": players_with
            })
    
    # Add rushing yards category
    rushing_thresholds = [200, 500, 1000, 1500, 2000]
    for threshold in rushing_thresholds:
        players_with = [pid for pid, yards in rushing_yards.items() if yards >= threshold]
        if len(players_with) >= 3:
            categories.append({
                "type": "season_stat",
                "stat_type": "rushing_yards",
                "threshold": threshold,
                "season": year,
                "player_ids": players_with
            })
    
    # Add receiving yards category
    receiving_thresholds = [200, 500, 1000, 1500, 2000]
    for threshold in receiving_thresholds:
        players_with = [pid for pid, yards in receiving_yards.items() if yards >= threshold]
        if len(players_with) >= 3:
            categories.append({
                "type": "season_stat",
                "stat_type": "receiving_yards",
                "threshold": threshold,
                "season": year,
                "player_ids": players_with
            })
    
    # Category 4: Awards
    awards_data = load_awards(year)
    if awards_data:
        for award_name, award_info in awards_data.items():
            winners = [w["athlete_id"] for w in award_info.get("winners", []) if w.get("athlete_id")]
            if len(winners) >= 1:
                categories.append({
                    "type": "award",
                    "name": award_name,
                    "year": year,
                    "player_ids": winners
                })
    
    # Category 5: Transfers
    transfer_players = [pid for pid, player_data in players.items() if player_data.get("transferred", False)]
    if len(transfer_players) >= 3:
        categories.append({
            "type": "transfer",
            "value": "Transferred schools",
            "player_ids": transfer_players
        })
    
    return categories

def find_valid_players_for_category(category, all_players):
    """Find all valid players for a given category."""
    return category.get("player_ids", [])

def generate_grid(categories, players, date):
    """Generate a playable 3x3 grid."""
    # Separate categories by type for better balance
    school_cats = [c for c in categories if c["type"] == "school"]
    conf_cats = [c for c in categories if c["type"] == "conference"]
    stat_cats = [c for c in categories if c["type"] == "season_stat"]
    award_cats = [c for c in categories if c["type"] == "award"]
    transfer_cats = [c for c in categories if c["type"] == "transfer"]
    
    # Select 3 diverse categories for rows
    row_categories = []
    if school_cats:
        row_categories.append(random.choice(school_cats))
    if conf_cats:
        row_categories.append(random.choice(conf_cats))
    if stat_cats:
        row_categories.append(random.choice(stat_cats))
    
    # Select 3 diverse categories for columns
    col_categories = []
    if school_cats:
        col_categories.append(random.choice(school_cats))
    if conf_cats:
        col_categories.append(random.choice(conf_cats))
    if stat_cats:
        col_categories.append(random.choice(stat_cats))
    
    # Ensure we have 3 of each
    while len(row_categories) < 3:
        if stat_cats:
            row_categories.append(random.choice(stat_cats))
        elif award_cats:
            row_categories.append(random.choice(award_cats))
        elif transfer_cats:
            row_categories.append(random.choice(transfer_cats))
        else:
            break
    
    while len(col_categories) < 3:
        if stat_cats:
            col_categories.append(random.choice(stat_cats))
        elif award_cats:
            col_categories.append(random.choice(award_cats))
        elif transfer_cats:
            col_categories.append(random.choice(transfer_cats))
        else:
            break
    
    # Find valid players for each cell
    grid = {}
    playable = True
    for i, row_cat in enumerate(row_categories):
        for j, col_cat in enumerate(col_cat):
            cell_key = f"{i}_{j}"
            row_valid = set(row_cat.get("player_ids", []))
            col_valid = set(col_cat.get("player_ids", []))
            valid_players = list(row_valid & col_valid)
            grid[cell_key] = valid_players
            
            if not valid_players:
                playable = False
    
    # If not playable, try to find a better combination
    if not playable:
        print("  [!] Grid not playable, trying alternative categories...")
        # Try with different category combinations
        for _ in range(10):  # Try 10 times
            row_cats = []
            col_cats = []
            
            # Pick random categories
            if school_cats:
                row_cats.append(random.choice(school_cats))
                col_cats.append(random.choice(school_cats))
            if conf_cats:
                row_cats.append(random.choice(conf_cats))
                col_cats.append(random.choice(conf_cats))
            if stat_cats:
                row_cats.append(random.choice(stat_cats))
                col_cats.append(random.choice(stat_cats))
            
            grid = {}
            playable = True
            for i, row_cat in enumerate(row_cats):
                for j, col_cat in enumerate(col_cats):
                    cell_key = f"{i}_{j}"
                    valid_players = list(set(row_cat.get("player_ids", [])) & set(col_cat.get("player_ids", [])))
                    grid[cell_key] = valid_players
                    if not valid_players:
                        playable = False
            
            if playable:
                row_categories = row_cats
                col_categories = col_cats
                break
    
    if playable:
        return {
            "date": date,
            "row_categories": row_categories,
            "col_categories": col_categories,
            "grid": grid
        }
    
    return None

def main():
    """Main function to run the grid generator."""
    ensure_dirs()
    
    # Parse command line arguments
    if len(sys.argv) >= 2:
        date = sys.argv[1]
    else:
        # Default: today
        date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    print(f"Starting grid generator for date: {date}")
    
    # Extract year from date
    year = int(date.split('-')[0])
    
    # Load data
    players = load_player_data()
    if not players:
        print("[!] No player data found. Run ingest_boxscores.py first.")
        return
    
    print(f"  [✓] Loaded {len(players)} players")
    
    # Generate categories
    categories = generate_categories(players, {}, year)
    print(f"  [✓] Generated {len(categories)} categories")
    
    # Generate grid
    grid = generate_grid(categories, players, date)
    
    if grid:
        # Save grid
        grid_file = os.path.join(GRIDS_DIR, f"{date}.json")
        with open(grid_file, 'w') as f:
            json.dump(grid, f, indent=2)
        print(f"[✓] Grid generated and saved to {grid_file}")
        
        # Print grid summary
        print("\nGrid Summary:")
        print("  Rows:")
        for i, cat in enumerate(grid["row_categories"]):
            print(f"    {i+1}. {cat['value'] or cat['stat_type'] or cat['name']} ({len(cat['player_ids'])} players)")
        print("  Columns:")
        for i, cat in enumerate(grid["col_categories"]):
            print(f"    {i+1}. {cat['value'] or cat['stat_type'] or cat['name']} ({len(cat['player_ids'])} players)")
    else:
        print("[!] Failed to generate a playable grid.")

if __name__ == "__main__":
    main()
