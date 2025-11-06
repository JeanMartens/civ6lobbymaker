"""
Voting and results calculation utilities
"""
import random
from typing import Dict, Any


def calculate_weighted_results(votes: Dict[str, Dict], categories: Dict[str, list]) -> Dict[str, Any]:
    """
    Calculate weighted random results from all player votes
    
    Args:
        votes: Dict of player_id -> {category: choice}
        categories: Dict of category -> [options]
    
    Returns:
        Dict of category -> {"selected": choice, "votes": {option: count}}
    """
    final_settings = {}
    
    for category in categories.keys():
        votes_count = {}
        
        # Count votes for this category
        for player_votes in votes.values():
            if category in player_votes:
                choice = player_votes[category]
                votes_count[choice] = votes_count.get(choice, 0) + 1
        
        # Weighted random selection
        if votes_count:
            choices = list(votes_count.keys())
            weights = list(votes_count.values())
            selected = random.choices(choices, weights=weights, k=1)[0]
            final_settings[category] = {
                "selected": selected,
                "votes": votes_count
            }
    
    return final_settings


def format_vote_results(weighted_results: Dict[str, Any]) -> str:
    """Format voting results as a readable string"""
    lines = ["## 🎲 Paramètres sélectionnés pour la partie\n"]
    
    for category, result_data in weighted_results.items():
        lines.append(f"**{category}**: {result_data['selected']}")
    
    return "\n".join(lines)


def format_vote_details(category: str, result_data: Dict, total_voters: int) -> str:
    """Format detailed vote breakdown for a category"""
    selected = result_data["selected"]
    votes_count = result_data["votes"]
    
    lines = [f"## {category}"]
    lines.append(f"**✅ Sélectionné**: {selected}\n")
    lines.append("**Détail des votes**:")
    
    # Sort by vote count
    sorted_votes = sorted(votes_count.items(), key=lambda x: x[1], reverse=True)
    for option, count in sorted_votes:
        percentage = (count / total_voters) * 100
        is_winner = "🏆" if option == selected else "  "
        lines.append(f"{is_winner} **{option}**: {count} vote(s) ({percentage:.0f}%)")
    
    return "\n".join(lines)
