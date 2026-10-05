/**
 * College Grid - Game Logic
 * Handles game state, validation, and scoring.
 */

class GridGame {
    constructor() {
        this.dataManager = new DataManager();
        this.currentGuesses = {};   // cellKey -> player_id
        this.guessCount = 0;
        this.correctGuesses = 0;
        this.gameComplete = false;
        this.maxGuesses = 9;
        this.selectedCell = null;   // {row, col, cellKey}
    }

    async init(date) {
        try {
            const gridLoaded = await this.dataManager.loadGrid(date);
            if (!gridLoaded) {
                return false;
            }
            await this.dataManager.loadPlayers();
            this.renderGrid();
            this.updateStats();
            console.log('Game initialized');
            return true;
        } catch (error) {
            console.error('Error initializing game:', error);
            return false;
        }
    }

    renderGrid() {
        const columnHeaders = document.getElementById('columnHeaders');
        const rowLabels = document.getElementById('rowLabels');
        const gridBody = document.getElementById('gridBody');

        columnHeaders.innerHTML = '';
        rowLabels.innerHTML = '';
        gridBody.innerHTML = '';

        // Column headers (index 0..2 into col_categories)
        for (let j = 0; j < 3; j++) {
            const header = document.createElement('div');
            header.className = 'column-header';
            header.textContent = this.dataManager.getCategoryLabel(0, j, false);
            columnHeaders.appendChild(header);
        }

        // Row labels (index 0..2 into row_categories)
        for (let i = 0; i < 3; i++) {
            const label = document.createElement('div');
            label.className = 'row-label';
            label.textContent = this.dataManager.getCategoryLabel(i, 0, true);
            rowLabels.appendChild(label);
        }

        // Grid cells
        for (let row = 0; row < 3; row++) {
            for (let col = 0; col < 3; col++) {
                const cell = document.createElement('div');
                cell.className = 'grid-cell';
                cell.id = `cell-${row}-${col}`;

                const categoryLabel = document.createElement('div');
                categoryLabel.className = 'cell-label';
                categoryLabel.textContent =
                    this.dataManager.getCategoryLabel(row, 0, true) + ' + ' +
                    this.dataManager.getCategoryLabel(0, col, false);

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

                cell.addEventListener('click', () => {
                    this.selectCell(row, col);
                });

                gridBody.appendChild(cell);
            }
        }
    }

    selectCell(rowIndex, colIndex) {
        const cellKey = `${rowIndex}_${colIndex}`;

        if (this.currentGuesses[cellKey]) {
            return;
        }

        document.querySelectorAll('.grid-cell').forEach(c => {
            c.style.borderColor = '';
            c.style.boxShadow = '';
        });

        const selectedCell = document.getElementById(`cell-${rowIndex}-${colIndex}`);
        selectedCell.style.borderColor = '#3b82f6';
        selectedCell.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.3)';

        this.selectedCell = { rowIndex, colIndex, cellKey };
    }

    async makeGuess(playerId, rowIndex, colIndex) {
        if (this.gameComplete) return;
        if (this.guessCount >= this.maxGuesses) return;

        const cellKey = `${rowIndex}_${colIndex}`;

        if (Object.values(this.currentGuesses).includes(playerId)) {
            alert('You already guessed this player!');
            return;
        }

        if (this.currentGuesses[cellKey]) {
            alert('This cell is already filled!');
            return;
        }

        this.currentGuesses[cellKey] = playerId;
        this.guessCount++;

        const isValid = this.dataManager.isPlayerValidForCell(playerId, rowIndex, colIndex);
        const player = this.dataManager.players[playerId];

        this.updateCell(rowIndex, colIndex, player, isValid);

        if (isValid) {
            this.correctGuesses++;
        }
        this.updateStats();

        if (this.guessCount >= this.maxGuesses) {
            this.gameComplete = true;
            this.showResults();
        }
    }

    updateCell(rowIndex, colIndex, player, isValid) {
        const cell = document.getElementById(`cell-${rowIndex}-${colIndex}`);
        const answer = document.getElementById(`answer-${rowIndex}-${colIndex}`);
        const status = document.getElementById(`status-${rowIndex}-${colIndex}`);

        if (player) {
            answer.textContent = escapeHtml(player.name);
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

    updateStats() {
        document.getElementById('guessCount').textContent = `${this.guessCount}/${this.maxGuesses}`;
        document.getElementById('correctCount').textContent = this.correctGuesses;
        document.getElementById('score').textContent = this.correctGuesses;
    }

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

    reset() {
        this.currentGuesses = {};
        this.guessCount = 0;
        this.correctGuesses = 0;
        this.gameComplete = false;
        this.selectedCell = null;
        this.renderGrid();
        this.updateStats();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}