# College Grid

A daily college football trivia game inspired by Immaculate Grid, built as a static GitHub Pages site with ESPN API data.

## Features

- Daily 3x3 grid of college football trivia
- Player-school, conference, and stat-based categories
- Real-time data from ESPN College Football API
- Static site deployment (no backend required)
- Mobile-responsive design

## Architecture

### Data Pipeline
1. **Scraper** (`scraper/`): Crawls ESPN API for box scores, awards, and player data
2. **GitHub Actions** (`.github/workflows/`): Automated daily data updates
3. **Static Data** (`data/`): Processed JSON files for the frontend
4. **Web App** (`web/`): Vanilla HTML/CSS/JS frontend

### ESPN API Endpoints Used
- Box scores: `site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={id}`
- Awards: `sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/awards`
- Scoreboard: `site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates={date}`

## Setup

### Local Development
```bash
# Clone the repository
git clone https://github.com/yourusername/collegeGrids.git
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
2. Set source to "GitHub Actions"
3. The nightly ingest workflow will automatically update data

## Game Rules

- 3x3 grid of trivia categories
- Pick a player who fits both the row and column category
- 9 guesses total
- Lower score is better (based on player rarity)

## Category Types

- **School**: Player attended/played for this school
- **Conference**: Player played in this conference
- **Season Stat**: Player achieved this stat in a specific season
- **Career Stat**: Player achieved this stat over their career
- **Award**: Winner of this award
- **Transfer**: Player transferred between schools

## Data Sources

- ESPN College Football API (primary)
- Player statistics from box scores
- Award winners from core API
- Conference and school data from team records

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Inspired by Immaculate Grid (Sports Reference)
- Data provided by ESPN College Football API
- Built with vanilla HTML, CSS, and JavaScript
