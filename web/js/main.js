/**
 * College Grid - Main Application
 * Initializes the game and handles user interaction.
 *
 * Uses Eastern time for the date so the grid matches the daily schedule.
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Get today's date in Eastern time (not UTC)
    const now = new Date();
    const eastern = now.toLocaleString('en-US', { timeZone: 'America/New_York' });
    const easternDate = new Date(eastern);
    const dateStr = easternDate.toISOString().split('T')[0];

    // Display current date
    document.getElementById('currentDate').textContent = easternDate.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    // Initialize game
    const game = new GridGame();
    await game.init(dateStr);

    // Setup input handling
    const playerInput = document.getElementById('playerInput');
    const guessBtn = document.getElementById('guessBtn');
    const autocompleteResults = document.getElementById('autocompleteResults');

    // Autocomplete functionality
    playerInput.addEventListener('input', async (e) => {
        const query = e.target.value.trim();

        if (query.length < 2) {
            autocompleteResults.style.display = 'none';
            return;
        }

        const results = game.dataManager.searchPlayers(query);

        if (results.length === 0) {
            autocompleteResults.style.display = 'none';
            return;
        }

        autocompleteResults.innerHTML = '';
        autocompleteResults.style.display = 'block';

        results.forEach(result => {
            const div = document.createElement('div');
            div.className = 'autocomplete-result';

            // Use textContent to avoid XSS
            const nameEl = document.createElement('div');
            nameEl.className = 'player-name';
            nameEl.textContent = result.name;

            const schoolEl = document.createElement('div');
            schoolEl.className = 'player-school';
            schoolEl.textContent = result.school || 'Unknown School';

            div.appendChild(nameEl);
            div.appendChild(schoolEl);

            div.addEventListener('click', () => {
                playerInput.value = result.name;
                autocompleteResults.style.display = 'none';
            });
            autocompleteResults.appendChild(div);
        });
    });

    // Hide autocomplete when clicking outside
    document.addEventListener('click', (e) => {
        if (!playerInput.contains(e.target) && !autocompleteResults.contains(e.target)) {
            autocompleteResults.style.display = 'none';
        }
    });

    // Handle guess button click
    guessBtn.addEventListener('click', () => {
        const playerName = playerInput.value.trim();

        if (!playerName) {
            alert('Please enter a player name');
            return;
        }

        // Find the player
        const results = game.dataManager.searchPlayers(playerName);
        if (results.length === 0) {
            alert('Player not found');
            return;
        }

        const player = results[0];

        // If a cell is selected, guess there; otherwise find first empty cell
        let targetRow = -1, targetCol = -1;
        if (game.selectedCell) {
            targetRow = game.selectedCell.rowIndex;
            targetCol = game.selectedCell.colIndex;
        } else {
            // Find first empty cell
            for (let r = 0; r < 3; r++) {
                for (let c = 0; c < 3; c++) {
                    const cellKey = `${r}_${c}`;
                    if (!game.currentGuesses[cellKey]) {
                        targetRow = r;
                        targetCol = c;
                        break;
                    }
                }
                if (targetRow >= 0) break;
            }
        }

        if (targetRow >= 0 && targetCol >= 0) {
            game.makeGuess(player.id, targetRow, targetCol);
            playerInput.value = '';
        } else {
            alert('All cells are filled!');
        }
    });

    // Handle Enter key
    playerInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            guessBtn.click();
        }
    });
});