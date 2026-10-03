/**
 * College Grid - Game Logic
 * Handles game state, validation, and scoring
 */

class GridGame {
    constructor() {
        this.dataManager = new DataManager();
        this.currentGuesses = [];
        this.guessCount = 0;
        this.correctGuesses = 0;
        this.gameComplete = false;
        this.maxGuesses = 9;
    }

    /**
     * Initialize the game
     */
    async init(date) {
        try {
            await this.dataManager.loadGrid(date);
            await this.dataManager.loadPlayers();
            this.renderGrid();
            this.updateStats();
            console.log('Game initialized');
        } catch (error) {
            console.error('Error initializing game:', error);
            alert('Failed to load game data. Please try again later.');
        }
    }

    /**
     * Render the grid
     */
    renderGrid() {
        const columnHeaders = document.getElementById('columnHeaders');
        const rowLabels = document.getElementById('rowLabels');
        const gridBody = document.getElementById('gridBody');
        
        // Clear existing content
        columnHeaders.innerHTML = '';
        rowLabels.innerHTML = '';
        gridBody.innerHTML = '';
        
        // Render column headers
        for (let i = 0; i < 3; i++) {
            const header = document.createElement('div');
            header.className = 'column-header';
            header.textContent = this.dataManager.getCategoryLabel(i, i, false);
            columnHeaders.appendChild(header);
        }
        
        // Render row labels
        for (let i = 0; i < 3; i++) {
            const label = document.createElement('div');
            label.className = 'row-label';
            label.textContent = this.dataManager.getCategoryLabel(i, i, true);
            rowLabels.appendChild(label);
        }
        
        // Render grid cells
        for (let row = 0; row < 3; row++) {
            for (let col = 0; col < 3; col++) {
                const cell = document.createElement('div');
                cell.className = 'grid-cell';
                cell.id = `cell-${row}-${col}`;
                
                const categoryLabel = document.createElement('div');
                categoryLabel.className = 'cell-label';
                categoryLabel.textContent = this.dataManager.getCategoryLabel(row, col, true) + ' + ' + 
                                          this.dataManager.getCategoryLabel(row, col, false);
                
                const answer = document.createElement('div');
                answer.className = 'cell-answer';
                answer.id = `answer-${row}-${col}`;
                answer.textContent = '?';
                
                const status = document.createElement('div');
                status.className = 'cell-status';
                status.id = `status-${row}-${col}`;
                status.textContent = '';
                
                cell.appendChild(categoryLabel);
                cell.appendChild(answer);
                cell.appendChild(status);
                gridBody.appendChild(cell);
            }
        }
    }

    /**
     * Make a guess
     */
    async makeGuess(playerId, rowIndex, colIndex) {
        if (this.gameComplete) return;
        if (this.guessCount >= this.maxGuesses) return;
        
        // Check if player is already guessed
        if (this.currentGuesses.includes(playerId)) {
            alert('You already guessed this player!');
            return;
        }
        
        // Add guess
        this.currentGuesses.push(playerId);
        this.guessCount++;
        
        // Check if correct
        const isValid = this.dataManager.isPlayerValidForCell(playerId, rowIndex, colIndex);
        const player = this.dataManager.players[playerId];
        
        // Update cell display
        this.updateCell(rowIndex, colIndex, player, isValid);
        
        // Update stats
        if (isValid) {
            this.correctGuesses++;
        }
        this.updateStats();
        
        // Check if game is complete
        if (this.guessCount >= this.maxGuesses) {
            this.gameComplete = true;
            this.showResults();
        }
    }

    /**
     * Update cell display
     */
    updateCell(rowIndex, colIndex, player, isValid) {
        const cell = document.getElementById(`cell-${rowIndex}-${colIndex}`);
        const answer = document.getElementById(`answer-${rowIndex}-${colIndex}`);
        const status = document.getElementById(`status-${rowIndex}-${colIndex}`);
        
        if (player) {
            answer.textContent = player.name;
            cell.classList.add(isValid ? 'correct' : 'incorrect');
            status.textContent = isValid ? '✓ Correct!' : '✗ Incorrect';
            status.classList.add(isValid ? 'correct' : 'incorrect');
        } else {
            answer.textContent = 'Unknown';
            cell.classList.add('incorrect');
            status.textContent = '✗ Invalid player';
            status.classList.add('incorrect');
        }
    }

    /**
     * Update stats display
     */
    updateStats() {
        document.getElementById('guessCount').textContent = `${this.guessCount}/${this.maxGuesses}`;
        document.getElementById('correctCount').textContent = this.correctGuesses;
        document.getElementById('score').textContent = this.correctGuesses;
    }

    /**
     * Show final results
     */
    showResults() {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'results-section';
        resultDiv.innerHTML = `
            <h2>Game Complete!</h2>
            <p>You got ${this.correctGuesses} out of ${this.guessCount} correct!</p>
            <button onclick="location.reload()">Play Again</button>
        `;
        document.querySelector('main').appendChild(resultDiv);
    }

    /**
     * Reset the game
     */
    reset() {
        this.currentGuesses = [];
        this.guessCount = 0;
        this.correctGuesses = 0;
        this.gameComplete = false;
        this.renderGrid();
        this.updateStats();
    }
}
