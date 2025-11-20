"""Magic: The Gathering Card Classifier"""

from typing import Dict, Any, Optional
from .base_classifier import BaseCardClassifier
from ..unified_card import UnifiedCard


class MTGCardClassifier(BaseCardClassifier):
    """Classifier for Magic: The Gathering cards"""

    def get_card_type(self) -> str:
        return 'mtg'

    def classify_from_text(self, text: str, user_id: int) -> Optional[UnifiedCard]:
        """Classify MTG card from text"""
        # Simplified implementation
        words = text.split()
        title = ' '.join(words[:3]) if len(words) >= 3 else text
        
        return UnifiedCard(
            card_type='mtg',
            title=title,
            user_id=user_id,
            game_name='Magic: The Gathering',
            organization_mode='by_set',
            ai_identified=True,
            ai_confidence=0.5
        )

    def classify_from_image(self, image_path: str, user_id: int) -> Optional[UnifiedCard]:
        """Classify from image - to be implemented"""
        return None

    def classify_from_dict(self, data: Dict[str, Any], user_id: int) -> UnifiedCard:
        """Classify MTG card from dictionary"""
        return UnifiedCard(
            card_type='mtg',
            title=data.get('title') or data.get('name', 'Unknown MTG Card'),
            user_id=user_id,
            card_number=data.get('card_number'),
            quantity=int(data.get('quantity', 1)),
            game_name='Magic: The Gathering',
            set_name=data.get('set_name'),
            set_code=data.get('set_code'),
            rarity=data.get('rarity'),
            card_subtype=data.get('card_subtype'),
            storage_location=data.get('storage_location'),
            notes=data.get('notes'),
            estimated_value=float(data['estimated_value']) if data.get('estimated_value') else None,
            organization_mode=data.get('organization_mode') or 'by_set'
        )

    def extract_set_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract MTG set information"""
        return {
            'set_name': data.get('set_name'),
            'set_code': data.get('set_code'),
            'set_symbol': None
        }

    def extract_rarity(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract MTG rarity"""
        return data.get('rarity')
