"""
Pokémon Card Classifier

Identifies and classifies Pokémon TCG cards.
"""

from typing import Dict, Any, Optional
import re
from .base_classifier import BaseCardClassifier
from ..unified_card import UnifiedCard


class PokemonCardClassifier(BaseCardClassifier):
    """Classifier for Pokémon Trading Card Game cards"""

    # Common Pokémon set codes and names
    POKEMON_SETS = {
        'SV': 'Scarlet & Violet',
        'SV1': 'Scarlet & Violet Base',
        'SV2': 'Paldea Evolved',
        'SV3': 'Obsidian Flames',
        'SV4': '151',
        'SV5': 'Temporal Forces',
        'SWSH': 'Sword & Shield',
        'SWSH1': 'Sword & Shield Base',
        'SWSH12': 'Silver Tempest',
        'BS': 'Base Set',
        'JU': 'Jungle',
        'FO': 'Fossil',
        'B2': 'Base Set 2',
        'TR': 'Team Rocket',
        'XY': 'XY Base',
        'SM': 'Sun & Moon',
    }

    # Pokémon rarity codes
    RARITY_MAPPING = {
        '●': 'Common',
        '◆': 'Uncommon',
        '★': 'Rare',
        '★H': 'Rare Holo',
        'RH': 'Reverse Holo',
        'RR': 'Double Rare',
        'RRR': 'Triple Rare',
        'SR': 'Secret Rare',
        'UR': 'Ultra Rare',
        'HR': 'Hyper Rare',
        'AR': 'Art Rare',
        'SAR': 'Special Art Rare',
        'PR': 'Promo',
    }

    def get_card_type(self) -> str:
        return 'pokemon'

    def classify_from_text(self, text: str, user_id: int) -> Optional[UnifiedCard]:
        """
        Classify Pokémon card from text input.

        Example text formats:
        - "Charizard 6/102 Base Set Holo"
        - "Pikachu VMAX 044/185 Vivid Voltage"
        - "Mewtwo ex SV1 150/198 Secret Rare"
        """
        text = self.clean_text(text)

        # Try to extract card name
        card_name = self._extract_card_name(text)
        if not card_name:
            return None

        # Extract card number (e.g., "6/102", "044/185")
        card_number = self._extract_card_number(text)

        # Extract set code/name
        set_info = self._extract_set_from_text(text)

        # Extract rarity
        rarity = self._extract_rarity_from_text(text)

        # Determine card subtype
        card_subtype = self._determine_subtype(card_name, text)

        # Create UnifiedCard
        card = UnifiedCard(
            card_type='pokemon',
            title=card_name,
            user_id=user_id,
            card_number=self.normalize_card_number(card_number) if card_number else None,
            game_name='Pokemon',
            set_name=set_info.get('set_name'),
            set_code=set_info.get('set_code'),
            rarity=rarity,
            card_subtype=card_subtype,
            ai_identified=True,
            ai_confidence=self.calculate_confidence(
                sum([bool(card_name), bool(card_number), bool(set_info), bool(rarity)]), 4
            )
        )

        # Auto-assign organization mode
        card.organization_mode = 'by_set'

        return card

    def classify_from_image(self, image_path: str, user_id: int) -> Optional[UnifiedCard]:
        """
        Classify Pokémon card from image.

        This would use OCR + AI to identify the card.
        For now, returns None - to be implemented with AI integration.
        """
        # TODO: Implement with Gemini/Claude AI vision
        # 1. OCR the image to extract text
        # 2. Identify set symbol visually
        # 3. Extract card number, name, rarity
        # 4. Cross-reference with known Pokémon card database
        return None

    def classify_from_dict(self, data: Dict[str, Any], user_id: int) -> UnifiedCard:
        """
        Classify Pokémon card from dictionary data (CSV import, API, etc.)
        """
        # Extract and normalize fields
        title = data.get('title') or data.get('name') or data.get('card_name', 'Unknown Pokémon')
        card_number = data.get('card_number') or data.get('number')

        # Set information
        set_name = data.get('set_name') or data.get('set')
        set_code = data.get('set_code') or self._infer_set_code(set_name)

        # Rarity
        rarity = data.get('rarity')
        if rarity and rarity in self.RARITY_MAPPING:
            rarity = self.RARITY_MAPPING[rarity]

        # Card subtype
        card_subtype = data.get('card_subtype') or data.get('supertype') or self._determine_subtype(title, '')

        # Create UnifiedCard
        card = UnifiedCard(
            card_type='pokemon',
            title=title,
            user_id=user_id,
            card_number=self.normalize_card_number(card_number) if card_number else None,
            quantity=int(data.get('quantity', 1)),
            game_name='Pokemon',
            set_name=set_name,
            set_code=set_code,
            rarity=rarity,
            card_subtype=card_subtype,
            storage_location=data.get('storage_location'),
            notes=data.get('notes'),
            estimated_value=float(data['estimated_value']) if data.get('estimated_value') else None,
            purchase_price=float(data['purchase_price']) if data.get('purchase_price') else None,
        )

        # Set organization mode
        card.organization_mode = data.get('organization_mode') or 'by_set'

        return card

    def extract_set_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Pokémon set information"""
        set_name = data.get('set_name') or data.get('set')
        set_code = data.get('set_code')

        if not set_code and set_name:
            set_code = self._infer_set_code(set_name)

        return {
            'set_name': set_name,
            'set_code': set_code,
            'set_symbol': None,  # Could be extracted from image
        }

    def extract_rarity(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract Pokémon card rarity"""
        rarity = data.get('rarity')

        if rarity and rarity in self.RARITY_MAPPING:
            return self.RARITY_MAPPING[rarity]

        return rarity

    # ==========================================
    # PRIVATE HELPER METHODS
    # ==========================================

    def _extract_card_name(self, text: str) -> Optional[str]:
        """Extract Pokémon card name from text"""
        # Common patterns:
        # "Charizard ex"
        # "Pikachu VMAX"
        # "Mewtwo V"

        # Remove card numbers first
        text_no_number = re.sub(r'\d+/\d+', '', text)

        # Remove set names
        for set_code in self.POKEMON_SETS.keys():
            text_no_number = text_no_number.replace(set_code, '')

        # Remove rarity indicators
        for rarity in self.RARITY_MAPPING.values():
            text_no_number = text_no_number.replace(rarity, '')

        # Extract name (usually first 1-3 words)
        words = text_no_number.split()
        if not words:
            return None

        # Try to get name with suffix (ex, V, VMAX, etc.)
        name_parts = []
        for word in words[:4]:  # Look at first 4 words max
            name_parts.append(word)
            if word.lower() in ['ex', 'v', 'vmax', 'vstar', 'gx', 'break']:
                break

        return ' '.join(name_parts).strip() if name_parts else None

    def _extract_card_number(self, text: str) -> Optional[str]:
        """Extract card number from text (e.g., '6/102', '044/185')"""
        match = re.search(r'(\d+)/(\d+)', text)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        return None

    def _extract_set_from_text(self, text: str) -> Dict[str, Any]:
        """Extract set information from text"""
        # Check for known set codes
        for set_code, set_name in self.POKEMON_SETS.items():
            if set_code.lower() in text.lower() or set_name.lower() in text.lower():
                return {'set_code': set_code, 'set_name': set_name}

        return {'set_code': None, 'set_name': None}

    def _extract_rarity_from_text(self, text: str) -> Optional[str]:
        """Extract rarity from text"""
        text_lower = text.lower()

        # Check for rarity keywords
        for rarity_code, rarity_name in self.RARITY_MAPPING.items():
            if rarity_name.lower() in text_lower or rarity_code.lower() in text_lower:
                return rarity_name

        # Check for common rarity words
        if 'common' in text_lower:
            return 'Common'
        elif 'uncommon' in text_lower:
            return 'Uncommon'
        elif 'rare' in text_lower:
            if 'ultra' in text_lower:
                return 'Ultra Rare'
            elif 'secret' in text_lower:
                return 'Secret Rare'
            elif 'holo' in text_lower:
                return 'Rare Holo'
            else:
                return 'Rare'

        return None

    def _determine_subtype(self, card_name: str, text: str) -> str:
        """Determine card subtype (Pokémon, Trainer, Energy)"""
        text_lower = (card_name + ' ' + text).lower()

        if any(word in text_lower for word in ['trainer', 'supporter', 'item', 'stadium', 'tool']):
            return 'Trainer'
        elif 'energy' in text_lower:
            return 'Energy'
        else:
            return 'Pokémon'

    def _infer_set_code(self, set_name: str) -> Optional[str]:
        """Infer set code from set name"""
        if not set_name:
            return None

        set_name_lower = set_name.lower()

        for set_code, name in self.POKEMON_SETS.items():
            if name.lower() == set_name_lower:
                return set_code

        return None
