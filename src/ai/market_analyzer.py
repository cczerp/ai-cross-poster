"""
Market Analysis - Sell-Through Rate Calculator
===============================================
Analyzes market velocity and demand for items to estimate time-to-sell.

Features:
- Sell-through rate: % of items that actually sell vs sit unsold
- Days to sell estimate: Based on current market velocity
- Demand level: High/Medium/Low based on sold listings
- Price competitiveness: Is your price good for the market?

Data sources (in order of preference):
1. eBay sold listings (public, easy to scrape)
2. Your own database (past sales of similar items)
3. AI estimation (Claude/Gemini knowledge)
"""

import os
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


class MarketAnalyzer:
    """
    Analyzes market data to calculate sell-through rates and estimate time to sell.

    Sell-through rate = (Sold items last 30 days) / (Sold + Active listings) * 100

    Example:
    - 50 sold in last 30 days
    - 200 currently listed
    - Sell-through = 50/(50+200) = 20%
    - Days to sell ≈ 30 days * (1/0.20) = 150 days (slow market)
    """

    def __init__(self, db=None):
        self.db = db

    def analyze_market(
        self,
        item_name: str,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyze market for an item and calculate sell-through rate.

        Returns:
            {
                "sell_through_rate": float,  # 0-100 percentage
                "demand_level": str,  # "High", "Medium", "Low"
                "days_to_sell_estimate": int,  # Estimated days to sell
                "sold_last_30_days": int,  # How many sold recently
                "active_listings": int,  # How many currently listed
                "average_sold_price": float,  # Average price of sold items
                "price_competitiveness": str,  # "Great", "Good", "High", "Too Low"
                "confidence": float,  # 0-1, how confident is this estimate
                "data_source": str,  # Where data came from
                "market_insights": List[str]  # Key takeaways
            }
        """

        # Try multiple data sources in order
        result = None

        # 1. Try our own database first (most reliable for items we've sold before)
        if self.db:
            result = self._analyze_from_database(item_name, brand, category)
            if result and result['confidence'] > 0.5:
                return result

        # 2. Try eBay sold listings (public data, very reliable)
        # NOTE: For now, using estimated data. In production, would scrape eBay API
        result = self._estimate_from_ai_knowledge(item_name, brand, category, price)

        return result

    def _analyze_from_database(
        self,
        item_name: str,
        brand: Optional[str],
        category: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Check our own database for similar items we've sold or listed before.

        This is the BEST data source because it's real data from OUR users.
        """
        if not self.db:
            return None

        try:
            # Search for similar collectibles in our database
            similar_items = self.db.find_similar_collectibles(
                brand=brand,
                category=category,
                limit=50
            )

            if not similar_items or len(similar_items) < 5:
                # Not enough data
                return None

            # Calculate statistics from our data
            sold_items = [item for item in similar_items if item.get('status') == 'sold']
            active_listings = [item for item in similar_items if item.get('status') == 'active']

            sold_count = len(sold_items)
            active_count = len(active_listings)

            if sold_count == 0:
                return None  # No sales data

            # Calculate sell-through rate
            total_listings = sold_count + active_count
            sell_through_rate = (sold_count / total_listings) * 100 if total_listings > 0 else 0

            # Calculate average sold price
            sold_prices = [item.get('sold_price', 0) for item in sold_items if item.get('sold_price')]
            avg_sold_price = sum(sold_prices) / len(sold_prices) if sold_prices else 0

            # Estimate days to sell based on sell-through rate
            if sell_through_rate >= 60:
                days_estimate = 7  # Fast moving
                demand_level = "High"
            elif sell_through_rate >= 30:
                days_estimate = 21  # Medium
                demand_level = "Medium"
            else:
                days_estimate = 90  # Slow
                demand_level = "Low"

            return {
                "sell_through_rate": round(sell_through_rate, 1),
                "demand_level": demand_level,
                "days_to_sell_estimate": days_estimate,
                "sold_last_30_days": sold_count,
                "active_listings": active_count,
                "average_sold_price": round(avg_sold_price, 2),
                "price_competitiveness": "Unknown",
                "confidence": 0.8,  # High confidence - real data!
                "data_source": "Your sales history",
                "market_insights": [
                    f"{sold_count} similar items sold by your users",
                    f"{sell_through_rate:.0f}% sell-through rate",
                    f"Typical selling price: ${avg_sold_price:.2f}"
                ]
            }

        except Exception as e:
            print(f"Database market analysis failed: {e}")
            return None

    def _estimate_from_ai_knowledge(
        self,
        item_name: str,
        brand: Optional[str],
        category: Optional[str],
        price: Optional[float]
    ) -> Dict[str, Any]:
        """
        Use AI knowledge and general market rules to estimate sell-through.

        This is a fallback when we don't have real data.
        Based on general collectibles market trends.
        """

        # Category-based estimates (based on industry averages)
        category_lower = (category or "").lower()

        if "trading_card" in category_lower or "pokemon" in item_name.lower():
            # Trading cards: Very liquid market
            sell_through = 45
            days_estimate = 14
            demand = "Medium-High"
            insights = ["Trading cards typically sell quickly", "High demand category"]

        elif "sports" in category_lower or any(league in item_name.upper() for league in ["MLB", "NFL", "NBA", "NHL"]):
            # Sports items: Seasonal demand
            sell_through = 35
            days_estimate = 21
            demand = "Medium"
            insights = ["Sports items sell better during season", "Moderate market velocity"]

        elif "star wars" in item_name.lower() or "marvel" in item_name.lower():
            # Pop culture collectibles: Strong demand
            sell_through = 50
            days_estimate = 10
            demand = "High"
            insights = ["Popular franchise = strong demand", "Collectors actively seeking"]

        elif "vintage" in item_name.lower() or "antique" in category_lower:
            # Vintage items: Slower, niche market
            sell_through = 15
            days_estimate = 90
            demand = "Low"
            insights = ["Vintage items need the right buyer", "Patience required"]

        elif "clothing" in category_lower or "apparel" in category_lower:
            # Clothing: Fast fashion, quick turnover
            sell_through = 40
            days_estimate = 14
            demand = "Medium"
            insights = ["Clothing sells quickly if priced right", "Size and season matter"]

        else:
            # Default for general items
            sell_through = 25
            days_estimate = 30
            demand = "Medium"
            insights = ["General market estimate", "Actual results may vary"]

        # Price competitiveness (if we have a price)
        price_comp = "Unknown"
        if price:
            # Very rough estimates - would use real comp data in production
            if price < 20:
                price_comp = "Great deal"
                days_estimate = int(days_estimate * 0.7)  # Sells faster if cheap
            elif price > 200:
                price_comp = "Premium pricing"
                days_estimate = int(days_estimate * 1.5)  # Takes longer if expensive
            else:
                price_comp = "Fair market value"

        return {
            "sell_through_rate": sell_through,
            "demand_level": demand,
            "days_to_sell_estimate": days_estimate,
            "sold_last_30_days": 0,  # Unknown
            "active_listings": 0,  # Unknown
            "average_sold_price": price or 0,
            "price_competitiveness": price_comp,
            "confidence": 0.3,  # Low confidence - just estimates
            "data_source": "AI estimation (industry averages)",
            "market_insights": insights
        }

    @classmethod
    def from_env(cls, db=None):
        """Create from environment variables"""
        return cls(db=db)
