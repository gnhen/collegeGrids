#!/usr/bin/env python3
"""
College Grid Generator - Creates playable 3x3 grids from processed data.

Usage:
    python generate_grids.py [date]
    
    Example:
    python generate_grids.py 2025-10-03
    
    If no date provided, generates for today.

Determinism:
    The generator seeds its random choice by date so the same date always
    produces the same grid.  This is important for reproducibility and for
    the frontend to know which grid belongs to which day.
"""

import json
import os
import sys
import random
import datetime
from collections import defaultdict

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "data")
GRIDS_DIR = os.path.join(DATA_DIR, "grids")
AWARDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "awards")


def ensure_dirs():
    os.makedirs(GRIDS_DIR, exist_ok=True)


def load_player_data():
    player_file = os.path.join(DATA_DIR, "players.json")
    if os.path.exists(player_file):
        with open(player_file, "r") as f:
            return json.load(f)
    return {}


def load_awards(year):
    awards_file = os.path.join(AWARDS_DIR, f"{year}_awards.json")
    if os.path.exists(awards_file):
        with open(awards_file, "r") as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------

def _cat_label(cat):
    """Return a human-readable label for a category dict."""
    if cat["type"] == "school":
        return cat["value"]
    if cat["type"] == "conference":
        return cat["value"]
    if cat["type"] == "season_stat":
        unit = {"passing_yards": "pass yds", "rushing_yards": "rush yds",
                "receiving_yards": "rec yds", "tackles": "tackles",
                "sacks": "sacks", "interceptions": "INT",
                "passing_tds": "pass TD", "rushing_tds": "rush TD",
                "receiving_tds": "rec TD", "field_goals_made": "FG"}.get(
            cat["stat_type"], cat["stat_type"])
        return f"{cat['threshold']}+ {unit}"
    if cat["type"] == "award":
        return cat["name"]
    if cat["type"] == "transfer":
        return "Transfer"
    return str(cat)


def _cat_key(cat):
    """Return a stable key for a category (used for seeding / dedup)."""
    if cat["type"] in ("school", "conference", "award"):
        return (cat["type"], cat["value"] or cat["name"])
    if cat["type"] == "season_stat":
        return (cat["type"], cat["stat_type"], cat["threshold"])
    if cat["type"] == "transfer":
        return ("transfer",)
    return (str(cat),)


def generate_categories(players, awards, year):
    """Generate a diverse set of categories from real data."""
    categories = []
    seen_keys = set()

    def add_cat(cat):
        key = _cat_key(cat)
        if key in seen_keys:
            return
        seen_keys.add(key)
        categories.append(cat)

    # --- Schools (pick 5-6 with the most players) ---
    school_players = defaultdict(list)
    for pid, pdata in players.items():
        for school in pdata.get("schools", []):
            school_players[school].append(pid)

    valid_schools = {k: v for k, v in school_players.items() if len(v) >= 5}
    top_schools = sorted(valid_schools.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    for school, pids in top_schools:
        add_cat({"type": "school", "value": school, "player_ids": pids})

    # --- Conferences (deduplicated by name) ---
    conf_players = defaultdict(set)
    for pid, pdata in players.items():
        for conf in pdata.get("conferences", []):
            conf_players[conf].add(pid)

    valid_confs = {k: sorted(v) for k, v in conf_players.items() if len(v) >= 5}
    for conf, pids in sorted(valid_confs.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
        add_cat({"type": "conference", "value": conf, "player_ids": pids})

    # --- Season stats (passing, rushing, receiving yards for current year) ---
    stat_types = ["passing_yards", "rushing_yards", "receiving_yards"]
    thresholds_map = {
        "passing_yards": [1000, 2000, 3000, 4000],
        "rushing_yards": [200, 500, 1000, 1500],
        "receiving_yards": [200, 500, 1000, 1500],
    }

    for stat_type in stat_types:
        player_totals = {}
        for pid, pdata in players.items():
            total = 0
            for season, sstats in pdata.get("season_stats", {}).items():
                total += sstats.get(stat_type, 0)
            if total > 0:
                player_totals[pid] = total

        for threshold in thresholds_map.get(stat_type, [500]):
            pids = sorted([pid for pid, total in player_totals.items() if total >= threshold])
            if len(pids) >= 3:
                add_cat({
                    "type": "season_stat",
                    "stat_type": stat_type,
                    "threshold": threshold,
                    "season": year,
                    "player_ids": pids,
                })

    # --- Awards ---
    awards_data = load_awards(year)
    if awards_data:
        for award_name, award_info in awards_data.items():
            winners = sorted([w["athlete_id"] for w in award_info.get("winners", []) if w.get("athlete_id")])
            if len(winners) >= 1:
                add_cat({
                    "type": "award",
                    "name": award_name,
                    "year": year,
                    "player_ids": winners,
                })

    # --- Transfers ---
    transfer_players = sorted([pid for pid, pdata in players.items() if pdata.get("transferred", False)])
    if len(transfer_players) >= 3:
        add_cat({"type": "transfer", "value": "Transfer", "player_ids": transfer_players})

    return categories


# ---------------------------------------------------------------------------
# Grid generation
# ---------------------------------------------------------------------------

def _try_generate(categories, seed_str):
    """Try one random draw; return grid dict or None."""
    rng = random.Random(seed_str)

    school_cats = [c for c in categories if c["type"] == "school"]
    conf_cats = [c for c in categories if c["type"] == "conference"]
    stat_cats = [c for c in categories if c["type"] == "season_stat"]
    award_cats = [c for c in categories if c["type"] == "award"]
    transfer_cats = [c for c in categories if c["type"] == "transfer"]

    # Always pick at least one school and one stat for rows/cols
    row_cats = []
    if school_cats:
        row_cats.append(rng.choice(school_cats))
    if stat_cats:
        row_cats.append(rng.choice(stat_cats))
    if conf_cats:
        row_cats.append(rng.choice(conf_cats))

    col_cats = []
    if school_cats:
        col_cats.append(rng.choice(school_cats))
    if stat_cats:
        col_cats.append(rng.choice(stat_cats))
    if conf_cats:
        col_cats.append(rng.choice(conf_cats))

    # Fill remaining slots
    all_cats = [c for c in categories if c not in row_cats]
    rng.shuffle(all_cats)
    for c in all_cats:
        if len(row_cats) >= 3 and len(col_cats) >= 3:
            break
        if len(row_cats) < 3 and c not in row_cats:
            row_cats.append(c)
        if len(col_cats) < 3 and c not in col_cats:
            col_cats.append(c)

    grid = {}
    playable = True
    for i, rc in enumerate(row_cats):
        for j, cc in enumerate(col_cats):
            cell_key = f"{i}_{j}"
            valid = sorted(set(rc["player_ids"]) & set(cc["player_ids"]))
            grid[cell_key] = valid
            if not valid:
                playable = False

    if playable:
        return {"row_categories": row_cats, "col_categories": col_cats, "grid": grid}
    return None


def generate_grid(categories, players, date):
    """Generate a playable 3x3 grid for the given date.

    Uses the date as a seed so the same date always produces the same grid.
    Tries multiple random draws until a playable grid is found (up to 20).
    """
    seed_str = f"college-grid-{date}"
    for attempt in range(20):
        result = _try_generate(categories, seed_str + f"-{attempt}")
        if result:
            return result
    return None


def main():
    ensure_dirs()

    if len(sys.argv) >= 2:
        date = sys.argv[1]
    else:
        date = datetime.datetime.now().strftime("%Y-%m-%d")

    print(f"Starting grid generator for date: {date}")

    year = int(date.split("-")[0])

    players = load_player_data()
    if not players:
        print("[!] No player data found. Run ingest_boxscores.py first.")
        return

    print(f"  [✓] Loaded {len(players)} players")

    categories = generate_categories(players, {}, year)
    print(f"  [✓] Generated {len(categories)} categories")

    grid = generate_grid(categories, players, date)

    if grid:
        grid["date"] = date
        grid_file = os.path.join(GRIDS_DIR, f"{date}.json")
        with open(grid_file, "w") as f:
            json.dump(grid, f, indent=2)
        print(f"[✓] Grid generated and saved to {grid_file}")

        print("\nGrid Summary:")
        print("  Rows:")
        for i, cat in enumerate(grid["row_categories"]):
            label = _cat_label(cat)
            print(f"    {i+1}. {label} ({len(cat['player_ids'])} players)")
        print("  Columns:")
        for i, cat in enumerate(grid["col_categories"]):
            label = _cat_label(cat)
            print(f"    {i+1}. {label} ({len(cat['player_ids'])} players)")
    else:
        print("[!] Failed to generate a playable grid after 20 attempts.")


if __name__ == "__main__":
    main()