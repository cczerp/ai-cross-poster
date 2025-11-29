"""
Sports Card Classifier

Classifies sports cards for NFL, NBA, MLB, NHL, Soccer, etc.
"""

from typing import Dict, Any, Optional
import re
from .base_classifier import BaseCardClassifier
from ..unified_card import UnifiedCard


class SportsCardClassifier(BaseCardClassifier):
    """Classifier for sports cards (NFL, NBA, MLB, NHL, etc.)"""

    # Sport detection keywords
    SPORT_KEYWORDS = {
        'sports_nfl': ['nfl', 'football', 'quarterback', 'qb', 'touchdown'],
        'sports_nba': ['nba', 'basketball', 'lakers', 'celtics', 'dunk'],
        'sports_mlb': ['mlb', 'baseball', 'yankees', 'dodgers', 'homerun'],
        'sports_nhl': ['nhl', 'hockey', 'puck', 'maple leafs'],
        'sports_soccer': ['soccer', 'football', 'messi', 'ronaldo', 'premier league'],
    }

    # Common brands
    BRANDS = ['topps', 'panini', 'upper deck', 'donruss', 'fleer', 'bowman', 'prizm', 'select']

    def __init__(self, sport: str = 'nfl'):
        """
        Initialize sports classifier.

        Args:
            sport: Default sport ('nfl', 'nba', 'mlb', 'nhl', 'soccer')
        """
        super().__init__()
        self.sport = sport

    def get_card_type(self) -> str:
        return f'sports_{self.sport}'

    def classify_from_text(self, text: str, user_id: int) -> Optional[UnifiedCard]:
        """
        Classify sports card from text.

        Example formats:
        - "Tom Brady 2000 Topps Chrome #236 RC"
        - "Michael Jordan 1986 Fleer #57 Rookie Card"
        - "LeBron James 2003 Upper Deck #23"
        """
        text = self.clean_text(text)

        # Detect sport from text
        sport = self._detect_sport(text)

        # Extract player name (usually first 2-3 words)
        player_name = self._extract_player_name(text)

        # Extract year
        year = self._extract_year(text)

        # Extract brand
        brand = self._extract_brand(text)

        # Extract card number
        card_number = self._extract_card_number(text)

        # Check if rookie card
        is_rookie = self._is_rookie_card(text)

        # Extract series (e.g., "Chrome", "Prizm Silver", etc.)
        series = self._extract_series(text)

        # Extract parallel
        parallel = self._extract_parallel(text)

        # Create title
        title = f"{player_name}" if player_name else "Unknown Player"
        if series:
            title += f" {series}"
        if is_rookie:
            title += " RC"

        # Create UnifiedCard
        card = UnifiedCard(
            card_type=f'sports_{sport}',
            title=title,
            user_id=user_id,
            card_number=self.normalize_card_number(card_number) if card_number else None,
            sport=sport.upper(),
            year=year,
            brand=brand,
            series=series,
            player_name=player_name,
            is_rookie_card=is_rookie,
            parallel_color=parallel,
            ai_identified=True,
            ai_confidence=self.calculate_confidence(
                sum([bool(player_name), bool(year), bool(brand), bool(card_number)]), 4
            )
        )

        # Auto-assign organization mode
        card.organization_mode = 'by_year' if year else 'by_sport'

        return card

    def classify_from_image(self, image_path: str, user_id: int) -> Optional[UnifiedCard]:
        """
        Classify sports card from image using Gemini AI vision.

        Uses the Gemini classifier to analyze the card image and extract:
        - Player name, year, brand, series
        - Card number and rookie card status
        - Grading information if present
        - Parallel/variant information

        Args:
            image_path: Path to the card image
            user_id: User ID for the card

        Returns:
            UnifiedCard object or None if not a valid sports card
        """
        try:
            from ..ai_integration import create_card_from_ai_analysis
            from ...ai.gemini_classifier import GeminiClassifier
            from ...schema.unified_listing import Photo

            # Create Photo object from image path
            photo = Photo(local_path=image_path, is_primary=True)

            # Analyze card with Gemini
            gemini = GeminiClassifier.from_env()
            ai_result = gemini.analyze_card([photo])

            # Check if it's actually a card
            if not ai_result.get('is_card'):
                return None

            # Check if it's a sports card
            card_type = ai_result.get('card_type', '')
            if not card_type.startswith('sports_'):
                return None

            # Convert AI result to UnifiedCard
            card = create_card_from_ai_analysis(
                ai_result=ai_result,
                user_id=user_id,
                photos=[image_path]
            )

            return card

        except ImportError as e:
            print(f"Gemini classifier not available: {e}")
            return None
        except Exception as e:
            print(f"Error classifying sports card from image: {e}")
            import traceback
            traceback.print_exc()
            return None

    def classify_from_dict(self, data: Dict[str, Any], user_id: int) -> UnifiedCard:
        """Classify sports card from dictionary data (CSV import, API, etc.)"""
        # Detect sport from data
        sport = data.get('sport', '').lower() or self.sport

        # Extract player name
        player_name = data.get('player_name') or data.get('player') or data.get('name')

        # Build title
        title = player_name or 'Unknown Player'
        if data.get('series'):
            title += f" {data['series']}"
        if data.get('is_rookie_card') or data.get('rookie'):
            title += " RC"

        # Create UnifiedCard
        card = UnifiedCard(
            card_type=f'sports_{sport}',
            title=title,
            user_id=user_id,
            card_number=data.get('card_number'),
            quantity=int(data.get('quantity', 1)),
            sport=sport.upper(),
            year=int(data['year']) if data.get('year') else None,
            brand=data.get('brand'),
            series=data.get('series'),
            player_name=player_name,
            team=data.get('team'),
            is_rookie_card=bool(data.get('is_rookie_card') or data.get('rookie')),
            parallel_color=data.get('parallel') or data.get('parallel_color'),
            insert_series=data.get('insert_series'),
            grading_company=data.get('grading_company'),
            grading_score=float(data['grading_score']) if data.get('grading_score') else None,
            storage_location=data.get('storage_location'),
            notes=data.get('notes'),
            estimated_value=float(data['estimated_value']) if data.get('estimated_value') else None,
            purchase_price=float(data['purchase_price']) if data.get('purchase_price') else None,
            organization_mode=data.get('organization_mode') or 'by_year'
        )

        return card

    def extract_set_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract set/series information for sports cards"""
        return {
            'set_name': data.get('series') or data.get('set_name'),
            'set_code': None,  # Sports cards don't typically use set codes like TCGs
            'set_symbol': None
        }

    def extract_rarity(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract rarity - for sports cards, often indicated by parallel color"""
        parallel = data.get('parallel') or data.get('parallel_color')
        if parallel:
            return f"{parallel} Parallel"

        insert = data.get('insert_series')
        if insert:
            return f"{insert} Insert"

        return None

    # ==========================================
    # PRIVATE HELPER METHODS
    # ==========================================

    def _detect_sport(self, text: str) -> str:
        """Detect sport from text"""
        text_lower = text.lower()

        for sport_type, keywords in self.SPORT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return sport_type.replace('sports_', '')

        # Default to initialized sport
        return self.sport

    def _extract_player_name(self, text: str) -> Optional[str]:
        """Extract player name from text"""
        # Remove year, brand, card number
        text_clean = re.sub(r'\d{4}', '', text)  # Remove year
        text_clean = re.sub(r'#\d+', '', text_clean)  # Remove card number

        # Remove brand names
        for brand in self.BRANDS:
            text_clean = text_clean.replace(brand, '')
            text_clean = text_clean.replace(brand.title(), '')

        # Remove common suffixes
        text_clean = text_clean.replace(' RC', '').replace(' Rookie', '')

        # Get first 2-3 words as name
        words = text_clean.split()
        if len(words) >= 2:
            return f"{words[0]} {words[1]}".strip()

        return text_clean.strip() if text_clean.strip() else None

    def _extract_year(self, text: str) -> Optional[int]:
        """Extract year from text"""
        # Find 4-digit year (1900-2099)
        match = re.search(r'(19\d{2}|20\d{2})', text)
        if match:
            return int(match.group(1))
        return None

    def _extract_brand(self, text: str) -> Optional[str]:
        """Extract brand from text"""
        text_lower = text.lower()

        for brand in self.BRANDS:
            if brand in text_lower:
                return brand.title()

        return None

    def _extract_card_number(self, text: str) -> Optional[str]:
        """Extract card number from text"""
        # Look for #123 or just 123
        match = re.search(r'#?(\d+)', text)
        if match:
            return match.group(1)
        return None

    def _is_rookie_card(self, text: str) -> bool:
        """Check if this is a rookie card"""
        text_lower = text.lower()
        return ' rc' in text_lower or 'rookie' in text_lower

    def _extract_series(self, text: str) -> Optional[str]:
        """Extract series name (Chrome, Prizm, etc.)"""
        series_keywords = ['chrome', 'prizm', 'optic', 'select', 'donruss', 'bowman']

        text_lower = text.lower()
        for series in series_keywords:
            if series in text_lower:
                # Try to get variant too (e.g., "Prizm Silver")
                pattern = rf'{series}\s+(\w+)'
                match = re.search(pattern, text_lower)
                if match:
                    return f"{series.title()} {match.group(1).title()}"
                return series.title()

        return None

    def _extract_parallel(self, text: str) -> Optional[str]:
        """Extract parallel color"""
        parallel_colors = ['silver', 'gold', 'red', 'blue', 'green', 'orange', 'purple', 'black', 'refractor']

        text_lower = text.lower()
        for color in parallel_colors:
            if color in text_lower:
                return color.title()

        return None
