"""Card Collection Organization System

This module provides a unified system for organizing trading cards and sports cards.
Supports: Pokémon, MTG, Yu-Gi-Oh, NFL, NBA, MLB, NHL, and more.

Features:
- AI-powered card identification (via Gemini Vision)
- Automatic organization by set, year, sport, brand, etc.
- CSV import/export
- Grading support (PSA, BGS, CGC)
- Value tracking
- Storage integration
"""

from .unified_card import UnifiedCard
from .card_manager import CardCollectionManager
from .classifiers import (
    PokemonCardClassifier,
    MTGCardClassifier,
    YuGiOhCardClassifier,
    SportsCardClassifier,
)
from .ai_integration import (
    create_card_from_ai_analysis,
    add_card_to_collection,
    is_likely_card,
)

__all__ = [
    'UnifiedCard',
    'CardCollectionManager',
    'PokemonCardClassifier',
    'MTGCardClassifier',
    'YuGiOhCardClassifier',
    'SportsCardClassifier',
    'create_card_from_ai_analysis',
    'add_card_to_collection',
    'is_likely_card',
]
