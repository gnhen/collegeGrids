#!/usr/bin/env python3
"""
College Grid Awards Fetcher - Fetches seasonal award winners from ESPN API.

Usage:
    python fetch_awards.py [year]
    
    Example:
    python fetch_awards.py 2025
"""

import json
import os
import sys
import time
import urllib.request
import datetime

# Configuration
BASE_URL = "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football"
AWARDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "awards")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def ensure_dirs():
    """Create necessary directories if they don't exist."""
    os.makedirs(AWARDS_DIR, exist_ok=True)

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
        except Exception as e:
            print(f"  [!] Error fetching {url}: {e}")
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    return None

def fetch_awards(year):
    """Fetch all awards for a specific year."""
    print(f"--- Fetching Awards for {year} ---")
    
    awards_url = f"{BASE_URL}/seasons/{year}/awards?limit=100"
    awards_data = fetch_json(awards_url)
    
    if not awards_data:
        print(f"  [!] Failed to fetch awards for {year}")
        return {}
    
    items = awards_data.get('items', [])
    print(f"  Found {len(items)} award categories.")
    
    awards = {}
    for item in items:
        award_id = item.get('id')
        award_name = item.get('name') or item.get('displayName', 'Unknown')
        
        # Fetch detailed award info
        award_url = item.get('$ref')
        if not award_url:
            continue
            
        award_details = fetch_json(award_url)
        if not award_details:
            continue
        
        # Extract winners
        winners = award_details.get('winners', [])
        award_info = {
            "id": award_id,
            "name": award_name,
            "year": year,
            "winners": []
        }
        
        for winner in winners:
            athlete_ref = winner.get('athlete', {}).get('$ref', '')
            team_ref = winner.get('team', {}).get('$ref', '')
            
            # Extract athlete ID from ref
            athlete_id = None
            if athlete_ref:
                parts = athlete_ref.split('/')
                if len(parts) >= 2:
                    athlete_id = parts[-1].split('?')[0]
            
            # Extract team ID from ref
            team_id = None
            if team_ref:
                parts = team_ref.split('/')
                if len(parts) >= 2:
                    team_id = parts[-1].split('?')[0]
            
            award_info["winners"].append({
                "athlete_id": athlete_id,
                "team_id": team_id,
                "athlete_name": winner.get('athlete', {}).get('displayName', ''),
                "team_name": winner.get('team', {}).get('displayName', '')
            })
        
        awards[award_name] = award_info
    
    return awards

def save_awards(year, awards):
    """Save awards data to a JSON file."""
    filepath = os.path.join(AWARDS_DIR, f"{year}_awards.json")
    with open(filepath, 'w') as f:
        json.dump(awards, f, indent=2)
    print(f"  [✓] Saved awards for {year} to {filepath}")

def main():
    """Main function to run the awards fetcher."""
    ensure_dirs()
    
    # Parse command line arguments
    if len(sys.argv) >= 2:
        year = int(sys.argv[1])
    else:
        # Default: current year
        year = datetime.datetime.now().year
    
    print(f"Starting awards fetcher for year: {year}")
    
    awards = fetch_awards(year)
    
    if awards:
        save_awards(year, awards)
        print(f"\n[✓] Awards fetcher complete. Processed {len(awards)} award categories.")
    else:
        print(f"\n[!] No awards data found for {year}.")

if __name__ == "__main__":
    main()
