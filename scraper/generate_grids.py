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
CATEGORIES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scraper", "categories.json")

def ensure_dirs():
    """Create necessary directories if they don't exist."""
    os.makedirs(GRIDS_DIR, exist_ok=True)

def load_categories():
    """Load the category definitions."""
    if os.path.exists(CATEGORIES_FILE):
        with open(CATEGORIES_FILE, 'r') as f:
            return json.load(f)
    return None

def load_player_data():
    """Load processed player data."""
    player_file = os.path.join(DATA_DIR, "players.json")
    if os.path.exists(player_file):
        with open(player_file, 'r') as f:
            return json.load(f)
    return {}

def load_awards(year):
    """Load awards data for a specific year."""
    awards_file = os.path.join(DATA_DIR, "awards", f"{year}_awards.json")
    if os.path.exists(awards_file):
        with open(awards_file, 'r') as f:
            return json.load(f)
    return {}

def generate_categories(year):
    """Generate a set of categories for a given year."""
    categories = {
        "schools": [],
        "conferences": [],
        "season_stats": [],
        "career_stats": [],
        "awards": [],
        "transfers": [],
        "draft_picks": []
    }
    
    # Load awards for this year
    awards = load_awards(year)
    for award_name, award_data in awards.items():
        for winner in award_data.get("winners", []):
            categories["awards"].append({
                "type": "award",
                "name": award_name,
                "year": year,
                "player_id": winner["athlete_id"]
            })
    
    # Load player data for schools and stats
    players = load_player_data()
    for player_id, player_data in players.items():
        if player_data.get("school"):
            categories["schools"].append(player_id)
        if player_data.get("conference"):
            categories["conferences"].append(player_id)
    
    return categories

def find_valid_players_for_category(category, players):
    """Find all valid players for a given category."""
    valid_players = []
    
    if category["type"] == "school":
        for player_id, player_data in players.items():
            if player_data.get("school") == category["value"]:
                valid_players.append(player_id)
    
    elif category["type"] == "conference":
        for player_id, player_data in players.items():
            if player_data.get("conference") == category["value"]:
                valid_players.append(player_id)
    
    elif category["type"] == "season_stat":
        stat_type = category["stat_type"]
        threshold = category["threshold"]
        for player_id, player_data in players.items():
            season_stats = player_data.get("season_stats", {})
            for season, stats in season_stats.items():
                if stats.get(stat_type, 0) >= threshold:
                    valid_players.append(player_id)
                    break
    
    elif category["type"] == "career_stat":
        stat_type = category["stat_type"]
        threshold = category["threshold"]
        for player_id, player_data in players.items():
            career_stats = player_data.get("career_stats", {})
            if career_stats.get(stat_type, 0) >= threshold:
                valid_players.append(player_id)
    
    elif category["type"] == "award":
        for player_id, player_data in players.items():
            if player_id in category.get("winners", []):
                valid_players.append(player_id)
    
    elif category["type"] == "transfer":
        for player_id, player_data in players.items():
            if player_data.get("transferred", False):
                valid_players.append(player_id)
    
    return valid_players

def generate_grid(categories, players, date):
    """Generate a playable 3x3 grid."""
    # Select 3 random categories for rows
    row_categories = random.sample(categories, 3)
    col_categories = random.sample(categories, 3)
    
    # Find valid players for each cell
    grid = {}
    for i, row_cat in enumerate(row_categories):
        for j, col_cat in enumerate(col_cat):
            cell_key = f"{i}_{j}"
            valid_players = find_valid_players_for_category(row_cat, players) & find_valid_players_for_category(col_cat, players)
            grid[cell_key] = list(valid_players)
    
    # Check if grid is playable (every cell has at least 1 valid player)
    if all(len(grid.get(f"{i}_{j}", [])) > 0 for i in range(3) for j in range(3)):
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
    
    # Load data
    categories = load_categories()
    if not categories:
        # Generate categories for current year
        year = int(date.split('-')[0])
        categories = generate_categories(year)
    
    players = load_player_data()
    if not players:
        print("[!] No player data found. Run ingest_boxscores.py first.")
        return
    
    # Generate grid
    grid = generate_grid(categories["schools"] + categories["conferences"] + categories["season_stats"], players, date)
    
    if grid:
        # Save grid
        grid_file = os.path.join(GRIDS_DIR, f"{date}.json")
        with open(grid_file, 'w') as f:
            json.dump(grid, f, indent=2)
        print(f"[✓] Grid generated and saved to {grid_file}")
    else:
        print("[!] Failed to generate a playable grid.")

if __name__ == "__main__":
    main()
