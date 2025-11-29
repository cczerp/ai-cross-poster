"""
Feed Generator for Catalog Platforms
====================================
Generates product feeds in various formats for Facebook, Google Shopping, Pinterest
"""

import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from io import StringIO


class FeedFormat(Enum):
    """Supported feed formats"""
    CSV = "csv"
    XML = "xml"
    RSS = "rss"
    JSON = "json"


class FeedGenerator:
    """Generate product feeds for catalog platforms"""

    @staticmethod
    def generate_facebook_feed(listings: List[Dict[str, Any]], format: FeedFormat = FeedFormat.CSV) -> str:
        """
        Generate Facebook Product Catalog feed

        Args:
            listings: List of listing dictionaries
            format: Output format (CSV, XML, or JSON)

        Returns:
            Feed content as string
        """
        if format == FeedFormat.CSV:
            return FeedGenerator._generate_facebook_csv(listings)
        elif format == FeedFormat.XML:
            return FeedGenerator._generate_facebook_xml(listings)
        elif format == FeedFormat.JSON:
            import json
            return json.dumps([FeedGenerator._format_facebook_item(l) for l in listings], indent=2)
        else:
            raise ValueError(f"Unsupported format for Facebook: {format}")

    @staticmethod
    def _format_facebook_item(listing: Dict[str, Any]) -> Dict[str, str]:
        """Format a single listing for Facebook catalog"""
        photos = listing.get('photos', [])
        photo_url = photos[0] if photos else ''

        return {
            'id': str(listing.get('id', '')),
            'title': listing.get('title', '')[:100],
            'description': listing.get('description', '')[:5000],
            'availability': 'in stock' if listing.get('status') == 'active' else 'out of stock',
            'condition': listing.get('condition', 'used'),
            'price': f"{listing.get('price', 0):.2f} USD",
            'link': listing.get('link', ''),
            'image_link': photo_url,
            'brand': listing.get('brand', ''),
            'google_product_category': listing.get('category', ''),
        }

    @staticmethod
    def _generate_facebook_csv(listings: List[Dict[str, Any]]) -> str:
        """Generate Facebook feed in CSV format"""
        output = StringIO()
        fieldnames = ['id', 'title', 'description', 'availability', 'condition',
                     'price', 'link', 'image_link', 'brand', 'google_product_category']

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for listing in listings:
            writer.writerow(FeedGenerator._format_facebook_item(listing))

        return output.getvalue()

    @staticmethod
    def _generate_facebook_xml(listings: List[Dict[str, Any]]) -> str:
        """Generate Facebook feed in XML format"""
        root = ET.Element('rss', version='2.0')
        root.set('xmlns:g', 'http://base.google.com/ns/1.0')

        channel = ET.SubElement(root, 'channel')
        ET.SubElement(channel, 'title').text = 'Product Catalog'
        ET.SubElement(channel, 'link').text = 'https://example.com'
        ET.SubElement(channel, 'description').text = 'Product feed'

        for listing in listings:
            item = ET.SubElement(channel, 'item')
            formatted = FeedGenerator._format_facebook_item(listing)

            for key, value in formatted.items():
                ET.SubElement(item, f'g:{key}').text = str(value)

        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')

    @staticmethod
    def generate_google_shopping_feed(listings: List[Dict[str, Any]], format: FeedFormat = FeedFormat.XML) -> str:
        """
        Generate Google Shopping Product Feed

        Args:
            listings: List of listing dictionaries
            format: Output format (XML or CSV)

        Returns:
            Feed content as string
        """
        if format == FeedFormat.XML:
            return FeedGenerator._generate_google_xml(listings)
        elif format == FeedFormat.CSV:
            return FeedGenerator._generate_google_csv(listings)
        else:
            raise ValueError(f"Unsupported format for Google Shopping: {format}")

    @staticmethod
    def _format_google_item(listing: Dict[str, Any]) -> Dict[str, str]:
        """Format a single listing for Google Shopping"""
        photos = listing.get('photos', [])
        photo_url = photos[0] if photos else ''

        return {
            'id': str(listing.get('id', '')),
            'title': listing.get('title', '')[:150],
            'description': listing.get('description', '')[:5000],
            'link': listing.get('link', ''),
            'image_link': photo_url,
            'additional_image_link': ','.join(photos[1:4]) if len(photos) > 1 else '',
            'condition': listing.get('condition', 'used'),
            'availability': 'in stock' if listing.get('status') == 'active' else 'out of stock',
            'price': f"{listing.get('price', 0):.2f} USD",
            'brand': listing.get('brand', ''),
            'gtin': listing.get('upc', ''),
            'mpn': listing.get('sku', ''),
            'google_product_category': listing.get('category', ''),
            'product_type': listing.get('category', ''),
            'shipping_weight': f"{listing.get('weight', 0)} lb",
        }

    @staticmethod
    def _generate_google_xml(listings: List[Dict[str, Any]]) -> str:
        """Generate Google Shopping feed in XML format"""
        root = ET.Element('rss', version='2.0')
        root.set('xmlns:g', 'http://base.google.com/ns/1.0')

        channel = ET.SubElement(root, 'channel')
        ET.SubElement(channel, 'title').text = 'Product Feed'
        ET.SubElement(channel, 'link').text = 'https://example.com'
        ET.SubElement(channel, 'description').text = 'Google Shopping product feed'

        for listing in listings:
            item = ET.SubElement(channel, 'item')
            formatted = FeedGenerator._format_google_item(listing)

            for key, value in formatted.items():
                if value:  # Only include non-empty values
                    ET.SubElement(item, f'g:{key}').text = str(value)

        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')

    @staticmethod
    def _generate_google_csv(listings: List[Dict[str, Any]]) -> str:
        """Generate Google Shopping feed in CSV format"""
        output = StringIO()
        fieldnames = ['id', 'title', 'description', 'link', 'image_link', 'additional_image_link',
                     'condition', 'availability', 'price', 'brand', 'gtin', 'mpn',
                     'google_product_category', 'product_type', 'shipping_weight']

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for listing in listings:
            writer.writerow(FeedGenerator._format_google_item(listing))

        return output.getvalue()

    @staticmethod
    def generate_pinterest_feed(listings: List[Dict[str, Any]], format: FeedFormat = FeedFormat.CSV) -> str:
        """
        Generate Pinterest Product Catalog feed

        Args:
            listings: List of listing dictionaries
            format: Output format (CSV or XML)

        Returns:
            Feed content as string
        """
        if format == FeedFormat.CSV:
            return FeedGenerator._generate_pinterest_csv(listings)
        elif format == FeedFormat.XML:
            return FeedGenerator._generate_pinterest_xml(listings)
        else:
            raise ValueError(f"Unsupported format for Pinterest: {format}")

    @staticmethod
    def _format_pinterest_item(listing: Dict[str, Any]) -> Dict[str, str]:
        """Format a single listing for Pinterest catalog"""
        photos = listing.get('photos', [])
        photo_url = photos[0] if photos else ''

        return {
            'id': str(listing.get('id', '')),
            'title': listing.get('title', '')[:100],
            'description': listing.get('description', '')[:500],
            'link': listing.get('link', ''),
            'image_link': photo_url,
            'additional_image_link': ','.join(photos[1:5]) if len(photos) > 1 else '',
            'availability': 'in stock' if listing.get('status') == 'active' else 'out of stock',
            'price': f"{listing.get('price', 0):.2f} USD",
            'brand': listing.get('brand', ''),
            'condition': listing.get('condition', 'used'),
            'product_type': listing.get('category', ''),
        }

    @staticmethod
    def _generate_pinterest_csv(listings: List[Dict[str, Any]]) -> str:
        """Generate Pinterest feed in CSV format"""
        output = StringIO()
        fieldnames = ['id', 'title', 'description', 'link', 'image_link', 'additional_image_link',
                     'availability', 'price', 'brand', 'condition', 'product_type']

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for listing in listings:
            writer.writerow(FeedGenerator._format_pinterest_item(listing))

        return output.getvalue()

    @staticmethod
    def _generate_pinterest_xml(listings: List[Dict[str, Any]]) -> str:
        """Generate Pinterest feed in XML format"""
        root = ET.Element('rss', version='2.0')

        channel = ET.SubElement(root, 'channel')
        ET.SubElement(channel, 'title').text = 'Product Catalog'
        ET.SubElement(channel, 'link').text = 'https://example.com'
        ET.SubElement(channel, 'description').text = 'Pinterest product feed'

        for listing in listings:
            item = ET.SubElement(channel, 'item')
            formatted = FeedGenerator._format_pinterest_item(listing)

            for key, value in formatted.items():
                if value:
                    ET.SubElement(item, key).text = str(value)

        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')
