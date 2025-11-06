"""
Civilization-related utility functions
"""
import random
from typing import List, Tuple
from core.configs import CIV_EMOJI_CONFIG, LEADERS


def get_available_civs(banned_civs: List[str]) -> List[str]:
    """Get list of civilizations that aren't banned (just names)"""
    return [civ for civ in LEADERS if civ not in banned_civs]


def get_available_civs_with_emoji(banned_civs: List[str]) -> List[Tuple[str, str]]:
    """Get list of civilizations that aren't banned (with emojis)"""
    return [
        (CIV_EMOJI_CONFIG.get(civ, ""), civ) 
        for civ in LEADERS 
        if civ not in banned_civs
    ]


def assign_civ_pools(
    available_civs: List[str],
    num_players: int,
    pool_size: int
) -> List[List[str]]:
    """
    Assign random unique civilization pools to players
    
    Returns list of pools, or None if not enough civs available
    """
    total_needed = num_players * pool_size
    
    if len(available_civs) < total_needed:
        return None
    
    # Shuffle and split
    shuffled = available_civs.copy()
    random.shuffle(shuffled)
    
    pools = []
    for i in range(num_players):
        start_idx = i * pool_size
        end_idx = start_idx + pool_size
        pools.append(shuffled[start_idx:end_idx])
    
    return pools


def parse_emoji_from_text(text: str) -> List[str]:
    """Extract emojis from text input"""
    import re
    
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002500-\U00002BEF"  # chinese char
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U00002600-\U000027BF"  # Miscellaneous Symbols
        "\U0001F650-\U0001F67F"  # Ornamental Dingbats
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "]+", 
        flags=re.UNICODE
    )
    
    found_emojis = emoji_pattern.findall(text)
    
    # Check for multi-character emojis
    if "🕵️‍♀️" in text:
        found_emojis.append("🕵️‍♀️")
    
    return found_emojis


def emoji_to_civ(emoji: str) -> List[str]:
    """Get civilization(s) that match an emoji"""
    matching_civs = []
    for civ, civ_emoji in CIV_EMOJI_CONFIG.items():
        if civ_emoji == emoji:
            matching_civs.append(civ)
    return matching_civs


def emojis_to_civs(emojis: List[str]) -> Tuple[List[str], List[str], List[Tuple[str, List[str]]]]:
    """
    Convert list of emojis to civilizations
    
    Returns:
        - selected_civs: Unique civs found
        - not_found: Emojis that didn't match any civ
        - duplicates: Emojis that matched multiple civs (emoji, [civs])
    """
    selected_civs = []
    not_found = []
    duplicates = []
    
    for emoji in emojis:
        civs = emoji_to_civ(emoji)
        
        if not civs:
            not_found.append(emoji)
        elif len(civs) == 1:
            if civs[0] not in selected_civs:
                selected_civs.append(civs[0])
        else:
            duplicates.append((emoji, civs))
            # Add all civs with duplicate emoji
            for civ in civs:
                if civ not in selected_civs:
                    selected_civs.append(civ)
    
    return selected_civs, not_found, duplicates
