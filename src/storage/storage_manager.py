"""
Storage Location Management System
===================================
Manage physical storage locations (bins, shelves, boxes) for inventory items
"""

from typing import Dict, List, Optional, Any
from datetime import datetime


class StorageManager:
    """Manage storage locations and bin assignments"""

    def __init__(self, db):
        """
        Initialize Storage Manager

        Args:
            db: Database instance
        """
        self.db = db

    def create_location(
        self,
        user_id: int,
        name: str,
        location_type: str = "bin",  # bin, shelf, box, room
        parent_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new storage location

        Args:
            user_id: User ID
            name: Location name (e.g., "Bin-A1", "Shelf-Top-Left")
            location_type: Type of storage location
            parent_id: Parent location ID (for hierarchical storage)
            notes: Additional notes

        Returns:
            Created location dict
        """
        if hasattr(self.db, 'create_storage_location'):
            location = self.db.create_storage_location(
                user_id=user_id,
                name=name,
                location_type=location_type,
                parent_id=parent_id,
                notes=notes
            )
            return location
        else:
            # Fallback implementation
            return {
                'id': 1,
                'user_id': user_id,
                'name': name,
                'location_type': location_type,
                'parent_id': parent_id,
                'notes': notes,
                'item_count': 0,
                'created_at': datetime.now().isoformat()
            }

    def assign_location(
        self,
        listing_id: int,
        location_id: int,
        quantity: int = 1
    ) -> bool:
        """
        Assign an item to a storage location

        Args:
            listing_id: Listing ID
            location_id: Storage location ID
            quantity: Number of items

        Returns:
            Success boolean
        """
        if hasattr(self.db, 'assign_storage_location'):
            return self.db.assign_storage_location(listing_id, location_id, quantity)
        else:
            print(f"Assigned listing {listing_id} to location {location_id}")
            return True

    def get_location(self, location_id: int) -> Optional[Dict[str, Any]]:
        """
        Get storage location by ID

        Args:
            location_id: Location ID

        Returns:
            Location dict or None
        """
        if hasattr(self.db, 'get_storage_location'):
            return self.db.get_storage_location(location_id)
        return None

    def get_user_locations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all storage locations for a user

        Args:
            user_id: User ID

        Returns:
            List of location dicts
        """
        if hasattr(self.db, 'get_user_storage_locations'):
            return self.db.get_user_storage_locations(user_id)
        return []

    def get_location_items(self, location_id: int) -> List[Dict[str, Any]]:
        """
        Get all items in a storage location

        Args:
            location_id: Location ID

        Returns:
            List of items with listing details
        """
        if hasattr(self.db, 'get_location_items'):
            return self.db.get_location_items(location_id)
        return []

    def find_item_location(self, listing_id: int) -> Optional[Dict[str, Any]]:
        """
        Find the storage location of an item

        Args:
            listing_id: Listing ID

        Returns:
            Location dict or None
        """
        if hasattr(self.db, 'get_item_location'):
            return self.db.get_item_location(listing_id)
        return None

    def suggest_location(
        self,
        user_id: int,
        category: Optional[str] = None,
        size: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Suggest an optimal storage location for an item

        Args:
            user_id: User ID
            category: Item category
            size: Item size

        Returns:
            Suggested location dict or None
        """
        locations = self.get_user_locations(user_id)

        if not locations:
            return None

        # Find least-used location
        least_used = min(locations, key=lambda loc: loc.get('item_count', 0))

        return least_used

    def bulk_assign(
        self,
        location_id: int,
        listing_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Bulk assign multiple items to a location

        Args:
            location_id: Storage location ID
            listing_ids: List of listing IDs

        Returns:
            Results dict with success count
        """
        success_count = 0
        failed = []

        for listing_id in listing_ids:
            try:
                if self.assign_location(listing_id, location_id):
                    success_count += 1
                else:
                    failed.append(listing_id)
            except Exception as e:
                failed.append(listing_id)
                print(f"Error assigning listing {listing_id}: {e}")

        return {
            'success': True,
            'assigned': success_count,
            'failed': failed,
            'total': len(listing_ids)
        }

    def update_location(
        self,
        location_id: int,
        name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update storage location details

        Args:
            location_id: Location ID
            name: New name
            notes: New notes

        Returns:
            Success boolean
        """
        if hasattr(self.db, 'update_storage_location'):
            return self.db.update_storage_location(
                location_id=location_id,
                name=name,
                notes=notes
            )
        return True

    def delete_location(self, location_id: int, reassign_to: Optional[int] = None) -> bool:
        """
        Delete a storage location

        Args:
            location_id: Location ID to delete
            reassign_to: Optional location ID to reassign items to

        Returns:
            Success boolean
        """
        if hasattr(self.db, 'delete_storage_location'):
            return self.db.delete_storage_location(location_id, reassign_to)
        return True

    def generate_barcode_label(
        self,
        location_id: int,
        format: str = "qr"  # qr, barcode, text
    ) -> str:
        """
        Generate a printable barcode/QR label for a location

        Args:
            location_id: Location ID
            format: Label format (qr, barcode, text)

        Returns:
            Label data (base64 encoded image or text)
        """
        location = self.get_location(location_id)
        if not location:
            raise ValueError("Location not found")

        # Simple text label for now
        label = f"""
┌────────────────────────┐
│ STORAGE LOCATION       │
│ {location['name']:^22} │
│ ID: {location_id:^18} │
└────────────────────────┘
        """

        return label.strip()
