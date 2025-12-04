"""
SEO Automation System
====================
Automatically generates SEO-optimized titles, keywords, and metadata
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter
import json

from ..database import get_db


class SEOAutomation:
    """Handles SEO optimization for listings"""

    def __init__(self):
        self.db = get_db()

        # SEO keywords by category
        self.category_keywords = {
            'clothing': ['vintage', 'retro', 'brand', 'size', 'condition', 'authentic', 'original'],
            'shoes': ['size', 'brand', 'condition', 'authentic', 'vintage', 'rare', 'limited'],
            'electronics': ['working', 'tested', 'brand', 'model', 'condition', 'original', 'rare'],
            'collectibles': ['rare', 'vintage', 'authentic', 'mint', 'original', 'limited', 'brand'],
            'sports': ['autographed', 'game used', 'vintage', 'rare', 'authentic', 'brand'],
            'books': ['first edition', 'signed', 'rare', 'vintage', 'collectible', 'author'],
            'toys': ['vintage', 'rare', 'complete', 'original', 'brand', 'collectible']
        }

        # Brand value multipliers (higher = more valuable for SEO)
        self.brand_multipliers = {
            'supreme': 3.0, 'nike': 2.5, 'adidas': 2.3, 'gucci': 3.2, 'louis vuitton': 3.1,
            'chanel': 3.0, 'prada': 2.8, 'hermes': 3.3, 'role': 2.9, 'off-white': 2.7,
            'stone island': 2.6, 'palace': 2.4, 'bape': 2.5, 'yeezy': 2.8, 'jordan': 2.9
        }

    def optimize_listing_seo(self, listing_id: int) -> Dict[str, Any]:
        """
        Optimize SEO for a listing

        Args:
            listing_id: Listing ID

        Returns:
            SEO optimization results
        """
        listing = self.db.get_listing(listing_id)
        if not listing:
            return {'error': 'Listing not found'}

        # Generate optimized title
        optimized_title = self.generate_seo_title(listing)

        # Generate keywords and hashtags
        keywords = self.generate_keywords(listing)
        hashtags = self.generate_hashtags(listing)

        # Create SEO data
        seo_data = {
            'keywords': keywords,
            'hashtags': hashtags,
            'search_terms': self.generate_search_terms(listing),
            'optimized_title': optimized_title,
            'seo_score': self.calculate_seo_score(listing, optimized_title, keywords)
        }

        # Update listing with SEO data
        self.db.update_listing(
            listing_id,
            title=optimized_title,
            attributes=json.dumps({
                **(json.loads(listing.get('attributes', '{}')) or {}),
                'seo_data': seo_data
            })
        )

        return {
            'listing_id': listing_id,
            'original_title': listing['title'],
            'optimized_title': optimized_title,
            'keywords': keywords,
            'hashtags': hashtags,
            'seo_score': seo_data['seo_score']
        }

    def generate_seo_title(self, listing: Dict) -> str:
        """Generate an SEO-optimized title"""
        title_parts = []

        # Extract brand if present
        brand = self._extract_brand(listing)
        if brand:
            title_parts.append(brand.title())

        # Add key attributes
        condition = listing.get('condition', '').lower()
        if condition in ['new', 'like_new', 'excellent']:
            title_parts.append(condition.replace('_', ' ').title())

        # Add category/size info
        category = listing.get('category', '').lower()
        if category:
            title_parts.append(category.title())

        # Add size if clothing
        attributes = json.loads(listing.get('attributes', '{}')) or {}
        size = attributes.get('size')
        if size:
            title_parts.append(f"Size {size}")

        # Add year/model for collectibles
        year = attributes.get('year')
        if year:
            title_parts.append(str(year))

        # Add original title keywords
        original_keywords = self._extract_key_terms(listing['title'])
        title_parts.extend(original_keywords[:2])  # Limit to 2 additional terms

        # Ensure title is within limits
        full_title = ' '.join(title_parts)
        if len(full_title) > 80:  # eBay limit
            # Truncate intelligently
            full_title = self._truncate_title_smartly(full_title, 80)

        return full_title

    def generate_keywords(self, listing: Dict) -> List[str]:
        """Generate SEO keywords for the listing"""
        keywords = set()

        # Add category-specific keywords
        category = listing.get('category', '').lower()
        if category in self.category_keywords:
            keywords.update(self.category_keywords[category])

        # Extract from title
        title_keywords = self._extract_key_terms(listing['title'])
        keywords.update(title_keywords)

        # Extract from description
        if listing.get('description'):
            desc_keywords = self._extract_key_terms(listing['description'])
            keywords.update(desc_keywords[:5])  # Limit description keywords

        # Add brand if detected
        brand = self._extract_brand(listing)
        if brand:
            keywords.add(brand.lower())

        # Add condition keywords
        condition = listing.get('condition', '').lower()
        if condition:
            keywords.add(condition)

        # Add attributes as keywords
        attributes = json.loads(listing.get('attributes', '{}')) or {}
        for key, value in attributes.items():
            if isinstance(value, str) and len(value) < 20:  # Avoid long values
                keywords.add(value.lower())

        # Filter and rank keywords
        filtered_keywords = [k for k in keywords if len(k) > 2 and not k.isdigit()]
        return self._rank_keywords(filtered_keywords, listing)[:10]  # Top 10

    def generate_hashtags(self, listing: Dict) -> List[str]:
        """Generate relevant hashtags"""
        hashtags = []

        # Brand hashtag
        brand = self._extract_brand(listing)
        if brand:
            hashtags.append(f"#{brand.replace(' ', '').lower()}")

        # Category hashtag
        category = listing.get('category', '').lower()
        if category:
            hashtags.append(f"#{category.replace(' ', '').lower()}")

        # Condition hashtag
        condition = listing.get('condition', '').lower()
        if condition in ['new', 'vintage', 'rare']:
            hashtags.append(f"#{condition}")

        # Popular general hashtags
        general_hashtags = ['#forsale', '#vintage', '#collectibles', '#resell']
        hashtags.extend(general_hashtags)

        return list(set(hashtags))  # Remove duplicates

    def generate_search_terms(self, listing: Dict) -> List[str]:
        """Generate search terms for the listing"""
        search_terms = []

        # Brand + category combinations
        brand = self._extract_brand(listing)
        category = listing.get('category', '').lower()

        if brand and category:
            search_terms.append(f"{brand} {category}")
            search_terms.append(f"{category} {brand}")

        # Brand + condition
        condition = listing.get('condition', '').lower()
        if brand and condition:
            search_terms.append(f"{brand} {condition}")

        # Add some popular search terms
        search_terms.extend([
            "vintage clothing",
            "designer brands",
            "collectible items",
            "rare finds"
        ])

        return search_terms

    def calculate_seo_score(self, listing: Dict, optimized_title: str, keywords: List[str]) -> float:
        """Calculate SEO score for the listing"""
        score = 0.0

        # Title optimization (40% of score)
        title_score = 0.0
        if 30 <= len(optimized_title) <= 80:
            title_score += 30  # Good length
        if any(k.lower() in optimized_title.lower() for k in keywords[:3]):
            title_score += 10  # Contains top keywords

        # Keywords (30% of score)
        keyword_score = min(len(keywords) * 3, 30)  # Up to 10 keywords = 30 points

        # Brand recognition (20% of score)
        brand_score = 0.0
        brand = self._extract_brand(listing)
        if brand and brand.lower() in self.brand_multipliers:
            brand_score = 20 * min(self.brand_multipliers[brand.lower()], 1.0)

        # Description quality (10% of score)
        desc_score = 0.0
        description = listing.get('description', '')
        if len(description) > 50:
            desc_score += 5
        if len(description) > 100:
            desc_score += 5

        total_score = title_score + keyword_score + brand_score + desc_score
        return min(total_score, 100.0)  # Cap at 100

    def _extract_brand(self, listing: Dict) -> Optional[str]:
        """Extract brand from listing data"""
        # Check attributes first
        attributes = json.loads(listing.get('attributes', '{}')) or {}
        brand = attributes.get('brand')
        if brand:
            return brand

        # Check title for brand keywords
        title_lower = listing['title'].lower()
        for brand_name in self.brand_multipliers.keys():
            if brand_name in title_lower:
                return brand_name.title()

        return None

    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text"""
        # Remove punctuation and split
        words = re.findall(r'\b\w+\b', text.lower())

        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'size', 'condition', 'brand'}
        filtered_words = [w for w in words if w not in stop_words and len(w) > 2]

        # Count frequency
        word_counts = Counter(filtered_words)

        # Return most common words
        return [word for word, count in word_counts.most_common(10)]

    def _rank_keywords(self, keywords: List[str], listing: Dict) -> List[str]:
        """Rank keywords by relevance"""
        scored_keywords = []

        for keyword in keywords:
            score = 1.0

            # Boost brand keywords
            if keyword in self.brand_multipliers:
                score *= self.brand_multipliers[keyword]

            # Boost condition keywords
            if keyword in ['new', 'vintage', 'rare', 'authentic', 'mint']:
                score *= 1.5

            # Boost category-specific keywords
            category = listing.get('category', '').lower()
            if category in self.category_keywords and keyword in self.category_keywords[category]:
                score *= 1.3

            scored_keywords.append((keyword, score))

        # Sort by score and return keywords
        scored_keywords.sort(key=lambda x: x[1], reverse=True)
        return [k for k, s in scored_keywords]

    def _truncate_title_smartly(self, title: str, max_length: int) -> str:
        """Truncate title while preserving important parts"""
        if len(title) <= max_length:
            return title

        words = title.split()
        result = ""

        for word in words:
            if len(result + " " + word) <= max_length:
                result += " " + word if result else word
            else:
                break

        return result

    def bulk_optimize_seo(self, user_id: int, listing_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """Bulk optimize SEO for multiple listings"""
        if listing_ids is None:
            # Get all active listings for user
            listings = self.db.get_active_listings(user_id)
            listing_ids = [l['id'] for l in listings]

        results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'results': []
        }

        for listing_id in listing_ids:
            try:
                result = self.optimize_listing_seo(listing_id)
                results['results'].append(result)
                results['successful'] += 1
            except Exception as e:
                results['results'].append({
                    'listing_id': listing_id,
                    'error': str(e)
                })
                results['failed'] += 1

            results['total_processed'] += 1

        return results

    def sync_seo_across_platforms(self, listing_id: int):
        """Sync SEO changes across all platforms where listing is posted"""
        # This would update the SEO-optimized title on all platforms
        # TODO: Implement platform-specific SEO syncing
        pass