"""
Shopping Mode & Database Lookup
================================
Look up collectibles while shopping to make informed purchase decisions.
"""

from typing import List, Dict, Any, Optional
from ..database import get_db


class ShoppingLookup:
    """
    Collectibles database lookup for shopping.

    Features:
    - Quick search by name, brand, keyword
    - Price comparison
    - Profit calculator
    - Mobile-friendly lookup
    """

    def __init__(self):
        """Initialize shopping lookup"""
        self.db = get_db()

    def quick_lookup(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Quick lookup while shopping.

        Args:
            query: Search query (name, brand, keyword)
            max_results: Maximum results to return

        Returns:
            List of matching collectibles with pricing
        """
        print(f"\n{'='*70}")
        print(f"🔍 QUICK LOOKUP: '{query}'")
        print(f"{'='*70}\n")

        # Search database
        results = self.db.search_collectibles(query=query)[:max_results]

        if not results:
            print("❌ No matches found in database")
            print("\n💡 Tip: Take a photo and use AI recognition to identify and add to database")
            return []

        # Display results
        for i, collectible in enumerate(results, 1):
            print(f"{i}. {collectible['name']}")
            if collectible['brand']:
                print(f"   Brand: {collectible['brand']}")
            if collectible['category']:
                print(f"   Category: {collectible['category']}")

            # Price info
            if collectible['estimated_value_avg']:
                low = collectible['estimated_value_low'] or 0
                high = collectible['estimated_value_high'] or 0
                avg = collectible['estimated_value_avg']

                print(f"   💰 Market Value: ${low:.2f} - ${high:.2f} (Avg: ${avg:.2f})")

            # Condition
            if collectible['condition']:
                print(f"   Condition: {collectible['condition']}")

            # Confidence
            if collectible['confidence_score']:
                confidence_pct = collectible['confidence_score'] * 100
                print(f"   Confidence: {confidence_pct:.0f}%")

            # Times found
            if collectible['times_found'] > 1:
                print(f"   📊 Found {collectible['times_found']} times")

            print()

        return results

    def profit_calculator(
        self,
        collectible_id: int,
        purchase_price: float,
        condition: Optional[str] = None,
        fees_percentage: float = 15.0,  # eBay ~13%, Mercari ~13-15%
    ) -> Dict[str, Any]:
        """
        Calculate potential profit for a collectible.

        Args:
            collectible_id: Database collectible ID
            purchase_price: What you'd pay for it
            condition: Item condition (affects value)
            fees_percentage: Platform fees (default 15%)

        Returns:
            Profit analysis dictionary
        """
        # Get collectible
        cursor = self.db._get_cursor()
        cursor.execute("SELECT * FROM collectibles WHERE id = ?", (collectible_id,))
        collectible = dict(cursor.fetchone())

        if not collectible:
            return {"error": "Collectible not found"}

        print(f"\n{'='*70}")
        print(f"💰 PROFIT CALCULATOR")
        print(f"{'='*70}")
        print(f"Item: {collectible['name']}")
        if collectible['brand']:
            print(f"Brand: {collectible['brand']}")

        # Estimated selling price
        avg_value = collectible['estimated_value_avg'] or 0
        low_value = collectible['estimated_value_low'] or avg_value
        high_value = collectible['estimated_value_high'] or avg_value

        print(f"\n📊 Market Value:")
        print(f"   Low: ${low_value:.2f}")
        print(f"   Avg: ${avg_value:.2f}")
        print(f"   High: ${high_value:.2f}")

        print(f"\n💵 Your Purchase Price: ${purchase_price:.2f}")

        # Calculate profits at different price points
        scenarios = [
            ("Conservative (Low)", low_value),
            ("Expected (Avg)", avg_value),
            ("Optimistic (High)", high_value),
        ]

        print(f"\n📈 Profit Scenarios ({fees_percentage:.0f}% fees):")
        print(f"{'':45} {'Sale':<10} {'Fees':<10} {'Profit':<10} {'ROI':<10}")
        print(f"{'-'*70}")

        best_profit = 0
        best_roi = 0

        for scenario_name, sell_price in scenarios:
            if sell_price == 0:
                continue

            fees = sell_price * (fees_percentage / 100)
            profit = sell_price - fees - purchase_price
            roi = (profit / purchase_price * 100) if purchase_price > 0 else 0

            best_profit = max(best_profit, profit)
            best_roi = max(best_roi, roi)

            # Color coding for profit
            profit_icon = "✅" if profit > 0 else "❌"

            print(f"{scenario_name:<45} ${sell_price:<9.2f} ${fees:<9.2f} ${profit:<9.2f} {roi:>6.0f}%  {profit_icon}")

        # Recommendation
        print(f"\n{'='*70}")
        if best_profit > 0:
            print(f"💡 RECOMMENDATION: {'GOOD BUY! ✅' if best_roi > 50 else 'Worth considering 👍'}")
            print(f"   Expected Profit: ${avg_value - (avg_value * fees_percentage/100) - purchase_price:.2f}")
            print(f"   Expected ROI: {((avg_value - (avg_value * fees_percentage/100) - purchase_price) / purchase_price * 100):.0f}%")
        else:
            print(f"⚠️  WARNING: May not be profitable at this price")
            print(f"   Max profit: ${best_profit:.2f}")

        print(f"{'='*70}\n")

        return {
            "collectible_name": collectible['name'],
            "purchase_price": purchase_price,
            "estimated_value": avg_value,
            "fees": avg_value * (fees_percentage / 100),
            "expected_profit": avg_value - (avg_value * fees_percentage/100) - purchase_price,
            "expected_roi": ((avg_value - (avg_value * fees_percentage/100) - purchase_price) / purchase_price * 100) if purchase_price > 0 else 0,
            "is_profitable": (avg_value - (avg_value * fees_percentage/100) - purchase_price) > 0,
        }

    def compare_prices(
        self,
        collectible_name: str,
        asking_price: float,
    ) -> Dict[str, Any]:
        """
        Compare asking price vs database market value.

        Args:
            collectible_name: Name of collectible
            asking_price: What seller is asking

        Returns:
            Price comparison analysis
        """
        # Find collectible
        collectible = self.db.find_collectible(collectible_name)

        if not collectible:
            print(f"\n❌ '{collectible_name}' not found in database")
            print("💡 Tip: Use AI recognition to identify and add to database")
            return {"error": "Not found"}

        avg_value = collectible['estimated_value_avg'] or 0
        low_value = collectible['estimated_value_low'] or avg_value
        high_value = collectible['estimated_value_high'] or avg_value

        print(f"\n{'='*70}")
        print(f"💲 PRICE COMPARISON")
        print(f"{'='*70}")
        print(f"Item: {collectible['name']}")

        print(f"\n📊 Market Value:")
        print(f"   Low: ${low_value:.2f}")
        print(f"   Avg: ${avg_value:.2f}")
        print(f"   High: ${high_value:.2f}")

        print(f"\n💵 Asking Price: ${asking_price:.2f}")

        # Calculate difference
        diff_from_avg = asking_price - avg_value
        diff_pct = (diff_from_avg / avg_value * 100) if avg_value > 0 else 0

        print(f"\n📈 Analysis:")
        if asking_price < low_value:
            print(f"   ✅ EXCELLENT DEAL! {abs(diff_pct):.0f}% below market average")
            recommendation = "BUY NOW! Great price"
        elif asking_price < avg_value:
            print(f"   ✅ Good deal - {abs(diff_pct):.0f}% below market average")
            recommendation = "Good buy"
        elif asking_price < high_value:
            print(f"   👍 Fair price - {diff_pct:.0f}% above average but within range")
            recommendation = "Fair price"
        else:
            print(f"   ⚠️  OVERPRICED - {diff_pct:.0f}% above market")
            recommendation = "Overpriced - negotiate or pass"

        print(f"\n💡 Recommendation: {recommendation}")
        print(f"{'='*70}\n")

        return {
            "collectible_name": collectible['name'],
            "asking_price": asking_price,
            "market_avg": avg_value,
            "market_low": low_value,
            "market_high": high_value,
            "difference": diff_from_avg,
            "difference_pct": diff_pct,
            "recommendation": recommendation,
        }

    def get_top_collectibles(self, limit: int = 20) -> List[Dict]:
        """Get most frequently found collectibles"""
        cursor = self.db._get_cursor()
        cursor.execute("""
            SELECT * FROM collectibles
            ORDER BY times_found DESC, estimated_value_avg DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_high_value_collectibles(
        self,
        min_value: float = 100.0,
        limit: int = 20
    ) -> List[Dict]:
        """Get high-value collectibles to watch for"""
        cursor = self.db._get_cursor()
        cursor.execute("""
            SELECT * FROM collectibles
            WHERE estimated_value_avg >= ?
            ORDER BY estimated_value_avg DESC
            LIMIT ?
        """, (min_value, limit))
        return [dict(row) for row in cursor.fetchall()]

    @classmethod
    def from_env(cls) -> "ShoppingLookup":
        """Create shopping lookup instance"""
        return cls()


# Convenience functions
def quick_lookup(query: str, max_results: int = 5) -> List[Dict]:
    """Quick lookup collectible while shopping"""
    lookup = ShoppingLookup()
    return lookup.quick_lookup(query, max_results)


def profit_calculator(
    collectible_id: int,
    purchase_price: float,
    fees_percentage: float = 15.0
) -> Dict:
    """Calculate potential profit"""
    lookup = ShoppingLookup()
    return lookup.profit_calculator(collectible_id, purchase_price, fees_percentage=fees_percentage)


def compare_prices(collectible_name: str, asking_price: float) -> Dict:
    """Compare asking price vs market value"""
    lookup = ShoppingLookup()
    return lookup.compare_prices(collectible_name, asking_price)
