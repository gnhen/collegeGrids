/**
 * College Grid - Data Management
 * Handles loading and managing game data from the server.
 *
 * Uses relative paths so the site works on both localhost and
 * user.github.io/collegeGrids/ deployments.
 */

class DataManager {
    constructor() {
        this.gridData = null;
        this.players = {};
        this.isLoading = false;
    }

    async loadGrid(date) {
        this.isLoading = true;
        try {
            const response = await fetch(`./data/grids/${date}.json`);
            if (!response.ok) {
                console.warn(`Grid not found for ${date}: ${response.status}`);
                return null;
            }
            this.gridData = await response.json();
            console.log('Grid loaded:', this.gridData);
            return this.gridData;
        } catch (error) {
            console.error('Error loading grid:', error);
            return null;
        } finally {
            this.isLoading = false;
        }
    }

    async loadPlayers() {
        try {
            const response = await fetch('./data/players.json');
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

    getValidPlayersForCell(rowIndex, colIndex) {
        if (!this.gridData) return [];
        const cellKey = `${rowIndex}_${colIndex}`;
        const playerIds = this.gridData.grid[cellKey] || [];
        return playerIds.map(id => this.players[id]).filter(Boolean);
    }

    isPlayerValidForCell(playerId, rowIndex, colIndex) {
        if (!this.gridData) return false;
        const cellKey = `${rowIndex}_${colIndex}`;
        const validPlayerIds = this.gridData.grid[cellKey] || [];
        return validPlayerIds.includes(playerId);
    }

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
                return `${category.threshold}+ ${category.stat_type}`;
            case 'award':
                return category.name;
            case 'transfer':
                return 'Transfer';
            case 'catch_all':
                return category.value || 'Any player';
            default:
                return category.value || '';
        }
    }

    searchPlayers(query) {
        if (!this.players || !query) return [];
        const results = [];
        const lowerQuery = query.toLowerCase();

        for (const [id, player] of Object.entries(this.players)) {
            if (player.name && player.name.toLowerCase().includes(lowerQuery)) {
                results.push({ id, ...player });
            }
        }

        return results.slice(0, 10);
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DataManager;
}