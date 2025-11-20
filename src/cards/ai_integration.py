"""
Card AI Integration

Converts Gemini AI card analysis results into UnifiedCard objects
and provides helper functions for card detection and organization.
"""

from typing import Dict, Any, Optional
from .unified_card import UnifiedCard
from .card_manager import CardCollectionManager


def create_card_from_ai_analysis(
    ai_result: Dict[str, Any],
    user_id: int,
    photos: Optional[list] = None,
    storage_location: Optional[str] = None
) -> Optional[UnifiedCard]:
    """
    Convert Gemini AI card analysis result into a UnifiedCard object.

    Args:
        ai_result: Result from GeminiClassifier.analyze_card()
        user_id: User ID
        photos: Optional list of photo paths
        storage_location: Optional storage location

    Returns:
        UnifiedCard object or None if not a valid card
    """
    if not ai_result.get('is_card'):
        return None

    # Determine card type from AI result
    card_type = ai_result.get('card_type', 'unknown')

    # Build card name/title
    if ai_result.get('player_name'):
        # Sports card
        title = ai_result.get('player_name', '')
        if ai_result.get('series'):
            title += f" {ai_result['series']}"
        if ai_result.get('is_rookie_card'):
            title += " RC"
    else:
        # TCG card
        title = ai_result.get('card_name', 'Unknown Card')

    # Map card_type to organization mode
    organization_mode = 'by_set'  # Default
    if card_type.startswith('sports_'):
        organization_mode = 'by_year' if ai_result.get('year') else 'by_sport'

    # Create UnifiedCard
    card = UnifiedCard(
        card_type=card_type,
        title=title,
        user_id=user_id,
        card_number=ai_result.get('card_number'),
        quantity=1,
        organization_mode=organization_mode,

        # TCG fields
        game_name=_get_game_name(card_type),
        set_name=ai_result.get('set_name'),
        set_code=ai_result.get('set_code'),
        rarity=ai_result.get('rarity'),

        # Sports fields
        sport=_get_sport(card_type),
        year=ai_result.get('year'),
        brand=ai_result.get('brand'),
        series=ai_result.get('series'),
        player_name=ai_result.get('player_name'),
        is_rookie_card=ai_result.get('is_rookie_card', False),
        parallel_color=ai_result.get('parallel'),

        # Grading
        grading_company=ai_result.get('grading_company') if ai_result.get('is_graded') else None,
        grading_score=ai_result.get('grading_score') if ai_result.get('is_graded') else None,

        # Value
        estimated_value=_calculate_avg_value(
            ai_result.get('estimated_value_low'),
            ai_result.get('estimated_value_high')
        ),

        # Location
        storage_location=storage_location,
        photos=photos or [],

        # AI metadata
        ai_identified=True,
        ai_confidence=ai_result.get('confidence', 0.0)
    )

    return card


def _get_game_name(card_type: str) -> Optional[str]:
    """Get game name from card type"""
    game_map = {
        'pokemon': 'Pokemon',
        'mtg': 'Magic: The Gathering',
        'yugioh': 'Yu-Gi-Oh!',
        'onepiece': 'One Piece',
        'dragonball': 'Dragon Ball',
    }
    return game_map.get(card_type)


def _get_sport(card_type: str) -> Optional[str]:
    """Get sport from card type"""
    if card_type.startswith('sports_'):
        sport_code = card_type.replace('sports_', '').upper()
        return sport_code
    return None


def _calculate_avg_value(low: Optional[float], high: Optional[float]) -> Optional[float]:
    """Calculate average value from low/high range"""
    if low is not None and high is not None:
        return (low + high) / 2
    elif low is not None:
        return low
    elif high is not None:
        return high
    return None


def is_likely_card(item_analysis: Dict[str, Any]) -> bool:
    """
    Check if item analysis suggests this might be a card.

    Args:
        item_analysis: Result from GeminiClassifier.analyze_item()

    Returns:
        True if item seems like a card
    """
    category = item_analysis.get('category', '').lower()
    item_name = item_analysis.get('item_name', '').lower()
    franchise = item_analysis.get('franchise', '').lower()
    keywords = [k.lower() for k in item_analysis.get('detected_keywords', [])]

    # Check for card keywords
    card_keywords = [
        'card', 'trading card', 'pokemon', 'mtg', 'magic', 'yugioh',
        'baseball', 'football', 'basketball', 'hockey', 'soccer',
        'rookie', 'autograph', 'graded', 'psa', 'bgscgc'
    ]

    # Check if category is cards
    if 'card' in category:
        return True

    # Check if name contains card-related terms
    if any(kw in item_name for kw in card_keywords):
        return True

    # Check if it's a sports/TCG franchise
    card_franchises = ['pokemon', 'mtg', 'magic', 'yugioh', 'mlb', 'nfl', 'nba', 'nhl']
    if any(f in franchise for f in card_franchises):
        return True

    # Check keywords
    if any(kw in keywords for kw in card_keywords):
        return True

    return False


def add_card_to_collection(
    ai_result: Dict[str, Any],
    user_id: int,
    photos: Optional[list] = None,
    storage_location: Optional[str] = None
) -> Optional[int]:
    """
    Convenience function to add a card directly to collection from AI analysis.

    Args:
        ai_result: Result from GeminiClassifier.analyze_card()
        user_id: User ID
        photos: Optional list of photo paths
        storage_location: Optional storage location

    Returns:
        Card ID or None if failed
    """
    card = create_card_from_ai_analysis(ai_result, user_id, photos, storage_location)
    if not card:
        return None

    manager = CardCollectionManager()
    card_id = manager.add_card(card)
    return card_id
