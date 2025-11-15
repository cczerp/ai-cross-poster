# AI Cross-Poster 🚀

**Analyzes images to create optimized listings on multiple resale platforms.**

AI Cross-Poster is a powerful Python library that streamlines the process of creating and publishing product listings across eBay and Mercari. It uses dual-AI enhancement (OpenAI GPT-4 Vision + Anthropic Claude) to analyze photos, generate compelling descriptions, and optimize for search.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## ✨ Features

- **📸 AI Photo Analysis**: Cost-efficient strategy - Claude analyzes photos, GPT-4 Vision only used as fallback
- **✍️ Smart AI Enhancement**: Claude handles ~90% of items, GPT-4 Vision only kicks in when needed
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
│  • Claude analyzes photos (primary analyzer)                │
│  • GPT-4 Vision fallback (only if Claude can't identify)    │
│  • 💰 Cost-optimized: Pay for GPT-4 only when needed        │
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
- [PhotoSync Integration](#-photosync-integration)
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

## 📸 PhotoSync Integration

**Seamlessly sync product photos from your phone to your computer!**

AI Cross-Poster integrates perfectly with [PhotoSync](https://www.photosync-app.com/) for an effortless photo workflow:

1. **Take photos** of your products on your phone
2. **Auto-sync** to your computer using PhotoSync
3. **Create listings** with AI analysis - no manual uploading!

### Quick Setup

1. Install PhotoSync app on your phone
2. Configure it to sync to: `ai-cross-poster/images/new_items/`
3. Set up your `.env`:
   ```bash
   PHOTOSYNC_FOLDER=./images/new_items
   ```
4. Take photos and they'll automatically appear in the folder!

### Workflow Example

```bash
# Create images folder
mkdir -p images/new_items images/processed images/archive

# Run the app
python main.py

# Select: 2️⃣ Create Listing from Photos (AI Analysis)
# Enter paths from PhotoSync folder:
#   Photo #1: ./images/new_items/item_front.jpg
#   Photo #2: ./images/new_items/item_back.jpg

# AI analyzes and creates complete listing!
```

📖 **Full PhotoSync Guide:** See [PHOTOSYNC_SETUP.md](PHOTOSYNC_SETUP.md) for:
- Detailed setup instructions
- Batch processing workflows
- Auto-organization scripts
- Tips for best photo results

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

### Getting API Keys - Step by Step

#### 1️⃣ eBay API Credentials (Required for eBay)

**Step 1: Create eBay Developer Account**
1. Go to https://developer.ebay.com/
2. Click "Register" and create a developer account
3. Complete the registration process

**Step 2: Create an Application**
1. Once logged in, go to https://developer.ebay.com/my/keys
2. Click "Create Application Key"
3. Choose "Production" keys (or "Sandbox" for testing)
4. Fill in application details:
   - Application Title: "AI Cross-Poster" (or your choice)
   - Privacy Policy URL: (can use placeholder for personal use)
5. Click "Create"

**Step 3: Get Client ID and Secret**
1. On the Application Keys page, you'll see:
   - **App ID (Client ID)**: Copy this
   - **Cert ID (Client Secret)**: Copy this
2. Add these to your `.env` file

**Step 4: Generate User Refresh Token**
1. Go to https://developer.ebay.com/my/auth/?env=production
2. Select your application
3. Choose the required scopes:
   - `https://api.ebay.com/oauth/api_scope/sell.inventory`
   - `https://api.ebay.com/oauth/api_scope/sell.inventory.readonly`
   - `https://api.ebay.com/oauth/api_scope/sell.fulfillment`
   - `https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly`
   - `https://api.ebay.com/oauth/api_scope/sell.account`
   - `https://api.ebay.com/oauth/api_scope/sell.account.readonly`
4. Click "Get OAuth Credential"
5. Sign in with your eBay seller account
6. Authorize the application
7. Copy the **User Refresh Token** (starts with `v^1.1#...`)

**Add to .env:**
```env
EBAY_CLIENT_ID=YourAppID-Here
EBAY_CLIENT_SECRET=YourCertID-Here
EBAY_REFRESH_TOKEN=v^1.1#your_long_refresh_token
```

---

#### 2️⃣ Mercari Credentials

**Option A: Mercari Shops API** (Recommended if you have a Mercari Shop)

> **Note**: Mercari Shops API is only available to approved shop sellers.

1. Go to Mercari Shops seller portal
2. Navigate to "Developer Settings" or "API Access"
3. Request API access (may require approval)
4. Once approved, generate:
   - **API Key**: Your authentication token
   - **Shop ID**: Your shop identifier

**Add to .env:**
```env
MERCARI_API_KEY=your_api_key_here
MERCARI_SHOP_ID=your_shop_id
```

**Option B: Mercari Automation** (For regular Mercari accounts)

> **Note**: This uses browser automation and requires Playwright.

1. Install Playwright:
   ```bash
   pip install playwright
   playwright install
   ```

2. Use your regular Mercari login credentials:

**Add to .env:**
```env
MERCARI_EMAIL=your_mercari_email@example.com
MERCARI_PASSWORD=your_mercari_password
```

⚠️ **Security Note**: Store credentials securely. Never commit `.env` to version control.

---

#### 3️⃣ OpenAI API Key (Optional - for GPT-4 Vision verification)

**Step 1: Create OpenAI Account**
1. Go to https://platform.openai.com/signup
2. Sign up for an account
3. Verify your email

**Step 2: Add Billing**
1. Go to https://platform.openai.com/account/billing
2. Add a payment method
3. Add credits ($10 minimum recommended)

**Step 3: Create API Key**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Name it: "AI Cross-Poster" (or your choice)
4. Copy the key (starts with `sk-proj-...` or `sk-...`)
   - ⚠️ **Save it immediately** - you can't see it again!

**Add to .env:**
```env
OPENAI_API_KEY=sk-proj-your-key-here
```

**Pricing**: ~$0.01-0.03 per image analysis with GPT-4 Vision

---

#### 4️⃣ Anthropic API Key (Optional - for Claude analysis)

**Step 1: Create Anthropic Account**
1. Go to https://console.anthropic.com/
2. Click "Sign Up" (top right)
3. Create account with email or Google
4. Verify your email

**Step 2: Navigate to API Keys**
1. Once logged in to the console
2. Look for "API Keys" in the left sidebar (or Settings → API Keys)
3. **Alternative**: Direct link: https://console.anthropic.com/settings/keys
4. If you see a workspace selector, make sure you're in the right workspace

**Step 3: Add Credits (Required before creating keys)**
1. Click "Billing" in left sidebar (or go to https://console.anthropic.com/settings/billing)
2. Click "Purchase Credits"
3. Add payment method
4. Purchase credits ($5 minimum, $10 recommended)
5. Wait for credits to appear in your account

**Step 4: Create API Key**
1. Go back to "API Keys" section
2. Click "+ Create Key" button
3. Name it: "AI Cross-Poster" (or your choice)
4. Click "Create Key"
5. **IMPORTANT**: Copy the key immediately (starts with `sk-ant-...`)
   - ⚠️ **You can only see it once!** Save it now or you'll have to create a new one

**Add to .env:**
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Pricing**: ~$0.01-0.02 per image analysis with Claude 3.5 Sonnet

**Troubleshooting:**
- **Can't find API Keys?** Make sure you're logged in to the **Console** (console.anthropic.com), not the chat interface (claude.ai)
- **No API Keys option?** You need to purchase credits first (Step 3 above)
- **Workspace issues?** Click your profile (bottom left) and check which workspace you're in
- **Need help?** Visit https://docs.anthropic.com/claude/reference/getting-started-with-the-api

---

### Complete .env Example

Here's what your complete `.env` file should look like:

```env
# eBay (Required for eBay publishing)
EBAY_CLIENT_ID=YourAppID-ProductionKey
EBAY_CLIENT_SECRET=YourCertID-ProductionKey
EBAY_REFRESH_TOKEN=v^1.1#your_refresh_token

# Mercari Shops (Option 1 - if you have Shops API access)
MERCARI_API_KEY=your_mercari_shops_api_key
MERCARI_SHOP_ID=your_shop_id

# Mercari Automation (Option 2 - for regular accounts)
MERCARI_EMAIL=your_email@example.com
MERCARI_PASSWORD=your_password

# AI Enhancement (Both optional but recommended)
OPENAI_API_KEY=sk-proj-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Optional Settings
USE_SANDBOX=false
AUTO_ENHANCE=true
```

### Minimum Requirements

**To get started, you need at least ONE of:**
- eBay credentials (for eBay publishing)
- Mercari credentials (for Mercari publishing)

**For AI enhancement, you need at least ONE of:**
- Anthropic API key (Claude - primary analyzer, recommended)
- OpenAI API key (GPT-4 Vision - fallback only)

💡 **Tip**: Claude is sufficient for ~90% of items. GPT-4 Vision is only used as fallback when Claude can't identify the item, saving you money!

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

#### How AI Enhancement Works (Cost-Efficient)

The system uses a smart fallback strategy to minimize costs:

**Step 1: Claude Analyzes (Primary)**
- Claude analyzes your photos first
- Generates title, description, keywords, SEO data
- Successfully identifies ~90% of items

**Step 2: GPT-4 Vision Fallback (Only if needed)**
- Only runs if Claude's analysis is incomplete
- Triggers when Claude can't identify brand, category, or generate proper title
- Saves you money by avoiding double analysis

**Example Output:**
```
🤖 Claude analyzing photos...
✅ Claude successfully identified the item
💰 Skipping GPT-4 Vision (Claude analysis was complete)

AI Provider: Claude
```

**Or when fallback is needed:**
```
🤖 Claude analyzing photos...
⚠️  Claude analysis incomplete - will try GPT-4 Vision as fallback
🔄 Using GPT-4 Vision as fallback...
✅ GPT-4 Vision successfully identified the item

AI Provider: GPT-4 Vision (fallback)
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
