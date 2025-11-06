"""
Game data model and basic operations
"""
import uuid
from typing import Dict, List, Optional


class Game:
    """Represents a Civilization VI game session"""
    
    def __init__(
        self,
        creator_id: int,
        max_bans: int = 2,
        civ_pool_size: int = 3,
        thread_id: Optional[int] = None
    ):
        self.id = str(uuid.uuid4())[:8]
        self.creator = creator_id
        self.players: List[int] = []
        self.votes: Dict[str, Dict] = {}
        self.bans: Dict[str, List[str]] = {}
        self.civ_selections: Dict[str, str] = {}
        self.civ_pools: Dict[str, List[str]] = {}
        self.max_bans = max_bans
        self.civ_pool_size = civ_pool_size
        self.voting_started = False
        self.banning_started = False
        self.selection_started = False
        self.results_channel_id: Optional[int] = None
        self.thread_id = thread_id
    
    def to_dict(self) -> Dict:
        """Convert game to dictionary for storage"""
        return {
            "id": self.id,
            "creator": self.creator,
            "players": self.players,
            "votes": self.votes,
            "bans": self.bans,
            "civ_selections": self.civ_selections,
            "civ_pools": self.civ_pools,
            "max_bans": self.max_bans,
            "civ_pool_size": self.civ_pool_size,
            "voting_started": self.voting_started,
            "banning_started": self.banning_started,
            "selection_started": self.selection_started,
            "results_channel_id": self.results_channel_id,
            "thread_id": self.thread_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Game':
        """Create game from dictionary"""
        game = cls.__new__(cls)
        game.id = data["id"]
        game.creator = data["creator"]
        game.players = data["players"]
        game.votes = data.get("votes", {})
        game.bans = data.get("bans", {})
        game.civ_selections = data.get("civ_selections", {})
        game.civ_pools = data.get("civ_pools", {})
        game.max_bans = data.get("max_bans", 2)
        game.civ_pool_size = data.get("civ_pool_size", 3)
        game.voting_started = data.get("voting_started", False)
        game.banning_started = data.get("banning_started", False)
        game.selection_started = data.get("selection_started", False)
        game.results_channel_id = data.get("results_channel_id")
        game.thread_id = data.get("thread_id")
        return game
    
    def add_player(self, player_id: int) -> bool:
        """Add a player to the game"""
        if player_id not in self.players:
            self.players.append(player_id)
            return True
        return False
    
    def is_player(self, player_id: int) -> bool:
        """Check if user is in the game"""
        return player_id in self.players
    
    def is_creator(self, player_id: int) -> bool:
        """Check if user is the game creator"""
        return player_id == self.creator
    
    def get_player_vote(self, player_id: int) -> Optional[Dict]:
        """Get a player's votes"""
        return self.votes.get(str(player_id))
    
    def set_player_vote(self, player_id: int, votes: Dict) -> None:
        """Set a player's votes"""
        self.votes[str(player_id)] = votes
    
    def get_player_bans(self, player_id: int) -> List[str]:
        """Get a player's bans"""
        return self.bans.get(str(player_id), [])
    
    def set_player_bans(self, player_id: int, bans: List[str]) -> None:
        """Set a player's bans"""
        self.bans[str(player_id)] = bans
    
    def get_player_selection(self, player_id: int) -> Optional[str]:
        """Get a player's civilization selection"""
        return self.civ_selections.get(str(player_id))
    
    def set_player_selection(self, player_id: int, civ: str) -> None:
        """Set a player's civilization selection"""
        self.civ_selections[str(player_id)] = civ
    
    def get_player_pool(self, player_id: int) -> List[str]:
        """Get a player's civilization pool"""
        return self.civ_pools.get(str(player_id), [])
    
    def all_voted(self, required_categories: int) -> bool:
        """Check if all players have completed voting"""
        for player_id in self.players:
            votes = self.get_player_vote(player_id)
            if not votes or len(votes) < required_categories:
                return False
        return True
    
    def all_banned(self) -> bool:
        """Check if all players have submitted bans"""
        for player_id in self.players:
            if str(player_id) not in self.bans:
                return False
        return True
    
    def all_selected(self) -> bool:
        """Check if all players have selected civilizations"""
        for player_id in self.players:
            if str(player_id) not in self.civ_selections:
                return False
        return True
    
    def get_all_bans(self) -> List[str]:
        """Get all banned civilizations (unique)"""
        all_bans = []
        for player_bans in self.bans.values():
            all_bans.extend(player_bans)
        return list(set(all_bans))
