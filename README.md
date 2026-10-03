# College Grid

A daily college football trivia game inspired by Immaculate Grid, built as a static GitHub Pages site with ESPN API data.

## Features

- **Daily Grid**: A new accurate grid generated every day at 12 AM EST
- **Real Data**: Powered by ESPN College Football API with live player statistics
- **Player-to-School Tracking**: Accurate "played for" cells using stable athlete IDs
- **Award Categories**: Includes Heisman, Davey O'Brien, Doak Walker, and more
- **Static Site**: No backend required - pure HTML/CSS/JS with GitHub Pages
- **Mobile Responsive**: Works on all devices

## How It Works

### Daily Grid Generation
1. **GitHub Actions** runs daily at 12 AM EST (5 AM UTC)
2. **Scraper** crawls ESPN box scores from the last 30 days
3. **Player Database** is built from box score data
4. **Grid Generator** creates a playable 3x3 grid with real data
5. **Static Files** are committed and pushed to the repository
6. **GitHub Pages** serves the latest grid to users

### Data Sources
- **Box Scores**: `site.api.espn.com/apis/site/v2/sports/football/college-football/summary`
- **Awards**: `sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/awards`
- **Scoreboard**: `site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard`

### Key Technical Features
- Athlete IDs are stable across transfers (critical for "played for" cells)
- Box scores contain detailed player statistics (passing, rushing, receiving, defensive)
- Awards endpoint returns Heisman, Davey O'Brien, Doak Walker, and 28+ other awards
- All endpoints work without API keys
- Resumable crawling with checkpoint system

## Game Rules

- 3x3 grid of trivia categories
- Pick a player who fits both the row and column category
- 9 guesses total
- Lower score is better (based on player rarity)
- Players can be active or retired

## Category Types

- **School**: Player attended/played for this school
- **Conference**: Player played in this conference
- **Season Stat**: Player achieved this stat in a specific season (e.g., 1000+ rushing yards)
- **Career Stat**: Player achieved this stat over their career
- **Award**: Winner of this award (Heisman, etc.)
- **Transfer**: Player transferred between schools

## Setup

### Local Development
```bash
# Clone the repository
git clone https://github.com/gnhen/collegeGrids.git
cd collegeGrids

# Run the scraper
cd scraper
python ingest_boxscores.py 20240907 20241005
python fetch_awards.py 2024
python generate_grids.py 2024-10-05

# Start a local server
cd ../web
python -m http.server 8080
```

### GitHub Pages Deployment
1. Enable GitHub Pages in repository settings
2. Set source to "GitHub Actions" or "master branch"
3. The daily_grid.yml workflow will automatically update data every day at 12 AM EST

## Architecture

### Data Flow
```
ESPN API → Scraper → Processed JSON → GitHub Actions → GitHub Pages → User
```

### Components
- **scraper/**: Python scripts for data ingestion and grid generation
- **web/**: Static HTML/CSS/JS frontend
- **.github/workflows/**: Automated daily grid generation
- **data/**: Processed player data and daily grids

## Project Structure

```
collegeGrids/
├── .github/workflows/daily_grid.yml  # Daily grid generation
├── scraper/
│   ├── ingest_boxscores.py           # ESPN box score crawler
│   ├── fetch_awards.py               # Award winner fetcher
│   ├── generate_grids.py             # Grid generator
│   ├── categories.json               # Category definitions
│   └── requirements.txt              # Python dependencies
├── web/
│   ├── index.html                    # Main game interface
│   ├── css/style.css                 # Responsive styling
│   ├── js/
│   │   ├── data.js                   # Data management
│   │   ├── game.js                   # Game logic
│   │   └── main.js                   # App initialization
│   └── data/
│       ├── players.json              # Player database
│       └── grids/                    # Daily grids
├── README.md                         # This file
└── .gitignore                        # Git ignore rules
```

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Inspired by Immaculate Grid (Sports Reference)
- Data provided by ESPN College Football API
- Built with vanilla HTML, CSS, and JavaScript
