#!/usr/bin/env python3
"""
Test script to verify the scraper works correctly.
"""

import json
import os
import sys
import urllib.request

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_scoreboard():
    """Test scoreboard endpoint."""
    print("Testing scoreboard endpoint...")
    url = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=20241005&limit=5&groups=80"
    
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                events = data.get('events', [])
                print(f"  ✓ Found {len(events)} events")
                return True
            else:
                print(f"  ✗ HTTP {response.status}")
                return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_box_score():
    """Test box score endpoint."""
    print("Testing box score endpoint...")
    url = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event=401752859"
    
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                boxscore = data.get('boxscore', {})
                players = boxscore.get('players', [])
                print(f"  ✓ Found {len(players)} teams with player data")
                return True
            else:
                print(f"  ✗ HTTP {response.status}")
                return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_awards():
    """Test awards endpoint."""
    print("Testing awards endpoint...")
    url = "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2025/awards?limit=5"
    
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                items = data.get('items', [])
                print(f"  ✓ Found {len(items)} award categories")
                return True
            else:
                print(f"  ✗ HTTP {response.status}")
                return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Run all tests."""
    print("Running scraper tests...\n")
    
    results = []
    results.append(("Scoreboard", test_scoreboard()))
    results.append(("Box Score", test_box_score()))
    results.append(("Awards", test_awards()))
    
    print("\n" + "="*50)
    print("Test Results:")
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {name}: {status}")
    
    all_passed = all(result for _, result in results)
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
