# Civilization VI Discord Bot - Ban System Implementation

## Overview
This Discord bot manages Civilization VI game settings voting and civilization banning for multiplayer games. The ban system has been integrated to allow players to ban civilizations after the game settings have been determined.

## Features Added

### 1. Civilization Ban Phase
- After all players complete voting on game settings, the ban phase automatically starts
- Each player receives the final game settings along with their ban interface
- Players can ban up to X civilizations (configurable per game, default is 2)

### 2. Ban Interface
- **Multi-page selection**: Since Discord limits select menus to 25 options and we have 48 civilizations, the ban interface uses pagination
- **Clear selection tracking**: Shows which civs are currently selected
- **Validation**: Ensures players don't exceed the maximum ban limit

### 3. Commands Updated

#### `/create [max_bans]`
- Now accepts an optional `max_bans` parameter (0-10, default: 2)
- Sets how many civilizations each player can ban

#### `/progress [game_id]`
- Shows both voting AND ban progress
- Displays completion status for each phase

#### `/results [game_id]`
- Shows final results including:
  - Selected game settings
  - All banned civilizations (and who banned them)
  - List of available civilizations for the game

#### `/force_bans [game_id]` (Admin only)
- Forces the ban phase to start even if not all votes are complete
- Useful for testing or if a player is unavailable

## Game Flow

1. **Game Creation**: Host creates game with `/create [max_bans]`
2. **Players Join**: Players click "Join" button
3. **Voting Phase**: Host starts votes, players receive DM with settings choices
4. **Settings Revealed**: Once all votes are in, settings are calculated and shown
5. **Ban Phase**: Players receive DM with ban interface and game settings
6. **Final Results**: Once all bans are submitted, final thread shows:
   - Game settings
   - Banned civilizations
   - Available civilizations

## File Structure

```
core/
├── game_manager.py     # Main game logic with ban system
├── storage.py          # JSON storage for game data
└── commands.py         # Discord commands

data/
└── games.json          # Persistent game data storage
```

## Key Components

### BanView Class
- Handles the civilization selection interface
- Supports pagination for 48 civilizations
- Tracks selected bans and enforces limits

### GameManager Updates
- `create_game()`: Now stores max_bans parameter
- `check_all_votes_complete()`: Triggers ban phase after voting
- `check_all_bans_complete()`: Creates final results after banning
- `get_ban_progress()`: Tracks ban completion status
- `get_available_civs()`: Returns non-banned civilizations

## Installation

1. Place all files in their respective directories:
   - `game_manager.py` → `core/game_manager.py`
   - `storage.py` → `core/storage.py`
   - `commands.py` → `cogs/commands.py`

2. Ensure the bot has the following permissions:
   - Send Messages
   - Create Public Threads
   - Send Messages in Threads
   - Use Slash Commands
   - Send Direct Messages

3. The storage directory (`data/`) will be created automatically

## Configuration

### Adjusting Ban Limits
- Default: 2 bans per player
- Can be set per game: `/create max_bans:5`
- Maximum: 10 bans per player

### Modifying Civilization List
Edit the `LEADERS` list in `game_manager.py` to add/remove civilizations.

## Error Handling

- Players who have DMs disabled will be listed when votes/bans are sent
- If a player doesn't complete their bans, the game can still proceed
- Admin can force progression with `/force_bans` if needed

## Data Persistence

Game data is stored in JSON format including:
- Game ID and creator
- Player list
- All votes and bans
- Game state flags
- Results channel reference

This ensures games can survive bot restarts.
>>>>>>> master
