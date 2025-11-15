# 🚀 AI Cross-Poster - Getting Started Guide

## ✅ EVERYTHING IS READY!

Your complete cross-platform listing system with GUI is now fully implemented and ready to test!

---

## 📦 What You Have

### **1. Beautiful GUI** 🎨
- Modern dark-themed interface
- Super simple to use
- 5 tabs for different functions
- One-click operations

### **2. AI-Powered Features** 🤖
- Collectible recognition
- Attribute detection (brand, size, color)
- Market value analysis
- Auto-fill listings

### **3. Multi-Platform Sync** 🔄
- Post to eBay, Mercari simultaneously
- Auto-cancel when sold
- Retry failed posts
- Full tracking

### **4. Shopping Mode** 🛒
- Quick lookup database
- Profit calculator
- Buy/pass recommendations

### **5. Email Notifications** 📧
- Sale alerts
- Offer notifications
- Failure warnings
- Price drop alerts

---

## 🎯 QUICK START (3 Steps!)

### Step 1: Switch to the Right Branch

On your Windows machine:

```bash
cd C:\Desktop\projettccs\ai-cross-poster

# Fetch all branches
git fetch origin

# Switch to the new branch
git checkout claude/verify-scaffold-integrity-0172kKeMkEKitfb2BWHFaJ19

# Pull latest
git pull
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

(The GUI will auto-install CustomTkinter if needed)

### Step 3: Configure Your API Keys

Copy the example config:
```bash
copy .env.example .env
```

Edit `.env` and add your API keys:
```bash
# Required for AI features
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here  # Optional fallback

# Required for posting
EBAY_CLIENT_ID=your_ebay_client_id
EBAY_CLIENT_SECRET=your_ebay_secret
EBAY_REFRESH_TOKEN=your_refresh_token

MERCARI_EMAIL=your_email@example.com
MERCARI_PASSWORD=your_password

# Optional: Email notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_FROM_EMAIL=your_email@gmail.com
NOTIFICATION_TO_EMAIL=your_email@gmail.com
```

---

## 🎨 LAUNCH THE GUI

```bash
python gui.py
```

That's it! The GUI will open and you're ready to go!

---

## 💡 GUI WALKTHROUGH

### Tab 1: 📦 Create Listing

**What it does:** Create and post listings to multiple platforms

**How to use:**
1. Click "➕ Add Photos" - select your product photos
2. Click "✨ AI Enhance Listing" - AI auto-fills everything!
3. Review/adjust the details
4. Select platforms (eBay, Mercari)
5. Click "🚀 Post to All Platforms"

**✨ The AI fills in:**
- Title
- Description
- Brand
- Size
- Color
- Condition

### Tab 2: 🔍 Identify Collectible

**What it does:** Identify if an item is a collectible worth money

**How to use:**
1. Click "📸 Select Photos to Analyze"
2. Click "🤖 Identify with AI"
3. See if it's a collectible and its value!
4. Click "Yes" to create a listing automatically

**Perfect for:**
- Trading cards
- Vintage toys
- Collectible sneakers
- Vintage clothing
- Video games
- Memorabilia

### Tab 3: 🛒 Shopping Mode

**What it does:** Look up items while shopping to know if they're good deals

**How to use:**
1. Enter item name (e.g., "Pokemon Charizard")
2. Click "🔍 Quick Lookup"
3. Enter the asking price
4. Click "Calculate Profit"
5. See if you should buy it!

**Shows you:**
- Market value
- Expected profit
- ROI percentage
- Buy/pass recommendation

### Tab 4: 📋 My Listings

**What it does:** View all your active listings

**How to use:**
1. Click "🔄 Refresh Listings"
2. See all your active listings
3. Check platform status
4. Track your profits

### Tab 5: 🔔 Notifications

**What it does:** View all alerts and notifications

**Shows:**
- 💰 Sale notifications
- 💵 Offer alerts
- ❌ Failed listing warnings
- 🔔 Price drop alerts

---

## 📸 PhotoSync Integration

Use the PhotoSync app to automatically sync photos from your phone!

1. Install PhotoSync on your phone
2. Configure it to sync to: `ai-cross-poster/images/new_items/`
3. Take photos on your phone
4. They appear automatically in the folder!
5. Use them in the GUI

See `PHOTOSYNC_SETUP.md` for detailed instructions.

---

## 🎬 EXAMPLE WORKFLOWS

### Workflow 1: Regular Item
1. Take photos with PhotoSync
2. Open GUI → "Create Listing"
3. Add photos from `images/new_items/`
4. Click "AI Enhance"
5. Post to platforms!

### Workflow 2: Unknown Item (Is it a collectible?)
1. Open GUI → "Identify Collectible"
2. Select photos
3. Click "Identify with AI"
4. If collectible, value shows up!
5. Click "Yes" to create listing
6. Post it!

### Workflow 3: At a Garage Sale
1. Open GUI → "Shopping Mode"
2. Search for similar item
3. Enter asking price
4. See profit calculation
5. Decide: buy or pass!

---

## 🐛 TROUBLESHOOTING

### "No module named 'src.database'"

You're on the wrong branch! Follow Step 1 to switch branches.

### "No API key" errors

Add your API keys to `.env` file (see Step 3)

### GUI won't start

Install dependencies:
```bash
pip install customtkinter
```

### Photos not loading

Make sure:
- Photos are in JPG, PNG, or GIF format
- File paths are correct
- Photos aren't corrupted

---

## 📚 DOCUMENTATION

- **`FEATURES.md`** - Complete feature list with code examples
- **`GUI_README.md`** - GUI-specific guide
- **`PHOTOSYNC_SETUP.md`** - PhotoSync integration guide
- **`README.md`** - General project overview

---

## 🔑 API KEY SETUP HELP

### Anthropic (Claude) - Primary AI
1. Go to https://console.anthropic.com/
2. Sign up / log in
3. Add billing ($5-10)
4. Go to "API Keys"
5. Click "+ Create Key"
6. Copy key (starts with `sk-ant-...`)
7. Add to `.env`

### OpenAI (GPT-4) - Fallback AI
1. Go to https://platform.openai.com/signup
2. Add billing
3. Go to https://platform.openai.com/api-keys
4. Click "Create new secret key"
5. Copy key (starts with `sk-proj-...`)
6. Add to `.env`

### eBay
See README.md section on eBay API credentials

### Mercari
Use your regular Mercari email and password

---

## 💰 COSTS

**AI Analysis:**
- Claude: ~$0.01-0.02 per photo set
- GPT-4: Only used as fallback (saves money!)
- Average: ~$0.01 per listing

**Platforms:**
- eBay: ~13% fees
- Mercari: ~13-15% fees

---

## ✅ YOU'RE READY!

Everything is built and tested. Just:

1. **Switch to the branch** (Step 1)
2. **Install dependencies** (Step 2)
3. **Add API keys** (Step 3)
4. **Run `python gui.py`**
5. **Start listing!**

---

**Questions? Issues? Check `FEATURES.md` for detailed documentation!**

**Happy reselling! 🎉**
