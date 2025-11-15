# Examples

This directory contains example scripts demonstrating how to use the AI Cross-Poster.

## Quick Start

### 1. Setup Environment

First, copy the `.env.example` file to `.env` and fill in your credentials:

```bash
cp ../.env.example ../.env
# Edit .env with your API keys
```

### 2. Install Dependencies

```bash
pip install -r ../requirements.txt
```

### 3. Run Examples

## Available Examples

### `quick_start.py`
**Simplest way to get started**

Creates a basic listing and publishes to all platforms with AI enhancement.

```bash
python quick_start.py
```

**What it demonstrates:**
- Creating a UnifiedListing
- Adding photos
- Publishing to all platforms at once
- Automatic AI enhancement

---

### `advanced_usage.py`
**Advanced features and detailed configuration**

Shows how to create comprehensive listings with full details and publish to individual platforms.

```bash
python advanced_usage.py
```

**What it demonstrates:**
- Detailed item specifics
- Category and SEO data
- Custom shipping configuration
- Publishing to individual platforms
- Manual AI enhancement
- Publishing history tracking

---

### `ai_photo_analysis.py`
**AI-powered photo analysis**

Let AI analyze your photos and automatically create listing content.

```bash
python ai_photo_analysis.py
```

**What it demonstrates:**
- Photo analysis with OpenAI GPT-4 Vision
- AI-generated titles and descriptions
- Automatic keyword extraction
- Category suggestions
- Interactive publishing confirmation

---

### `batch_listing.py`
**Bulk listing creation**

Create and publish multiple listings efficiently.

```bash
python batch_listing.py
```

**What it demonstrates:**
- Creating multiple listings
- Batch publishing
- Rate limiting
- Success tracking
- Error handling
- Summary reporting

---

## Customizing Examples

All examples can be customized:

1. **Photo Paths**: Update `local_path` in Photo objects to point to your images
2. **Pricing**: Adjust Price amounts to match your items
3. **Descriptions**: Modify descriptions to match your products
4. **Platform Selection**: Choose specific platforms in `publish_to_all()`

## Next Steps

After running the examples:

1. Check the [main README](../README.md) for detailed documentation
2. Review the API reference for each module
3. Customize the code for your specific needs
4. Set up your production environment variables

## Need Help?

- Check the main README for troubleshooting
- Review the inline code comments
- Ensure all API credentials are correctly configured in `.env`
