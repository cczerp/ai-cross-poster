# AI Cross-Poster Mobile App

A mobile app for Android and iOS that allows users to take photos, generate AI-powered listings, and post to eBay and Mercari.

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│   Mobile App (React Native + Expo)      │
│   - Camera integration                   │
│   - Photo upload                         │
│   - AI listing generation                │
│   - Multi-platform posting               │
└──────────────┬──────────────────────────┘
               │ HTTPS REST API
               ▼
┌─────────────────────────────────────────┐
│   Backend API (FastAPI + Python)         │
│   - User authentication (JWT)            │
│   - Photo storage                        │
│   - AI integration (Claude/GPT-4)        │
│   - eBay/Mercari APIs                    │
│   - PostgreSQL database                  │
└─────────────────────────────────────────┘
```

## 📱 Features

### Current Features
- ✅ Take photos with phone camera
- ✅ Upload multiple photos
- ✅ AI-powered listing generation (Claude/GPT-4)
- ✅ Storage location tracking (A1, B2, etc.)
- ✅ Post to eBay and Mercari
- ✅ Draft listings
- ✅ View active listings

### Planned Features (Premium)
- 🔄 User authentication with email/password
- 🔄 Cloud sync across devices
- 🔄 Subscription tiers (Free, Pro, Business)
- 🔄 Analytics and sales tracking
- 🔄 Barcode scanning for quick lookups
- 🔄 Bulk listing tools
- 🔄 Auto-reposting
- 🔄 Price recommendations

## 🚀 Getting Started

### Prerequisites

**Backend:**
- Python 3.10+
- pip

**Mobile App:**
- Node.js 16+
- npm or yarn
- Expo CLI: `npm install -g expo-cli`
- Android Studio (for Android) or Xcode (for iOS)

### Backend Setup

1. **Install dependencies:**
```bash
cd mobile_app/backend
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
# Create .env file
cat > .env << EOF
# API Keys
ANTHROPIC_API_KEY=your_claude_api_key
OPENAI_API_KEY=your_openai_api_key

# eBay API
EBAY_APP_ID=your_ebay_app_id
EBAY_CERT_ID=your_ebay_cert_id
EBAY_DEV_ID=your_ebay_dev_id

# Mercari API
MERCARI_API_KEY=your_mercari_api_key

# Database
DATABASE_URL=sqlite:///./data/mobile_app.db

# JWT Secret
JWT_SECRET_KEY=your_super_secret_key_change_this
EOF
```

3. **Run the backend:**
```bash
python main.py
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### Mobile App Setup

1. **Install dependencies:**
```bash
cd mobile_app/android
npm install
```

2. **Update API URL:**
Edit `App.tsx` and change `API_BASE_URL`:
```typescript
// For local development (Android emulator)
const API_BASE_URL = 'http://10.0.2.2:8000';

// For local development (iOS simulator)
const API_BASE_URL = 'http://localhost:8000';

// For physical device on same network
const API_BASE_URL = 'http://192.168.1.XXX:8000';

// For production
const API_BASE_URL = 'https://your-api-domain.com';
```

3. **Run the app:**
```bash
# Start Expo
npm start

# Run on Android
npm run android

# Run on iOS (macOS only)
npm run ios
```

## 📦 Deployment

### Backend Deployment Options

#### Option 1: Railway (Easiest)
1. Create account at https://railway.app
2. Install Railway CLI: `npm i -g @railway/cli`
3. Deploy:
```bash
cd mobile_app/backend
railway login
railway init
railway up
```

#### Option 2: Render
1. Create account at https://render.com
2. Create new Web Service
3. Connect your GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### Option 3: Google Cloud Run
1. Install Google Cloud SDK
2. Build container:
```bash
cd mobile_app/backend
gcloud builds submit --tag gcr.io/YOUR_PROJECT/ai-cross-poster
gcloud run deploy --image gcr.io/YOUR_PROJECT/ai-cross-poster --platform managed
```

#### Option 4: AWS Elastic Beanstalk
1. Install AWS CLI and EB CLI
2. Initialize:
```bash
cd mobile_app/backend
eb init -p python-3.10 ai-cross-poster
eb create ai-cross-poster-env
eb deploy
```

### Mobile App Deployment

#### Build for Android (Google Play)

1. **Configure app.json:**
```json
{
  "expo": {
    "name": "AI Cross-Poster",
    "slug": "ai-cross-poster",
    "version": "1.0.0",
    "android": {
      "package": "com.yourcompany.aicrossposter",
      "versionCode": 1,
      "permissions": ["CAMERA", "WRITE_EXTERNAL_STORAGE", "READ_EXTERNAL_STORAGE"]
    }
  }
}
```

2. **Build APK/AAB:**
```bash
# Install EAS CLI
npm install -g eas-cli

# Login to Expo
eas login

# Configure build
eas build:configure

# Build for Android
eas build --platform android --profile production
```

3. **Submit to Google Play:**
```bash
# Submit to Google Play Console
eas submit --platform android
```

Or manually:
- Download the `.aab` file from EAS
- Go to https://play.google.com/console
- Create new app
- Upload the `.aab` file
- Fill out store listing
- Submit for review

#### Build for iOS (App Store)

```bash
# Build for iOS
eas build --platform ios --profile production

# Submit to App Store
eas submit --platform ios
```

## 💰 Monetization Strategy

### Subscription Tiers

**Free Tier:**
- 10 listings per month
- Basic AI analysis
- Manual posting
- Single device

**Pro Tier ($9.99/month):**
- Unlimited listings
- Advanced AI (GPT-4)
- Auto-posting
- Multiple devices
- Cloud sync
- Analytics

**Business Tier ($29.99/month):**
- Everything in Pro
- Bulk tools
- Priority support
- API access
- White-label option
- Team accounts

### Implementation with Stripe

1. **Backend integration:**
```bash
pip install stripe
```

2. **Add subscription endpoint:**
```python
@app.post("/subscriptions/create")
async def create_subscription(
    price_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Create Stripe checkout session
    session = stripe.checkout.Session.create(
        customer_email=current_user["email"],
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url="https://yourapp.com/success",
        cancel_url="https://yourapp.com/cancel",
    )
    return {"checkout_url": session.url}
```

3. **Mobile app integration:**
```typescript
// Use Stripe React Native SDK or WebView
import { useStripe } from '@stripe/stripe-react-native';
```

## 🔐 Security Considerations

### Before Launch:

1. **Implement proper JWT authentication:**
```python
from passlib.context import CryptContext
from jose import JWTError, jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm="HS256")
```

2. **Rate limiting:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/ai/analyze")
@limiter.limit("10/hour")  # Limit AI calls
async def analyze_photos(...):
    ...
```

3. **Environment variables:**
- Never commit API keys
- Use secrets management (AWS Secrets Manager, etc.)
- Rotate keys regularly

4. **HTTPS only:**
- Use SSL certificates (Let's Encrypt)
- Enforce HTTPS in production

5. **Input validation:**
- Validate all user inputs
- Sanitize file uploads
- Check file types and sizes

## 📊 Google Play Store Listing

### App Title
"AI Cross-Poster - Sell on eBay & Mercari"

### Short Description
"Take photos, let AI create listings, post to eBay and Mercari instantly. Your mobile reselling assistant!"

### Full Description
```
🚀 Sell faster with AI-powered listings!

AI Cross-Poster helps resellers create professional listings in seconds:

📷 CAMERA INTEGRATION
• Take photos directly in the app
• Upload from gallery
• Capture multiple angles

🤖 AI-POWERED LISTINGS
• Auto-generate titles and descriptions
• Detect brand, size, color automatically
• Smart price suggestions
• Identify valuable collectibles

📦 MULTI-PLATFORM POSTING
• Post to eBay instantly
• Cross-post to Mercari
• More platforms coming soon

📍 INVENTORY TRACKING
• Label storage locations (A1, B2, etc.)
• Never lose track of items
• Quick lookup when items sell

💰 PERFECT FOR:
• Clothing resellers
• Thrift flippers
• Collectible sellers
• Small businesses
• Anyone selling online

⭐ FEATURES:
✓ Professional AI-generated listings
✓ Multi-photo support
✓ Storage organization
✓ Draft listings
✓ Sales tracking
✓ Works offline (drafts)

Start selling smarter today!
```

### Screenshots Needed
1. Camera screen taking photo
2. Photo gallery view
3. AI analysis in progress
4. Generated listing
5. Platform selection
6. Success screen

### Keywords
reselling, ebay, mercari, ai, listings, sell, camera, inventory, cross-post, thrift

## 🐛 Troubleshooting

### Common Issues

**Camera not working:**
- Check permissions in app settings
- Restart the app
- Check `Info.plist` (iOS) or `AndroidManifest.xml` (Android)

**API connection failed:**
- Verify backend is running
- Check `API_BASE_URL` is correct
- For physical device, use computer's local IP
- Check firewall settings

**Upload failed:**
- Check file size (limit to 10MB)
- Verify image format (JPEG, PNG)
- Check storage permissions

## 📞 Support

For issues or questions:
- Email: support@yourapp.com
- Discord: https://discord.gg/yourserver
- Docs: https://docs.yourapp.com

## 📄 License

Proprietary - All rights reserved

---

Built with ❤️ for resellers everywhere
