"""
UnifiedCard - Universal data model for all card types

This class provides a standardized interface for all trading cards and sports cards,
regardless of their type (Pokémon, MTG, Yu-Gi-Oh, NFL, NBA, etc.)
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json


@dataclass
class UnifiedCard:
    """
    Unified data model for all card types.

    This class can represent:
    - Trading Card Games (Pokémon, MTG, Yu-Gi-Oh, etc.)
    - Sports Cards (NFL, NBA, MLB, NHL, etc.)
    - Any other collectible card type

    All fields are optional except the required core fields.
    """

    # ==========================================
    # REQUIRED CORE FIELDS
    # ==========================================
    card_type: str  # 'pokemon', 'mtg', 'yugioh', 'sports_nfl', 'sports_nba', 'sports_mlb', etc.
    title: str  # Full card name/title
    user_id: int  # Owner of this card

    # ==========================================
    # UNIVERSAL FIELDS (all cards)
    # ==========================================
    card_uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    card_number: Optional[str] = None
    quantity: int = 1

    # ==========================================
    # ORGANIZATION FIELDS
    # ==========================================
    organization_mode: Optional[str] = None  # 'by_set', 'by_year', 'by_sport', 'by_brand', etc.
    primary_category: Optional[str] = None  # Auto-assigned based on organization mode
    custom_categories: List[str] = field(default_factory=list)  # User-defined tags

    # ==========================================
    # PHYSICAL LOCATION
    # ==========================================
    storage_location: Optional[str] = None  # 'Binder A Page 1', 'Box 3 Row 2', etc.
    storage_item_id: Optional[int] = None  # Link to storage_items table

    # ==========================================
    # TCG FIELDS (Pokémon, MTG, Yu-Gi-Oh, etc.)
    # ==========================================
    game_name: Optional[str] = None  # 'Pokemon', 'Magic: The Gathering', 'Yu-Gi-Oh!', etc.
    set_name: Optional[str] = None  # Full set name
    set_code: Optional[str] = None  # Set abbreviation (SV1, M25, etc.)
    set_symbol: Optional[str] = None  # Set symbol description
    rarity: Optional[str] = None  # Common, Uncommon, Rare, Ultra Rare, Secret Rare, Mythic, etc.
    card_subtype: Optional[str] = None  # Trainer, Energy, Creature, Spell, Trap, etc.
    format_legality: Dict[str, str] = field(default_factory=dict)  # Standard: Legal, Modern: Banned, etc.

    # ==========================================
    # SPORTS CARD FIELDS (NFL, NBA, MLB, etc.)
    # ==========================================
    sport: Optional[str] = None  # 'NFL', 'NBA', 'MLB', 'NHL', etc.
    year: Optional[int] = None  # Card year
    brand: Optional[str] = None  # Topps, Panini, Upper Deck, etc.
    series: Optional[str] = None  # Series/product line (Prizm, Bowman Chrome, etc.)
    player_name: Optional[str] = None  # Player name (for sports cards)
    team: Optional[str] = None  # Team name
    is_rookie_card: bool = False  # RC flag
    parallel_color: Optional[str] = None  # Parallel/variant color (Silver, Gold, Red, etc.)
    insert_series: Optional[str] = None  # Insert/special series name

    # ==========================================
    # GRADING & VALUE
    # ==========================================
    grading_company: Optional[str] = None  # PSA, BGS, CGC, etc.
    grading_score: Optional[float] = None  # 9.5, 10, etc.
    grading_serial: Optional[str] = None  # Grading serial number
    estimated_value: Optional[float] = None  # Current estimated value
    value_tier: Optional[str] = None  # 'under_10', '10_50', '50_100', '100_500', 'over_500'
    purchase_price: Optional[float] = None  # What you paid for it

    # ==========================================
    # PHOTOS & NOTES
    # ==========================================
    photos: List[str] = field(default_factory=list)  # Photo paths
    notes: Optional[str] = None  # User notes

    # ==========================================
    # METADATA
    # ==========================================
    ai_identified: bool = False  # Was this auto-identified by AI?
    ai_confidence: float = 0.0  # Confidence score (0.0 - 1.0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Auto-assign primary category based on organization mode"""
        if not self.created_at:
            self.created_at = datetime.now()
        if not self.updated_at:
            self.updated_at = datetime.now()

        # Auto-assign primary category if not set
        if not self.primary_category and self.organization_mode:
            self.primary_category = self._auto_assign_category()

        # Auto-assign value tier based on estimated value
        if self.estimated_value and not self.value_tier:
            self.value_tier = self._calculate_value_tier()

    def _auto_assign_category(self) -> str:
        """Auto-assign primary category based on organization mode"""
        mode = self.organization_mode

        if mode == 'by_set':
            return self.set_code or self.set_name or 'Unknown Set'
        elif mode == 'by_year':
            return str(self.year) if self.year else 'Unknown Year'
        elif mode == 'by_sport':
            return self.sport or 'Unknown Sport'
        elif mode == 'by_brand':
            return self.brand or 'Unknown Brand'
        elif mode == 'by_game':
            return self.game_name or 'Unknown Game'
        elif mode == 'by_rarity':
            return self.rarity or 'Unknown Rarity'
        elif mode == 'by_number':
            return self.card_number or 'Unnumbered'
        elif mode == 'by_grading':
            if self.grading_company and self.grading_score:
                return f"{self.grading_company} {self.grading_score}"
            elif self.grading_company:
                return f"{self.grading_company} Ungraded"
            else:
                return 'Raw (Ungraded)'
        elif mode == 'by_value':
            return self.value_tier or self._calculate_value_tier()
        elif mode == 'by_binder':
            return self.storage_location or 'Unsorted'
        else:  # custom or unknown
            return 'Uncategorized'

    def _calculate_value_tier(self) -> str:
        """Calculate value tier based on estimated value"""
        if not self.estimated_value:
            return 'unknown'

        value = self.estimated_value
        if value < 10:
            return 'under_10'
        elif value < 50:
            return '10_50'
        elif value < 100:
            return '50_100'
        elif value < 500:
            return '100_500'
        else:
            return 'over_500'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)

        # Convert datetime to ISO format
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()

        # Convert lists and dicts to JSON strings for database storage
        data['custom_categories'] = json.dumps(self.custom_categories)
        data['format_legality'] = json.dumps(self.format_legality)
        data['photos'] = json.dumps(self.photos)

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedCard':
        """Create UnifiedCard from dictionary"""
        # Parse JSON fields
        if isinstance(data.get('custom_categories'), str):
            data['custom_categories'] = json.loads(data['custom_categories'] or '[]')
        if isinstance(data.get('format_legality'), str):
            data['format_legality'] = json.loads(data['format_legality'] or '{}')
        if isinstance(data.get('photos'), str):
            data['photos'] = json.loads(data['photos'] or '[]')

        # Parse datetime fields
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        return cls(**data)

    def to_csv_row(self) -> Dict[str, Any]:
        """
        Convert to CSV-friendly format for export.
        Returns a flattened dict suitable for CSV writing.
        """
        return {
            'Card UUID': self.card_uuid,
            'Card Type': self.card_type,
            'Title': self.title,
            'Card Number': self.card_number or '',
            'Quantity': self.quantity,
            'Organization Mode': self.organization_mode or '',
            'Primary Category': self.primary_category or '',
            'Custom Categories': ', '.join(self.custom_categories),

            # TCG Fields
            'Game': self.game_name or '',
            'Set Name': self.set_name or '',
            'Set Code': self.set_code or '',
            'Rarity': self.rarity or '',
            'Card Subtype': self.card_subtype or '',

            # Sports Fields
            'Sport': self.sport or '',
            'Year': self.year or '',
            'Brand': self.brand or '',
            'Series': self.series or '',
            'Player Name': self.player_name or '',
            'Team': self.team or '',
            'Rookie Card': 'Yes' if self.is_rookie_card else 'No',
            'Parallel': self.parallel_color or '',
            'Insert Series': self.insert_series or '',

            # Grading & Value
            'Grading Company': self.grading_company or '',
            'Grading Score': self.grading_score or '',
            'Grading Serial': self.grading_serial or '',
            'Estimated Value': self.estimated_value or '',
            'Purchase Price': self.purchase_price or '',

            # Location
            'Storage Location': self.storage_location or '',
            'Notes': self.notes or '',

            # Metadata
            'AI Identified': 'Yes' if self.ai_identified else 'No',
            'AI Confidence': f"{self.ai_confidence:.2%}" if self.ai_confidence else '',
            'Created At': self.created_at.strftime('%Y-%m-%d') if self.created_at else '',
        }

    @classmethod
    def from_csv_row(cls, row: Dict[str, Any], user_id: int) -> 'UnifiedCard':
        """
        Create UnifiedCard from CSV row.
        Handles various CSV formats flexibly.
        """
        return cls(
            card_uuid=row.get('Card UUID') or str(uuid.uuid4()),
            card_type=row.get('Card Type', 'unknown'),
            title=row.get('Title', 'Unknown Card'),
            user_id=user_id,
            card_number=row.get('Card Number') or None,
            quantity=int(row.get('Quantity', 1)),
            organization_mode=row.get('Organization Mode') or None,
            primary_category=row.get('Primary Category') or None,
            custom_categories=row.get('Custom Categories', '').split(', ') if row.get('Custom Categories') else [],

            # TCG Fields
            game_name=row.get('Game') or None,
            set_name=row.get('Set Name') or None,
            set_code=row.get('Set Code') or None,
            rarity=row.get('Rarity') or None,
            card_subtype=row.get('Card Subtype') or None,

            # Sports Fields
            sport=row.get('Sport') or None,
            year=int(row['Year']) if row.get('Year') else None,
            brand=row.get('Brand') or None,
            series=row.get('Series') or None,
            player_name=row.get('Player Name') or None,
            team=row.get('Team') or None,
            is_rookie_card=row.get('Rookie Card', '').lower() in ['yes', 'true', '1'],
            parallel_color=row.get('Parallel') or None,
            insert_series=row.get('Insert Series') or None,

            # Grading & Value
            grading_company=row.get('Grading Company') or None,
            grading_score=float(row['Grading Score']) if row.get('Grading Score') else None,
            grading_serial=row.get('Grading Serial') or None,
            estimated_value=float(row['Estimated Value']) if row.get('Estimated Value') else None,
            purchase_price=float(row['Purchase Price']) if row.get('Purchase Price') else None,

            # Location
            storage_location=row.get('Storage Location') or None,
            notes=row.get('Notes') or None,

            # Metadata
            ai_identified=row.get('AI Identified', '').lower() in ['yes', 'true', '1'],
            ai_confidence=float(row['AI Confidence'].rstrip('%')) / 100 if row.get('AI Confidence') and '%' in row['AI Confidence'] else 0.0,
        )

    def is_tcg_card(self) -> bool:
        """Check if this is a trading card game card"""
        return self.card_type in ['pokemon', 'mtg', 'yugioh', 'onepiece', 'dragonball']

    def is_sports_card(self) -> bool:
        """Check if this is a sports card"""
        return self.card_type.startswith('sports_')

    def get_display_name(self) -> str:
        """Get a friendly display name for the card"""
        if self.is_sports_card() and self.player_name:
            return f"{self.player_name} - {self.title}"
        return self.title

    def get_sort_key(self) -> tuple:
        """Get a sort key based on organization mode"""
        mode = self.organization_mode

        if mode == 'by_set':
            return (self.set_code or 'ZZZ', self.card_number or '0000', self.title)
        elif mode == 'by_year':
            return (self.year or 9999, self.title)
        elif mode == 'by_sport':
            return (self.sport or 'ZZZ', self.year or 9999, self.title)
        elif mode == 'by_brand':
            return (self.brand or 'ZZZ', self.year or 9999, self.title)
        elif mode == 'by_game':
            return (self.game_name or 'ZZZ', self.set_code or 'ZZZ', self.card_number or '0000')
        elif mode == 'by_rarity':
            return (self.rarity or 'ZZZ', self.title)
        elif mode == 'by_number':
            return (self.card_number or '9999', self.title)
        elif mode == 'by_grading':
            return (self.grading_company or 'ZZZ', -(self.grading_score or 0), self.title)
        elif mode == 'by_value':
            return (-(self.estimated_value or 0), self.title)
        else:  # by_binder, custom, or default
            return (self.storage_location or 'ZZZ', self.title)
