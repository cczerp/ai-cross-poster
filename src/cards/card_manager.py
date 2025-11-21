"""
Card Collection Manager

Main interface for managing card collections.
Handles CRUD operations, CSV import/export, and organization.
"""

from typing import List, Dict, Any, Optional
import csv
import io
from pathlib import Path
from .unified_card import UnifiedCard
from .classifiers import (
    PokemonCardClassifier,
    MTGCardClassifier,
    YuGiOhCardClassifier,
    SportsCardClassifier,
)
from src.database.db import get_db


class CardCollectionManager:
    """
    Main manager for card collections.

    Provides:
    - Add/Edit/Delete cards
    - CSV Import/Export
    - Organization mode switching
    - Search and filtering
    """

    def __init__(self):
        self.db = get_db()

        # Initialize classifiers
        self.classifiers = {
            'pokemon': PokemonCardClassifier(),
            'mtg': MTGCardClassifier(),
            'yugioh': YuGiOhCardClassifier(),
            'sports_nfl': SportsCardClassifier('nfl'),
            'sports_nba': SportsCardClassifier('nba'),
            'sports_mlb': SportsCardClassifier('mlb'),
            'sports_nhl': SportsCardClassifier('nhl'),
            'sports_soccer': SportsCardClassifier('soccer'),
        }

    # ==========================================
    # CARD CRUD OPERATIONS
    # ==========================================

    def add_card(self, card: UnifiedCard) -> int:
        """
        Add a card to the collection.

        Args:
            card: UnifiedCard object

        Returns:
            Card ID
        """
        cursor = self.db._get_cursor()

        card_dict = card.to_dict()

        cursor.execute("""
            INSERT INTO card_collections (
                user_id, card_uuid, card_type, title, card_number, quantity,
                organization_mode, primary_category, custom_categories,
                storage_location, storage_item_id,
                game_name, set_name, set_code, set_symbol, rarity, card_subtype, format_legality,
                sport, year, brand, series, player_name, team, is_rookie_card, parallel_color, insert_series,
                grading_company, grading_score, grading_serial, estimated_value, value_tier, purchase_price,
                photos, notes, ai_identified, ai_confidence
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """, (
            card_dict['user_id'], card_dict['card_uuid'], card_dict['card_type'], card_dict['title'],
            card_dict['card_number'], card_dict['quantity'],
            card_dict['organization_mode'], card_dict['primary_category'], card_dict['custom_categories'],
            card_dict['storage_location'], card_dict['storage_item_id'],
            card_dict['game_name'], card_dict['set_name'], card_dict['set_code'], card_dict['set_symbol'],
            card_dict['rarity'], card_dict['card_subtype'], card_dict['format_legality'],
            card_dict['sport'], card_dict['year'], card_dict['brand'], card_dict['series'],
            card_dict['player_name'], card_dict['team'], card_dict['is_rookie_card'],
            card_dict['parallel_color'], card_dict['insert_series'],
            card_dict['grading_company'], card_dict['grading_score'], card_dict['grading_serial'],
            card_dict['estimated_value'], card_dict['value_tier'], card_dict['purchase_price'],
            card_dict['photos'], card_dict['notes'], card_dict['ai_identified'], card_dict['ai_confidence']
        ))

        result = cursor.fetchone()
        self.db.conn.commit()
        return result['id']

    def get_card(self, card_id: int) -> Optional[UnifiedCard]:
        """Get a card by ID"""
        cursor = self.db._get_cursor()
        cursor.execute("SELECT * FROM card_collections WHERE id = %s", (card_id,))
        row = cursor.fetchone()

        if row:
            return UnifiedCard.from_dict(dict(row))
        return None

    def update_card(self, card_id: int, card: UnifiedCard):
        """Update an existing card"""
        cursor = self.db._get_cursor()
        card_dict = card.to_dict()

        cursor.execute("""
            UPDATE card_collections SET
                title = %s, card_number = %s, quantity = %s,
                organization_mode = %s, primary_category = %s, custom_categories = %s,
                storage_location = %s, storage_item_id = %s,
                game_name = %s, set_name = %s, set_code = %s, set_symbol = %s, rarity = %s, card_subtype = %s, format_legality = %s,
                sport = %s, year = %s, brand = %s, series = %s, player_name = %s, team = %s, is_rookie_card = %s, parallel_color = %s, insert_series = %s,
                grading_company = %s, grading_score = %s, grading_serial = %s, estimated_value = %s, value_tier = %s, purchase_price = %s,
                photos = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (
            card_dict['title'], card_dict['card_number'], card_dict['quantity'],
            card_dict['organization_mode'], card_dict['primary_category'], card_dict['custom_categories'],
            card_dict['storage_location'], card_dict['storage_item_id'],
            card_dict['game_name'], card_dict['set_name'], card_dict['set_code'], card_dict['set_symbol'],
            card_dict['rarity'], card_dict['card_subtype'], card_dict['format_legality'],
            card_dict['sport'], card_dict['year'], card_dict['brand'], card_dict['series'],
            card_dict['player_name'], card_dict['team'], card_dict['is_rookie_card'],
            card_dict['parallel_color'], card_dict['insert_series'],
            card_dict['grading_company'], card_dict['grading_score'], card_dict['grading_serial'],
            card_dict['estimated_value'], card_dict['value_tier'], card_dict['purchase_price'],
            card_dict['photos'], card_dict['notes'],
            card_id
        ))

        self.db.conn.commit()

    def delete_card(self, card_id: int):
        """Delete a card"""
        cursor = self.db._get_cursor()
        cursor.execute("DELETE FROM card_collections WHERE id = %s", (card_id,))
        self.db.conn.commit()

    # ==========================================
    # COLLECTION QUERIES
    # ==========================================

    def get_user_cards(
        self,
        user_id: int,
        card_type: Optional[str] = None,
        organization_mode: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UnifiedCard]:
        """
        Get cards for a user with optional filters.

        Args:
            user_id: User ID
            card_type: Filter by card type (pokemon, mtg, sports_nfl, etc.)
            organization_mode: Filter by organization mode
            limit: Max cards to return
            offset: Pagination offset

        Returns:
            List of UnifiedCard objects
        """
        cursor = self.db._get_cursor()

        query = "SELECT * FROM card_collections WHERE user_id = %s"
        params = [user_id]

        if card_type:
            query += " AND card_type = %s"
            params.append(card_type)

        if organization_mode:
            query += " AND organization_mode = %s"
            params.append(organization_mode)

        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [UnifiedCard.from_dict(dict(row)) for row in rows]

    def get_cards_by_organization(
        self,
        user_id: int,
        organization_mode: str,
        card_type: Optional[str] = None
    ) -> Dict[str, List[UnifiedCard]]:
        """
        Get cards organized by primary category.

        Args:
            user_id: User ID
            organization_mode: Organization mode
            card_type: Optional card type filter

        Returns:
            Dict mapping category names to lists of cards
        """
        cards = self.get_user_cards(user_id, card_type=card_type, limit=1000)

        # Filter by organization mode
        cards = [c for c in cards if c.organization_mode == organization_mode]

        # Group by primary category
        organized = {}
        for card in cards:
            category = card.primary_category or 'Uncategorized'
            if category not in organized:
                organized[category] = []
            organized[category].append(card)

        # Sort within each category
        for category in organized:
            organized[category].sort(key=lambda c: c.get_sort_key())

        return organized

    def search_cards(
        self,
        user_id: int,
        query: str,
        card_type: Optional[str] = None
    ) -> List[UnifiedCard]:
        """
        Search cards by title, player name, set name, etc.

        Args:
            user_id: User ID
            query: Search query
            card_type: Optional card type filter

        Returns:
            List of matching cards
        """
        cursor = self.db._get_cursor()

        sql = """
            SELECT * FROM card_collections
            WHERE user_id = %s
            AND (
                title ILIKE %s OR
                player_name ILIKE %s OR
                set_name ILIKE %s OR
                notes ILIKE %s
            )
        """
        params = [user_id, f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"]

        if card_type:
            sql += " AND card_type = %s"
            params.append(card_type)

        sql += " ORDER BY created_at DESC LIMIT 100"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        return [UnifiedCard.from_dict(dict(row)) for row in rows]

    # ==========================================
    # CSV IMPORT/EXPORT
    # ==========================================

    def export_to_csv(
        self,
        user_id: int,
        card_type: Optional[str] = None,
        organization_mode: Optional[str] = None
    ) -> str:
        """
        Export cards to CSV format.

        Args:
            user_id: User ID
            card_type: Optional card type filter
            organization_mode: Optional organization mode filter

        Returns:
            CSV string
        """
        cards = self.get_user_cards(user_id, card_type=card_type, organization_mode=organization_mode, limit=10000)

        if not cards:
            return ""

        # Convert to CSV rows
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=cards[0].to_csv_row().keys())

        writer.writeheader()
        for card in cards:
            writer.writerow(card.to_csv_row())

        return output.getvalue()

    def import_from_csv(
        self,
        user_id: int,
        csv_content: str,
        card_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import cards from CSV.

        Args:
            user_id: User ID
            csv_content: CSV file content as string
            card_type: Optional default card type if not in CSV

        Returns:
            Dict with import stats: {imported: int, errors: List[str]}
        """
        imported = 0
        errors = []

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
            try:
                # Determine card type
                row_card_type = row.get('Card Type') or card_type
                if not row_card_type:
                    errors.append(f"Row {row_num}: Missing card type")
                    continue

                # Get appropriate classifier
                classifier = self.classifiers.get(row_card_type)
                if not classifier:
                    errors.append(f"Row {row_num}: Unknown card type '{row_card_type}'")
                    continue

                # Create card from row
                card = classifier.classify_from_dict(row, user_id)

                # Add to database
                self.add_card(card)
                imported += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        return {
            'imported': imported,
            'errors': errors
        }

    # ==========================================
    # ORGANIZATION MODE MANAGEMENT
    # ==========================================

    def switch_organization_mode(
        self,
        user_id: int,
        new_mode: str,
        card_type: Optional[str] = None
    ):
        """
        Switch organization mode for all cards (or filtered cards).

        This will re-categorize all cards based on the new mode.

        Args:
            user_id: User ID
            new_mode: New organization mode
            card_type: Optional card type filter
        """
        cards = self.get_user_cards(user_id, card_type=card_type, limit=10000)

        for card in cards:
            card.organization_mode = new_mode
            # Re-calculate primary category
            card.primary_category = card._auto_assign_category()

            # Update in database
            self.update_card(card.id, card)

    def get_collection_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get collection statistics.

        Args:
            user_id: User ID

        Returns:
            Dict with stats
        """
        cursor = self.db._get_cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_cards,
                SUM(quantity) as total_quantity,
                COUNT(DISTINCT card_type) as card_types,
                SUM(estimated_value) as total_value,
                COUNT(CASE WHEN grading_company IS NOT NULL THEN 1 END) as graded_cards
            FROM card_collections
            WHERE user_id = %s
        """, (user_id,))

        row = cursor.fetchone()

        return dict(row) if row else {}
