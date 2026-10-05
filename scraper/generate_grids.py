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

Guarantees:
    Always produces a grid. If there's no real data, it falls back to
    a "played in 2024" catch-all that includes every player.
"""

import json
import os
import sys
import random
import datetime
from collections import defaultdict

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "web", "data")
GRIDS_DIR = os.path.join(DATA_DIR, "grids")
MIN_ANSWERS = 2  # every cell needs at least this many valid players
AWARDS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data", "processed", "awards")


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
    if cat["type"] == "catch_all":
        return cat.get("value", "Any player")
    return str(cat)


def _cat_key(cat):
    """Return a stable key for a category (used for seeding / dedup)."""
    if cat["type"] in ("school", "conference", "award"):
        return (cat["type"], cat["value"] or cat["name"])
    if cat["type"] == "season_stat":
        return (cat["type"], cat["stat_type"], cat["threshold"])
    if cat["type"] == "transfer":
        return ("transfer",)
    if cat["type"] == "catch_all":
        return ("catch_all", cat.get("value", ""))
    return (str(cat),)


def generate_categories(players, awards, year):
    """Generate a diverse set of categories from real data.

    Always includes at least one "catch-all" category that uses all players,
    so the grid generator can always find overlap.
    """
    categories = []
    seen_keys = set()
    all_player_ids = sorted(players.keys())

    def add_cat(cat):
        key = _cat_key(cat)
        if key in seen_keys:
            return
        seen_keys.add(key)
        categories.append(cat)

    # --- Catch-all (fallback: every player) ---
    if len(all_player_ids) >= 3:
        add_cat({
            "type": "catch_all",
            "value": f"Played {year}-present",
            "player_ids": all_player_ids,
        })

    # --- Schools (pick those with the most players) ---
    school_players = defaultdict(list)
    for pid, pdata in players.items():
        for school in pdata.get("schools", []):
            school_players[school].append(pid)

    valid_schools = {k: v for k, v in school_players.items() if len(v) >= 10}
    top_schools = sorted(valid_schools.items(), key=lambda x: len(x[1]), reverse=True)
    for school, pids in top_schools:
        add_cat({"type": "school", "value": school, "player_ids": sorted(pids)})

    # --- Conferences (deduplicated by name) ---
    conf_players = defaultdict(set)
    for pid, pdata in players.items():
        for conf in pdata.get("conferences", []):
            conf_players[conf].add(pid)

    valid_confs = {k: sorted(v) for k, v in conf_players.items() if len(v) >= 3}
    for conf, pids in sorted(valid_confs.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
        add_cat({"type": "conference", "value": conf, "player_ids": pids})

    # --- Season stats (passing, rushing, receiving yards for current year) ---
    stat_types = ["passing_yards", "rushing_yards", "receiving_yards"]
    thresholds_map = {
        "passing_yards": [500, 1000, 2000, 3000, 4000],
        "rushing_yards": [100, 200, 500, 1000, 1500],
        "receiving_yards": [100, 200, 500, 1000, 1500],
    }

    for stat_type in stat_types:
        player_totals = {}
        for pid, pdata in players.items():
            total = 0
            for season, sstats in pdata.get("season_stats", {}).items():
                total += sstats.get(stat_type, 0)
            if total > 0:
                player_totals[pid] = total

        for threshold in thresholds_map.get(stat_type, [100]):
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

    # Ensure we always have a catch-all in every row/col
    if not any(c["type"] == "catch_all" for c in categories):
        add_cat({
            "type": "catch_all",
            "value": "Any player",
            "player_ids": all_player_ids,
        })

    return categories


# ---------------------------------------------------------------------------
# Grid generation
# ---------------------------------------------------------------------------

def _try_generate(categories, seed_str, min_answers=MIN_ANSWERS):
    """Try one random draw; return grid dict or None."""
    rng = random.Random(seed_str)

    school_cats = [c for c in categories if c["type"] == "school"]
    conf_cats = [c for c in categories if c["type"] == "conference"]
    stat_cats = [c for c in categories if c["type"] == "season_stat"]
    award_cats = [c for c in categories if c["type"] == "award"]
    transfer_cats = [c for c in categories if c["type"] == "transfer"]
    catch_all_cats = [c for c in categories if c["type"] == "catch_all"]

    # Players have exactly one school, so two schools on opposite axes can never
    # overlap. Put schools (identity) on the rows and attributes (stats,
    # conferences, transfers, awards) on the columns so cells have answers.
    attr_cats = stat_cats + award_cats + transfer_cats  # conferences only fit one school, so skip

    if len(school_cats) >= 3 and len(attr_cats) >= 3:
        row_cats = rng.sample(school_cats, 3)
        col_cats = rng.sample(attr_cats, 3)
    else:
        # Not enough variety: pad with catch-all so we still return something
        row_cats = rng.sample(school_cats, min(3, len(school_cats)))
        col_cats = rng.sample(attr_cats, min(3, len(attr_cats)))
        while len(row_cats) < 3 and catch_all_cats:
            row_cats.append(catch_all_cats[0])
        while len(col_cats) < 3 and catch_all_cats:
            col_cats.append(catch_all_cats[0])

    grid = {}
    playable = True
    for i, rc in enumerate(row_cats):
        for j, cc in enumerate(col_cats):
            cell_key = f"{i}_{j}"
            valid = sorted(set(rc["player_ids"]) & set(cc["player_ids"]))
            grid[cell_key] = valid
            if len(valid) < min_answers:
                playable = False

    if playable:
        return {"row_categories": row_cats, "col_categories": col_cats, "grid": grid}
    return None


def generate_grid(categories, players, date):
    """Generate a playable 3x3 grid for the given date.

    Uses the date as a seed so the same date always produces the same grid.
    Tries multiple random draws until a playable grid is found (up to 1000).
    Falls back to a catch-all grid if nothing else works.
    """
    seed_str = f"college-grid-{date}"

    # First try normal generation
    for attempt in range(1000):
        # Prefer cells with 2+ answers; relax to 1 after 300 tries
        need = MIN_ANSWERS if attempt < 300 else 1
        result = _try_generate(categories, seed_str + f"-{attempt}", need)
        if result:
            return result

    # Fallback: use catch-all for everything
    catch_all_cats = [c for c in categories if c["type"] == "catch_all"]
    if catch_all_cats:
        cat = catch_all_cats[0]
        all_pids = sorted(cat["player_ids"])
        return {
            "row_categories": [cat, cat, cat],
            "col_categories": [cat, cat, cat],
            "grid": {
                "0_0": all_pids,
                "0_1": all_pids,
                "0_2": all_pids,
                "1_0": all_pids,
                "1_1": all_pids,
                "1_2": all_pids,
                "2_0": all_pids,
                "2_1": all_pids,
                "2_2": all_pids,
            },
        }

    return None


def write_manifest():
    """Write grids/index.json listing every grid date.

    GitHub Pages cannot list a directory, so the frontend reads this file
    to find the latest grid.
    """
    dates = sorted(f[:-5] for f in os.listdir(GRIDS_DIR)
                   if f.endswith(".json") and f != "index.json")
    with open(os.path.join(GRIDS_DIR, "index.json"), "w") as f:
        json.dump({"latest": dates[-1] if dates else None, "dates": dates}, f, indent=2)
    print(f"  [✓] Manifest updated ({len(dates)} grids)")


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
        write_manifest()

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
        print("[!] Failed to generate a grid even with fallback.")


if __name__ == "__main__":
    main()
