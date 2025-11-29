"""
Sales Sync Engine for AI Cross-Poster
=====================================
Detect sales, pull buyer info, notify users, and trigger auto-delisting
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json


class SalesSyncEngine:
    """Synchronize sales data across platforms"""

    def __init__(self, db, notification_manager=None):
        """
        Initialize Sales Sync Engine

        Args:
            db: Database instance
            notification_manager: NotificationManager instance (optional)
        """
        self.db = db
        self.notification_manager = notification_manager

    def detect_sale(
        self,
        listing_id: int,
        platform: str,
        sale_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detect and process a sale

        Args:
            listing_id: Listing ID
            platform: Platform where sale occurred
            sale_data: Sale information from platform

        Returns:
            Processing results
        """
        # Extract sale information
        sold_price = sale_data.get('price')
        buyer_info = sale_data.get('buyer', {})
        transaction_id = sale_data.get('transaction_id')
        sale_date = sale_data.get('sale_date', datetime.now())

        # Get listing details
        listing = self.db.get_listing(listing_id)
        if not listing:
            return {'success': False, 'error': 'Listing not found'}

        # Mark as sold in database
        self.db.mark_listing_sold(
            listing_id=listing_id,
            platform=platform,
            sold_price=sold_price,
            sale_date=sale_date,
            transaction_id=transaction_id
        )

        # Store buyer information
        if hasattr(self.db, 'save_buyer_info'):
            self.db.save_buyer_info(
                listing_id=listing_id,
                buyer_info=buyer_info
            )

        # Get storage location
        storage_location = None
        if hasattr(self.db, 'get_item_location'):
            storage_location = self.db.get_item_location(listing_id)

        # Calculate fees and profit
        from src.accounting import TaxReportGenerator
        tax_gen = TaxReportGenerator(self.db)
        fees = tax_gen.calculate_platform_fees(platform, sold_price or listing.get('price', 0))

        cost = listing.get('cost', 0) or 0
        net_profit = (sold_price or 0) - fees['total_fees'] - cost

        # Save transaction data
        if hasattr(self.db, 'save_transaction'):
            self.db.save_transaction(
                listing_id=listing_id,
                platform=platform,
                sale_price=sold_price,
                fees=fees['total_fees'],
                cost=cost,
                net_profit=net_profit,
                sale_date=sale_date
            )

        # Send notification
        self._notify_sale(
            user_id=listing.get('user_id'),
            listing=listing,
            platform=platform,
            sold_price=sold_price,
            buyer_info=buyer_info,
            storage_location=storage_location,
            net_profit=net_profit
        )

        # Schedule auto-delist (15 minute delay)
        self._schedule_auto_delist(
            listing_id=listing_id,
            sold_platform=platform,
            delay_minutes=15
        )

        return {
            'success': True,
            'listing_id': listing_id,
            'platform': platform,
            'sold_price': sold_price,
            'net_profit': net_profit,
            'storage_location': storage_location,
            'buyer_info': buyer_info
        }

    def _notify_sale(
        self,
        user_id: int,
        listing: Dict[str, Any],
        platform: str,
        sold_price: float,
        buyer_info: Dict[str, str],
        storage_location: Optional[Dict[str, Any]],
        net_profit: float
    ):
        """Send sale notification to user"""
        title = f"🎉 Sale on {platform.title()}!"

        message = f"""
        {listing.get('title', 'Item')} sold for ${sold_price:.2f}

        Net Profit: ${net_profit:.2f}
        Buyer: {buyer_info.get('name', 'N/A')}
        """

        if storage_location:
            message += f"\nStorage: {storage_location.get('name', 'N/A')}"

        # Create database notification
        if hasattr(self.db, 'create_notification'):
            self.db.create_notification(
                user_id=user_id,
                type='sale',
                title=title,
                message=message.strip(),
                listing_id=listing.get('id'),
                platform=platform,
                data={
                    'buyer': buyer_info,
                    'sold_price': sold_price,
                    'net_profit': net_profit,
                    'storage_location': storage_location
                }
            )

        # Send email notification (if configured)
        if self.notification_manager:
            try:
                self.notification_manager.send_email(
                    to=self.db.get_user_email(user_id),
                    subject=title,
                    body=message
                )
            except Exception as e:
                print(f"Failed to send email notification: {e}")

    def _schedule_auto_delist(
        self,
        listing_id: int,
        sold_platform: str,
        delay_minutes: int = 15
    ):
        """Schedule automatic delisting from other platforms"""
        # Use the lifecycle manager
        from src.automation import ItemLifecycleManager

        lifecycle = ItemLifecycleManager(self.db)

        # This will handle the delayed delisting
        lifecycle.mark_item_sold(
            listing_id=listing_id,
            platform=sold_platform,
            auto_delist=True,
            delist_delay_minutes=delay_minutes
        )

    def sync_platform_sales(
        self,
        user_id: int,
        platform: str
    ) -> Dict[str, Any]:
        """
        Sync sales from a specific platform

        Args:
            user_id: User ID
            platform: Platform to sync from

        Returns:
            Sync results
        """
        results = {
            'success': True,
            'platform': platform,
            'sales_detected': 0,
            'errors': []
        }

        try:
            # Get platform adapter
            from src.adapters import get_adapter
            adapter = get_adapter(platform)

            # Fetch recent sales
            sales = adapter.fetch_recent_sales(user_id)

            for sale in sales:
                try:
                    listing_id = sale.get('listing_id')
                    if listing_id:
                        self.detect_sale(listing_id, platform, sale)
                        results['sales_detected'] += 1
                except Exception as e:
                    results['errors'].append({
                        'sale': sale,
                        'error': str(e)
                    })

        except Exception as e:
            results['success'] = False
            results['error'] = str(e)

        return results

    def sync_all_platforms(self, user_id: int) -> Dict[str, Any]:
        """
        Sync sales from all connected platforms

        Args:
            user_id: User ID

        Returns:
            Combined sync results
        """
        platforms = ['ebay', 'etsy', 'mercari', 'poshmark', 'shopify']
        results = {
            'success': True,
            'total_sales': 0,
            'platforms': {}
        }

        for platform in platforms:
            try:
                platform_result = self.sync_platform_sales(user_id, platform)
                results['platforms'][platform] = platform_result
                results['total_sales'] += platform_result.get('sales_detected', 0)
            except Exception as e:
                results['platforms'][platform] = {
                    'success': False,
                    'error': str(e)
                }

        return results

    def get_sale_details(self, listing_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed sale information for a listing

        Args:
            listing_id: Listing ID

        Returns:
            Sale details dict or None
        """
        if hasattr(self.db, 'get_sale_details'):
            return self.db.get_sale_details(listing_id)

        # Fallback implementation
        listing = self.db.get_listing(listing_id)
        if listing and listing.get('status') == 'sold':
            return {
                'listing_id': listing_id,
                'sold_date': listing.get('sold_date'),
                'sold_price': listing.get('sold_price'),
                'platform': listing.get('platform'),
                'buyer_info': {},
                'net_profit': 0
            }

        return None
