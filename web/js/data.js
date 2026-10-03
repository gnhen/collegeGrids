/**
 * College Grid - Data Management
 * Handles loading and managing game data from the server
 */

class DataManager {
    constructor() {
        this.gridData = null;
        this.players = {};
        this.isLoading = false;
    }

    /**
     * Load the daily grid data
     */
    async loadGrid(date) {
        this.isLoading = true;
        try {
            const response = await fetch(`/data/grids/${date}.json`);
            if (!response.ok) {
                throw new Error(`Failed to load grid: ${response.status}`);
            }
            this.gridData = await response.json();
            console.log('Grid loaded:', this.gridData);
            return this.gridData;
        } catch (error) {
            console.error('Error loading grid:', error);
            throw error;
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Load player data
     */
    async loadPlayers() {
        try {
            const response = await fetch('/data/players.json');
            if (!response.ok) {
                throw new Error(`Failed to load players: ${response.status}`);
            }
            this.players = await response.json();
            console.log('Players loaded:', Object.keys(this.players).length, 'players');
            return this.players;
        } catch (error) {
            console.error('Error loading players:', error);
            throw error;
        }
    }

    /**
     * Get valid players for a specific cell
     */
    getValidPlayersForCell(rowIndex, colIndex) {
        if (!this.gridData) return [];
        const cellKey = `${rowIndex}_${colIndex}`;
        const playerIds = this.gridData.grid[cellKey] || [];
        return playerIds.map(id => this.players[id]).filter(Boolean);
    }

    /**
     * Check if a player is valid for a specific cell
     */
    isPlayerValidForCell(playerId, rowIndex, colIndex) {
        if (!this.gridData) return false;
        const cellKey = `${rowIndex}_${colIndex}`;
        const validPlayerIds = this.gridData.grid[cellKey] || [];
        return validPlayerIds.includes(playerId);
    }

    /**
     * Get category label for a cell
     */
    getCategoryLabel(rowIndex, colIndex, isRow = true) {
        if (!this.gridData) return '';
        const categories = isRow ? this.gridData.row_categories : this.gridData.col_categories;
        const category = categories[colIndex || rowIndex];
        if (!category) return '';
        
        switch (category.type) {
            case 'school':
                return category.value;
            case 'conference':
                return category.value;
            case 'season_stat':
                return `${category.threshold}+ ${category.stat_type} in ${category.season}`;
            case 'career_stat':
                return `${category.threshold}+ ${category.stat_type} career`;
            case 'award':
                return `${category.name} winner`;
            case 'transfer':
                return 'Transferred schools';
            default:
                return category.value || '';
        }
    }

    /**
     * Search players by name
     */
    searchPlayers(query) {
        if (!this.players || !query) return [];
        const results = [];
        const lowerQuery = query.toLowerCase();
        
        for (const [id, player] of Object.entries(this.players)) {
            if (player.name && player.name.toLowerCase().includes(lowerQuery)) {
                results.push({ id, ...player });
            }
        }
        
        return results.slice(0, 10); // Limit to 10 results
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DataManager;
}
