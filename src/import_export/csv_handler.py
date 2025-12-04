"""
CSV Import/Export System
========================
Handles importing CSV files from various marketplaces and exporting unified CSVs
"""

import csv
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import io

from ..database import get_db


class CSVImportExport:
    """Handles CSV import/export operations for various marketplaces"""

    # Marketplace CSV field mappings
    MARKETPLACE_MAPPINGS = {
        'mercari': {
            'title': ['title', 'item_name'],
            'description': ['description', 'item_description'],
            'price': ['price', 'item_price'],
            'condition': ['condition', 'item_condition'],
            'category': ['category', 'item_category'],
            'sku': ['sku', 'item_sku'],
            'upc': ['upc', 'item_upc'],
            'quantity': ['quantity', 'item_quantity'],
            'photos': ['photos', 'image_urls', 'photo_urls'],
            'storage_location': ['storage_location', 'location', 'bin']
        },
        'poshmark': {
            'title': ['title', 'item_title'],
            'description': ['description', 'item_description'],
            'price': ['price', 'item_price'],
            'condition': ['condition', 'item_condition'],
            'category': ['category', 'item_category'],
            'sku': ['sku', 'item_sku'],
            'upc': ['upc', 'item_upc'],
            'quantity': ['quantity', 'item_quantity'],
            'photos': ['photos', 'image_urls'],
            'storage_location': ['storage_location', 'location', 'bin']
        },
        'ebay': {
            'title': ['title', 'item_title'],
            'description': ['description', 'item_description'],
            'price': ['price', 'start_price', 'current_price'],
            'condition': ['condition', 'item_condition'],
            'category': ['category', 'primary_category'],
            'sku': ['sku', 'custom_label'],
            'upc': ['upc', 'product_upc'],
            'quantity': ['quantity', 'quantity_available'],
            'photos': ['photo_urls', 'picture_urls', 'gallery_urls'],
            'storage_location': ['storage_location', 'location', 'bin']
        },
        'etsy': {
            'title': ['title', 'item_name'],
            'description': ['description', 'item_description'],
            'price': ['price', 'item_price'],
            'condition': ['condition', 'item_condition'],
            'category': ['category', 'item_category'],
            'sku': ['sku', 'item_sku'],
            'upc': ['upc', 'item_upc'],
            'quantity': ['quantity', 'item_quantity'],
            'photos': ['photos', 'image_urls'],
            'storage_location': ['storage_location', 'location', 'bin']
        },
        'facebook_marketplace': {
            'title': ['title', 'name'],
            'description': ['description', 'description'],
            'price': ['price', 'price'],
            'condition': ['condition', 'condition'],
            'category': ['category', 'category'],
            'sku': ['sku', 'sku'],
            'upc': ['upc', 'upc'],
            'quantity': ['quantity', 'quantity'],
            'photos': ['photos', 'image_urls', 'images'],
            'storage_location': ['storage_location', 'location', 'bin']
        }
    }

    # Condition mappings to standardize conditions
    CONDITION_MAPPINGS = {
        'mercari': {
            '新品・未使用': 'new',
            '未使用に近い': 'like_new',
            '目立った傷や汚れなし': 'excellent',
            'やや傷や汚れあり': 'good',
            '傷や汚れあり': 'fair',
            '全体的に状態が悪い': 'poor'
        },
        'poshmark': {
            'new': 'new',
            'new_with_tags': 'new_with_tags',
            'new_without_tags': 'new_without_tags',
            'like_new': 'like_new',
            'excellent': 'excellent',
            'good': 'good',
            'fair': 'fair',
            'poor': 'poor'
        },
        'ebay': {
            'New': 'new',
            'New: With Tags': 'new_with_tags',
            'New without Tags': 'new_without_tags',
            'Like New': 'like_new',
            'Excellent': 'excellent',
            'Good': 'good',
            'Fair': 'fair',
            'Poor': 'poor'
        }
    }

    def __init__(self):
        self.db = get_db()

    def import_csv(self, file_path: str, marketplace: str, user_id: int,
                   auto_assign_sku: bool = True, import_mode: str = 'draft') -> Dict[str, Any]:
        """
        Import CSV file from a marketplace

        Args:
            file_path: Path to CSV file
            marketplace: Marketplace name (mercari, poshmark, ebay, etc.)
            user_id: User ID
            auto_assign_sku: Whether to auto-assign SKUs for items without them
            import_mode: 'draft' or 'direct' - whether to import as drafts or active listings

        Returns:
            Dict with import results
        """
        results = {
            'total_rows': 0,
            'imported': 0,
            'skipped': 0,
            'errors': [],
            'duplicates': []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Try to detect delimiter
                sample = f.read(1024)
                f.seek(0)
                delimiter = self._detect_delimiter(sample)

                reader = csv.DictReader(f, delimiter=delimiter)

                for row_num, row in enumerate(reader, 1):
                    results['total_rows'] = row_num

                    try:
                        # Normalize the row data
                        normalized_data = self._normalize_row(row, marketplace)

                        # Check for duplicates
                        if self._is_duplicate(normalized_data, user_id):
                            results['duplicates'].append({
                                'row': row_num,
                                'title': normalized_data.get('title', 'Unknown')
                            })
                            results['skipped'] += 1
                            continue

                        # Auto-assign SKU if needed
                        if auto_assign_sku and not normalized_data.get('sku'):
                            normalized_data['sku'] = self.db.generate_auto_sku(user_id)

                        # Create listing
                        listing_id = self._create_listing_from_normalized_data(
                            normalized_data, user_id, import_mode
                        )

                        results['imported'] += 1

                    except Exception as e:
                        results['errors'].append({
                            'row': row_num,
                            'error': str(e),
                            'data': row
                        })

        except Exception as e:
            results['errors'].append({
                'row': 0,
                'error': f"File read error: {str(e)}"
            })

        return results

    def export_csv(self, user_id: int, export_type: str = 'all',
                   marketplace_format: Optional[str] = None) -> str:
        """
        Export listings to CSV

        Args:
            user_id: User ID
            export_type: 'all', 'drafts', 'active', 'sold'
            marketplace_format: Optional marketplace format to export in

        Returns:
            CSV content as string
        """
        # Get listings based on export type
        listings = self._get_listings_for_export(user_id, export_type)

        if not listings:
            return ""

        # Create CSV output
        output = io.StringIO()
        fieldnames = self._get_export_fieldnames(marketplace_format)

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for listing in listings:
            row = self._format_listing_for_export(listing, marketplace_format)
            writer.writerow(row)

        return output.getvalue()

    def _normalize_row(self, row: Dict[str, str], marketplace: str) -> Dict[str, Any]:
        """Normalize a CSV row to unified format"""
        normalized = {}

        # Get field mappings for this marketplace
        mappings = self.MARKETPLACE_MAPPINGS.get(marketplace, {})

        # Map fields
        for unified_field, possible_fields in mappings.items():
            value = self._find_field_value(row, possible_fields)
            if value:
                normalized[unified_field] = self._normalize_field_value(unified_field, value, marketplace)

        # Generate UUID if not present
        if 'listing_uuid' not in normalized:
            normalized['listing_uuid'] = str(uuid.uuid4())

        return normalized

    def _find_field_value(self, row: Dict[str, str], possible_fields: List[str]) -> Optional[str]:
        """Find a field value from possible field names (case-insensitive)"""
        for field in possible_fields:
            # Try exact match first
            if field in row and row[field]:
                return row[field]

            # Try case-insensitive match
            for row_field in row.keys():
                if row_field.lower() == field.lower() and row[row_field]:
                    return row[row_field]

        return None

    def _normalize_field_value(self, field: str, value: str, marketplace: str) -> Any:
        """Normalize a field value based on field type"""
        if field == 'price':
            # Remove currency symbols and convert to float
            value = value.replace('$', '').replace('¥', '').replace('€', '').strip()
            try:
                return float(value)
            except ValueError:
                return 0.0

        elif field == 'condition':
            # Map marketplace-specific conditions to unified conditions
            condition_maps = self.CONDITION_MAPPINGS.get(marketplace, {})
            return condition_maps.get(value, value.lower())

        elif field == 'quantity':
            try:
                return int(value)
            except ValueError:
                return 1

        elif field == 'photos':
            # Try to parse as JSON array, otherwise split by comma
            try:
                photos = json.loads(value)
                return photos if isinstance(photos, list) else [value]
            except (json.JSONDecodeError, TypeError):
                return [url.strip() for url in value.split(',') if url.strip()]

        return value

    def _is_duplicate(self, normalized_data: Dict[str, Any], user_id: int) -> bool:
        """Check if this listing is a duplicate"""
        title = normalized_data.get('title', '').strip()
        if not title:
            return False

        # Check for exact title match
        existing = self.db.search_listings_by_title(user_id, title)
        return len(existing) > 0

    def _create_listing_from_normalized_data(self, data: Dict[str, Any],
                                           user_id: int, import_mode: str) -> int:
        """Create a listing from normalized data"""
        # Set status based on import mode
        status = 'draft' if import_mode == 'draft' else 'active'

        return self.db.create_listing(
            listing_uuid=data['listing_uuid'],
            title=data.get('title', 'Untitled'),
            description=data.get('description', ''),
            price=data.get('price', 0.0),
            condition=data.get('condition', 'good'),
            photos=data.get('photos', []),
            user_id=user_id,
            category=data.get('category'),
            sku=data.get('sku'),
            upc=data.get('upc'),
            quantity=data.get('quantity', 1),
            status=status,
            storage_location=data.get('storage_location')
        )

    def _get_listings_for_export(self, user_id: int, export_type: str) -> List[Dict]:
        """Get listings for export based on type"""
        if export_type == 'drafts':
            return self.db.get_drafts(user_id=user_id)
        elif export_type == 'active':
            return self.db.get_active_listings(user_id)
        elif export_type == 'sold':
            # Get sold listings (would need to implement this method)
            return []
        else:  # 'all'
            # Get all listings for user
            cursor = self.db._get_cursor()
            cursor.execute("""
                SELECT * FROM listings
                WHERE user_id::text = %s::text
                ORDER BY created_at DESC
            """, (str(user_id),))
            return [dict(row) for row in cursor.fetchall()]

    def _get_export_fieldnames(self, marketplace_format: Optional[str]) -> List[str]:
        """Get field names for export"""
        if marketplace_format and marketplace_format in self.MARKETPLACE_MAPPINGS:
            # Use marketplace-specific fields
            mappings = self.MARKETPLACE_MAPPINGS[marketplace_format]
            return list(mappings.keys())
        else:
            # Use unified format
            return ['title', 'description', 'price', 'condition', 'category',
                   'sku', 'upc', 'quantity', 'photos', 'status']

    def _format_listing_for_export(self, listing: Dict, marketplace_format: Optional[str]) -> Dict:
        """Format a listing for export"""
        # Parse JSON fields
        photos = []
        if listing.get('photos'):
            try:
                photos = json.loads(listing['photos'])
            except:
                photos = []

        row = {
            'title': listing.get('title', ''),
            'description': listing.get('description', ''),
            'price': listing.get('price', 0.0),
            'condition': listing.get('condition', ''),
            'category': listing.get('category', ''),
            'sku': listing.get('sku', ''),
            'upc': listing.get('upc', ''),
            'quantity': listing.get('quantity', 1),
            'photos': ','.join(photos) if photos else '',
            'storage_location': listing.get('storage_location', ''),
            'status': listing.get('status', '')
        }

        return row

    def _detect_delimiter(self, sample: str) -> str:
        """Detect CSV delimiter from sample"""
        delimiters = [',', '\t', ';', '|']
        counts = {}

        for delimiter in delimiters:
            counts[delimiter] = sample.count(delimiter)

        return max(counts, key=counts.get) if counts else ','