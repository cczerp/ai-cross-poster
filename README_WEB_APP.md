# AI Lister - Mobile Web App

AI-powered listing creator and inventory tracker for resellers.

## What It Does

### 📸 AI-Powered Listing Creation
- Upload photos from your phone
- AI analyzes and generates:
  - Title
  - Description
  - Suggested price
  - Brand, size, color
  - Condition assessment

### 📦 Inventory Tracking
- **Storage Locations**: Track where items are stored (B1, C2, Box-A, etc.)
- **Quantity Management**: Track single items or multiples
- **Mark as Sold**: Update inventory when items sell
- **Find Items Fast**: See storage location when item sells

### 📋 CSV Import/Export
- **Export listings** to CSV
- Edit in Excel/Google Sheets
- **Import back** to update storage locations in bulk
- Perfect for organizing large inventory

### 💾 Draft System
- Save listings before posting
- Edit later
- Organize your inventory

## How It Works

1. **Take Photos** - Use your phone camera
2. **AI Analyzes** - Automatically fills in details
3. **Add Location** - Enter storage location (B1, C2, etc.)
4. **Save Listing** - Stored with photos and details
5. **Export** - Get CSV to manually post anywhere
6. **Track Sales** - Mark as sold, see location instantly

## Key Features

✅ **User Authentication** - Each user has their own account and data
✅ **Data Separation** - Complete privacy, users can't see each other's inventory
✅ No automated posting (compliant with platform rules)
✅ AI analysis with Gemini
✅ Mobile-friendly interface
✅ Photo upload from phone camera
✅ Storage location tracking
✅ CSV bulk operations
✅ Works on any device with browser
✅ **Multi-User Cloud Ready** - Deploy once, support unlimited users
✅ Can be added to phone home screen

## Use Cases

### Individual Resellers
- Sell unique items (vintage, thrift finds, etc.)
- Store in bins/totes labeled B1, B2, C3, etc.
- When item sells → See location → Find in seconds
- No more searching through 10 bins!

### Small Businesses
- Track inventory across storage locations
- Export to CSV for bookkeeping
- Multiple users can access same inventory
- Simple workflow for employees

### Bulk Sellers
- Track quantities of same item
- Reduce quantity when sold
- Organize by storage area

## Privacy & Security

- ❌ No automated posting to eBay/Mercari (against their rules)
- ✅ All data stored locally on your server
- ✅ No data sent to third parties (except AI analysis)
- ✅ You control access via WiFi/ngrok

## Installation

See `SETUP_LINUX_SERVER.md` for step-by-step setup.

**Quick start:**
```bash
pip install flask werkzeug python-dotenv
python web_app.py
```

Access from phone: `http://YOUR_IP:5000`

## CSV Workflow

### Export
1. Go to "Saved Listings"
2. Click "Export to CSV"
3. Opens in Excel/Sheets

### Edit
Edit the "Storage Location" column:
```csv
ID,Title,Storage Location
1,Blue Shirt,B1
2,Red Shoes,B2
3,Vintage Toy,C1
```

### Import
1. Save CSV
2. Click "Import CSV"
3. Storage locations updated!

## Mobile Tips

### Add to Home Screen

**iPhone:**
1. Open in Safari
2. Share → "Add to Home Screen"
3. Acts like native app

**Android:**
1. Open in Chrome
2. Menu → "Add to Home screen"
3. Acts like native app

### Camera Access
Grant camera permission when prompted to use phone camera directly.

## Manual Posting Workflow

This app does NOT post automatically. Instead:

1. **Create listing** with AI
2. **Save to database**
3. **Export to CSV** or view in app
4. **Manually post** to eBay/Mercari/etc.
5. **Mark as sold** when it sells
6. **See storage location** to find item

## Why No Automated Posting?

eBay and Mercari prohibit automation/bots. This app:
- ✅ Helps you CREATE listings faster
- ✅ Tracks WHERE items are stored
- ✅ Exports data for manual posting
- ❌ Does NOT auto-post (stays compliant)

You manually copy/paste the listing details when posting.

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: Bootstrap 5, vanilla JavaScript
- **AI**: Google Gemini
- **Database**: SQLite
- **Mobile**: Responsive design, PWA-ready

## Requirements

- Python 3.8+
- Flask
- Google Gemini API key (for AI analysis)
- WiFi network or ngrok for remote access

## Support

- Check `SETUP_LINUX_SERVER.md` for setup help
- Check `docs/WEB_APP_DEPLOYMENT.md` for advanced deployment
- Issues? Check Flask logs for errors

## License

For personal and commercial use. Attribution appreciated.

---

**Built for resellers who want AI-powered listing creation and smart inventory tracking without breaking platform rules.**
