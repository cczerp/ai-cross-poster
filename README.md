# AI Cross-Poster 🚀

**Analyzes images to create optimized listings on multiple resale platforms.**

AI Cross-Poster is a powerful Python library that streamlines the process of creating and publishing product listings across eBay and Mercari. It uses dual-AI enhancement (OpenAI GPT-4 Vision + Anthropic Claude) to analyze photos, generate compelling descriptions, and optimize for search.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## ✨ Features

- **📸 AI Photo Analysis**: Two-step AI process - Claude analyzes first, GPT-4 Vision verifies for accuracy
- **✍️ Dual-AI Enhancement**: Claude creates comprehensive listings, GPT-4 Vision ensures label and description accuracy
- **🔄 Cross-Platform Publishing**: Publish to eBay and Mercari from a single unified schema
- **🎯 SEO Optimization**: Auto-generate keywords, search terms, and optimize titles for maximum visibility
- **⚡ Batch Processing**: Create and publish multiple listings efficiently
- **🛡️ Type-Safe**: Built with dataclasses for reliable, predictable behavior
- **🔌 Flexible Adapters**: Easy to extend for additional platforms

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Unified Listing Schema                   │
│  (One structured object for all platforms)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  AI Listing Enhancer                        │
│  • Step 1: Claude analyzes photos (details, SEO, keywords)  │
│  • Step 2: GPT-4 Vision verifies (accuracy check)           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                Platform Adapters                            │
│  • eBay Adapter (Sell API)                                  │
│  • Mercari Adapter (Shops API + Automation)                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               Cross-Platform Publisher                      │
│  • publish_to_all()                                         │
│  • publish_to_ebay()                                        │
│  • publish_to_mercari()                                     │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Table of Contents

- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [API Reference](#-api-reference)
- [Examples](#-examples)
- [Development Roadmap](#-development-roadmap)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- API credentials for your chosen platforms (see [Configuration](#-configuration))

### Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-cross-poster.git
cd ai-cross-poster

# Install dependencies
pip install -r requirements.txt

# Optional: Install with Mercari automation support
pip install -r requirements.txt
pip install playwright
playwright install
```

### Install as Package

```bash
pip install -e .
```

## ⚡ Quick Start

### Main CLI Application (Recommended)

Run the all-in-one menu-driven interface:

```bash
# Configure your credentials first
cp .env.example .env
# Edit .env with your API keys

# Run the main application
python main.py
```

**Main Menu Options:**
1. Create New Listing (Manual)
2. Create Listing from Photos (AI Analysis)
3. Enhance Current Listing with AI
4. Preview Current Listing
5. Publish to eBay
6. Publish to Mercari
7. Publish to All Platforms
8. View Publishing History
9. Load Example Listing

### Python API Usage

```python
from dotenv import load_dotenv
from src.schema import UnifiedListing, Photo, Price, ListingCondition
from src.publisher import publish_to_all

# Load environment variables
load_dotenv()

# Create a listing
listing = UnifiedListing(
    title="Nike Air Jordan 1 High Top Sneakers Size 10",
    description="Classic Air Jordan 1s in great condition",
    price=Price(amount=150.00),
    condition=ListingCondition.EXCELLENT,
    photos=[
        Photo(
            url="https://example.com/photo1.jpg",
            local_path="./photo1.jpg",
            is_primary=True,
        )
    ],
)

# Publish to all platforms (with AI enhancement)
results = publish_to_all(listing)

# Check results
for platform, result in results.items():
    if result.success:
        print(f"✅ {platform}: {result.listing_id}")
    else:
        print(f"❌ {platform}: {result.error}")
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

### Required Credentials

#### eBay API (Required for eBay)

1. Create an eBay developer account: https://developer.ebay.com/
2. Create an application to get your Client ID and Secret
3. Generate a refresh token using OAuth

```env
EBAY_CLIENT_ID=your_client_id
EBAY_CLIENT_SECRET=your_client_secret
EBAY_REFRESH_TOKEN=your_refresh_token
```

#### Mercari (Choose one method)

**Option 1: Mercari Shops API** (Recommended)
```env
MERCARI_API_KEY=your_api_key
MERCARI_SHOP_ID=your_shop_id
```

**Option 2: Mercari Automation** (Fallback)
```env
MERCARI_EMAIL=your_email@example.com
MERCARI_PASSWORD=your_password
```

#### AI Enhancement (Optional but Recommended)

```env
# OpenAI (for photo analysis)
OPENAI_API_KEY=sk-your-openai-key

# Anthropic (for enhanced copywriting)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
```

## 📖 Usage Guide

### 1. Creating a Listing

#### Basic Listing

```python
from src.schema import UnifiedListing, Photo, Price, ListingCondition, Shipping

listing = UnifiedListing(
    title="Your Product Title",
    description="Detailed product description",
    price=Price(amount=99.99),
    condition=ListingCondition.EXCELLENT,
    photos=[
        Photo(url="https://example.com/photo.jpg", is_primary=True)
    ],
    shipping=Shipping(cost=5.00),
)
```

#### Detailed Listing with Item Specifics

```python
from src.schema import ItemSpecifics, Category, SEOData

listing = UnifiedListing(
    title="Nike Air Max 90 Size 11",
    description="Classic Air Max...",
    price=Price(amount=85.00, compare_at_price=120.00),
    condition=ListingCondition.EXCELLENT,
    photos=[...],
    item_specifics=ItemSpecifics(
        brand="Nike",
        size="11",
        color="White/Black",
        model="Air Max 90",
    ),
    category=Category(
        primary="Clothing, Shoes & Accessories",
        subcategory="Men's Shoes",
    ),
    seo_data=SEOData(
        keywords=["nike", "air max", "sneakers"],
        hashtags=["sneakers", "nike"],
    ),
)
```

### 2. AI Enhancement

#### Automatic Enhancement (Recommended)

```python
from src.publisher import CrossPlatformPublisher

# Auto-enhance is enabled by default
publisher = CrossPlatformPublisher.from_env(auto_enhance=True)
results = publisher.publish_to_all(listing)
```

#### Manual Enhancement

```python
from src.enhancer import AIEnhancer

enhancer = AIEnhancer.from_env()
enhanced_listing = enhancer.enhance_listing(
    listing,
    target_platform="ebay",  # or "mercari" or "general"
    force=True,
)
```

### 3. Publishing

#### Publish to All Platforms

```python
from src.publisher import publish_to_all

results = publish_to_all(listing)
```

#### Publish to Specific Platform

```python
from src.publisher import publish_to_ebay, publish_to_mercari

# eBay only
ebay_result = publish_to_ebay(listing)

# Mercari only
mercari_result = publish_to_mercari(listing)
```

#### Advanced Publishing with Control

```python
from src.publisher import CrossPlatformPublisher

publisher = CrossPlatformPublisher.from_env()

# Publish to specific platforms
results = publisher.publish_to_all(
    listing,
    platforms=["ebay"],  # Only eBay
    enhance=True,
)

# Check success rate
print(f"Success Rate: {publisher.get_success_rate()}%")

# View history
for entry in publisher.get_publish_history():
    print(f"{entry['platform']}: {entry['listing_title']}")
```

## 🔍 API Reference

### Core Classes

#### `UnifiedListing`
The master schema for all listings.

**Required Fields:**
- `title` (str): Item title
- `description` (str): Full description
- `price` (Price): Price object
- `condition` (ListingCondition): Item condition
- `photos` (List[Photo]): Product photos

**Optional Fields:**
- `item_specifics` (ItemSpecifics): Brand, size, color, etc.
- `category` (Category): Categorization
- `seo_data` (SEOData): Keywords and search optimization
- `shipping` (Shipping): Shipping configuration
- `quantity` (int): Available quantity
- `sku` (str): Stock keeping unit

#### `ListingCondition` (Enum)
- `NEW`: Brand new
- `NEW_WITH_TAGS`: New with tags
- `NEW_WITHOUT_TAGS`: New without tags
- `LIKE_NEW`: Like new
- `EXCELLENT`: Excellent condition
- `GOOD`: Good condition
- `FAIR`: Fair condition
- `POOR`: Poor condition
- `FOR_PARTS`: For parts/not working

#### `CrossPlatformPublisher`

**Methods:**
- `publish_to_all(listing, enhance=None, platforms=None)`: Publish to all platforms
- `publish_to_ebay(listing, enhance=None)`: Publish to eBay
- `publish_to_mercari(listing, enhance=None)`: Publish to Mercari
- `get_publish_history()`: Get publishing history
- `get_success_rate(platform=None)`: Calculate success rate

#### `AIEnhancer`

**Methods:**
- `enhance_listing(listing, target_platform="general", force=False)`: Enhance listing with AI
- `analyze_photos_openai(photos)`: Analyze photos with GPT-4 Vision
- `enhance_with_claude(data, target_platform)`: Enhance with Claude

### Platform Adapters

#### `EbayAdapter`
- `publish_listing(listing)`: Complete eBay publishing workflow
- `create_inventory_item(listing, sku)`: Create inventory item
- `create_offer(listing, sku)`: Create offer
- `publish_offer(offer_id)`: Publish to eBay

#### `MercariAdapter`
- `publish_listing(listing)`: Publish to Mercari
- Automatically chooses between Shops API and automation

## 📚 Examples

See the [`examples/`](examples/) directory for complete examples:

- **`quick_start.py`**: Simplest way to get started
- **`advanced_usage.py`**: Detailed configuration and individual platform publishing
- **`ai_photo_analysis.py`**: AI-powered photo analysis and listing generation
- **`batch_listing.py`**: Bulk listing creation and publishing

## 🗺️ Development Roadmap

The project was built following this recommended order:

### ✅ Completed
1. ✅ Set up platform API access (eBay, Mercari)
2. ✅ Collect platform requirements (fields, limits, formats)
3. ✅ Create unified listing schema
4. ✅ Build platform adapters
5. ✅ Add dual-AI listing enhancer
6. ✅ Build cross-platform publisher

### 🔮 Future Enhancements (Optional)

7. **Sync Capabilities**
   - Edit propagation from one platform to another
   - Inventory sync across platforms
   - Price synchronization

8. **Auto-Detection Features**
   - Auto-category detection from photos
   - Auto-price comparison and suggestions
   - Smart pricing based on market data

9. **Analytics & Insights**
   - Listing performance tracking
   - Sales analytics dashboard
   - A/B testing for titles and descriptions

10. **Additional Capabilities**
    - Bulk import from CSV/Excel
    - Automatic re-listing
    - Template management
    - Multi-user support

## 🐛 Troubleshooting

### Common Issues

#### "Missing credentials" error
- Ensure all required environment variables are set in `.env`
- Check that API keys are valid and not expired
- Verify you have the correct scopes/permissions

#### eBay authentication fails
- Regenerate your refresh token
- Ensure your app has the correct OAuth scopes
- Check if you're using sandbox vs production credentials correctly

#### Mercari automation fails
- Install Playwright: `pip install playwright && playwright install`
- Check that email/password are correct
- Verify Mercari account is in good standing

#### AI enhancement not working
- Verify API keys are set for OpenAI and/or Anthropic
- Check API quota/billing status
- Ensure photos are accessible (local paths exist or URLs are valid)

#### Photo upload issues
- Ensure photos are in supported formats (JPG, PNG, GIF)
- Check file size limits (eBay: 12 photos max, Mercari: 10 photos max)
- Verify URLs are publicly accessible

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/ai-cross-poster.git
cd ai-cross-poster

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-cov python-dotenv

# Run tests
pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- eBay Developers Program for the Sell API
- Mercari for the resale platform
- OpenAI for GPT-4 Vision API
- Anthropic for Claude API

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/ai-cross-poster/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ai-cross-poster/discussions)

---

**Built with ❤️ for resellers everywhere**
