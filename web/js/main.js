/**
 * College Grid - Main Application
 * Initializes the game and handles user interaction
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Get today's date
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0];
    
    // Display current date
    document.getElementById('currentDate').textContent = today.toLocaleDateString('en-US', {
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
            div.innerHTML = `
                <div class="player-name">${result.name}</div>
                <div class="player-school">${result.school || 'Unknown School'}</div>
            `;
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
        
        // For now, just use the first result
        // In a real implementation, you'd want to match the input to the correct player
        const player = results[0];
        
        // Make a guess for the first empty cell
        for (let row = 0; row < 3; row++) {
            for (let col = 0; col < 3; col++) {
                const cell = document.getElementById(`cell-${row}-${col}`);
                if (!cell.classList.contains('correct') && !cell.classList.contains('incorrect')) {
                    game.makeGuess(player.id, row, col);
                    playerInput.value = '';
                    return;
                }
            }
        }
        
        alert('All cells are filled!');
    });
    
    // Handle Enter key
    playerInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            guessBtn.click();
        }
    });
});
