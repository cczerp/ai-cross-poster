"""
Base Card Classifier

All specific card classifiers (Pokémon, MTG, Sports, etc.) inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..unified_card import UnifiedCard


class BaseCardClassifier(ABC):
    """
    Base class for all card classifiers.

    Each card type (Pokémon, MTG, Sports, etc.) implements this interface
    to convert raw card data into a UnifiedCard object.
    """

    def __init__(self):
        self.card_type = self.get_card_type()

    @abstractmethod
    def get_card_type(self) -> str:
        """
        Return the card type identifier.
        Examples: 'pokemon', 'mtg', 'yugioh', 'sports_nfl', 'sports_nba'
        """
        pass

    @abstractmethod
    def classify_from_text(self, text: str, user_id: int) -> Optional[UnifiedCard]:
        """
        Classify a card from text input.

        Args:
            text: Card description or data (could be from manual entry, OCR, etc.)
            user_id: User who owns this card

        Returns:
            UnifiedCard object or None if unable to classify
        """
        pass

    @abstractmethod
    def classify_from_image(self, image_path: str, user_id: int) -> Optional[UnifiedCard]:
        """
        Classify a card from an image.

        Args:
            image_path: Path to card image
            user_id: User who owns this card

        Returns:
            UnifiedCard object or None if unable to classify
        """
        pass

    @abstractmethod
    def classify_from_dict(self, data: Dict[str, Any], user_id: int) -> UnifiedCard:
        """
        Classify a card from a dictionary (from CSV import, API, etc.)

        Args:
            data: Raw card data as dictionary
            user_id: User who owns this card

        Returns:
            UnifiedCard object
        """
        pass

    @abstractmethod
    def extract_set_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract set-specific information.

        Args:
            data: Raw card data

        Returns:
            Dict with set_name, set_code, set_symbol, etc.
        """
        pass

    @abstractmethod
    def extract_rarity(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract rarity information.

        Args:
            data: Raw card data

        Returns:
            Rarity string (Common, Rare, Ultra Rare, etc.)
        """
        pass

    def normalize_card_number(self, card_number: str) -> str:
        """
        Normalize card number format.

        Args:
            card_number: Raw card number

        Returns:
            Normalized card number
        """
        if not card_number:
            return ''

        # Remove leading zeros, but keep format like '001/150'
        parts = card_number.split('/')
        if len(parts) == 2:
            num = parts[0].lstrip('0') or '0'
            total = parts[1].lstrip('0') or '0'
            return f"{num}/{total}"

        return card_number.lstrip('0') or '0'

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text input.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        if not text:
            return ''

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Remove special characters that might cause issues
        text = text.replace('\n', ' ').replace('\r', ' ')

        return text.strip()

    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text for classification.

        Args:
            text: Input text

        Returns:
            List of keywords
        """
        # Common stop words to ignore
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}

        words = text.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords

    def calculate_confidence(self, identified_fields: int, total_fields: int) -> float:
        """
        Calculate confidence score based on identified fields.

        Args:
            identified_fields: Number of fields successfully identified
            total_fields: Total number of expected fields

        Returns:
            Confidence score (0.0 - 1.0)
        """
        if total_fields == 0:
            return 0.0

        confidence = identified_fields / total_fields

        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))

    def auto_assign_organization_mode(self, card: UnifiedCard) -> str:
        """
        Auto-suggest best organization mode for this card.

        Args:
            card: UnifiedCard object

        Returns:
            Suggested organization mode
        """
        # TCG cards: organize by set by default
        if card.is_tcg_card() and card.set_code:
            return 'by_set'

        # Sports cards: organize by year+brand
        if card.is_sports_card():
            if card.year and card.brand:
                return 'by_year'
            elif card.sport:
                return 'by_sport'

        # Graded cards: organize by grading
        if card.grading_company:
            return 'by_grading'

        # Default: by type
        return 'by_game' if card.is_tcg_card() else 'by_sport'

    def validate_card(self, card: UnifiedCard) -> tuple[bool, List[str]]:
        """
        Validate a UnifiedCard object.

        Args:
            card: UnifiedCard to validate

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        if not card.title:
            errors.append("Card title is required")
        if not card.card_type:
            errors.append("Card type is required")
        if not card.user_id:
            errors.append("User ID is required")

        # Check card_type validity
        valid_types = [
            'pokemon', 'mtg', 'yugioh', 'onepiece', 'dragonball',
            'sports_nfl', 'sports_nba', 'sports_mlb', 'sports_nhl',
            'sports_soccer', 'sports_other'
        ]
        if card.card_type not in valid_types:
            errors.append(f"Invalid card type: {card.card_type}")

        # Type-specific validation
        if card.is_tcg_card():
            if not card.game_name:
                errors.append("TCG cards require game_name")

        if card.is_sports_card():
            if not card.sport:
                errors.append("Sports cards require sport")

        return (len(errors) == 0, errors)
