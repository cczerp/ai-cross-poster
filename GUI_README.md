# AI Cross-Poster GUI

## 🎨 Beautiful, Simple Interface

Launch the GUI with:

```bash
python gui.py
```

Or on Windows:
```bash
python3 gui.py
```

## 📱 Features

The GUI has 5 main tabs:

### 1. 📦 Create Listing
- **Drag & drop or select photos**
- **AI Enhance button** - Auto-fills brand, size, color, description
- **One-click multi-platform posting**
- Platform checkboxes (eBay, Mercari)
- Track profit (enter your cost)

### 2. 🔍 Identify Collectible
- **Upload photos** to analyze
- **AI identifies collectibles** automatically
- **Shows market value** and pricing data
- **Saves to database** for future reference
- **One-click create listing** from collectible data

### 3. 🛒 Shopping Mode
- **Quick lookup** while shopping
- **Profit calculator** - know if it's a good buy
- Search database by name/brand
- See market values instantly

### 4. 📋 My Listings
- **View all active listings**
- **See platform status** (posted, active, failed)
- **Track profit** per listing
- Refresh with one click

### 5. 🔔 Notifications
- **View sale alerts**
- **See offer notifications**
- **Failed listing alerts**
- Mark all as read

---

## 🚀 Quick Workflow

### Option 1: Regular Item
1. Click "📦 Create Listing"
2. Add photos
3. Click "✨ AI Enhance" to auto-fill details
4. Adjust price/details
5. Click "🚀 Post to All Platforms"

### Option 2: Collectible Item
1. Click "🔍 Identify Collectible"
2. Select photos
3. Click "🤖 Identify with AI"
4. If collectible, click "Yes" to create listing
5. Auto-fills with market value!
6. Click "🚀 Post to All Platforms"

### Option 3: Shopping Mode
1. Click "🛒 Shopping Mode"
2. Enter item name (e.g., "Pokemon Charizard")
3. Click "🔍 Quick Lookup"
4. Enter asking price
5. Click "Calculate Profit"
6. See if it's a good buy!

---

## 💡 Tips

- **AI Enhance saves time** - automatically detects brand, size, color
- **Collectible recognition** builds your database over time
- **Shopping mode** helps you make smart buying decisions
- **All features work offline** except AI analysis (needs API keys)

---

## 📧 Email Notifications

Configure in `.env`:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_FROM_EMAIL=your_email@gmail.com
NOTIFICATION_TO_EMAIL=your_email@gmail.com
```

Get email alerts when:
- Items sell 💰
- You receive offers 💵
- Listings fail to post ❌
- Collectibles hit target price 🔔

---

## 🎯 Dependencies

The GUI auto-installs `customtkinter` on first run if missing.

Manual install:
```bash
pip install customtkinter
```

---

## 🖥️ Screenshots

### Create Listing Tab
- Left side: Photo upload with drag & drop
- Right side: Form with AI auto-fill

### Identify Collectible Tab
- Simple photo upload
- One-click AI analysis
- Beautiful results display

### Shopping Mode Tab
- Quick search bar
- Profit calculator
- Buy/pass recommendations

---

## ⚡ Performance

- **Fast**: Threaded operations keep UI responsive
- **Smart**: AI only runs when you click buttons
- **Efficient**: Database lookups are instant

---

**Built for resellers, by AI 🤖❤️**
