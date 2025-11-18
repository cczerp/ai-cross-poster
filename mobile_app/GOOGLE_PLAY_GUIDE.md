# 📱 Google Play Publishing Guide

Complete step-by-step guide to publish AI Cross-Poster on Google Play Store.

## 📋 Prerequisites Checklist

Before you start, make sure you have:

- [ ] Google Play Developer Account ($25 one-time fee)
- [ ] Privacy Policy URL (required)
- [ ] App icon (512x512 px)
- [ ] Feature graphic (1024x500 px)
- [ ] Screenshots (at least 2, max 8)
- [ ] Short description (80 chars max)
- [ ] Full description (4000 chars max)
- [ ] Backend deployed and running
- [ ] All API keys configured

## 🚀 Step-by-Step Publishing

### Step 1: Create Google Play Developer Account

1. Go to https://play.google.com/console
2. Click "Create account"
3. Pay $25 registration fee
4. Complete account setup

### Step 2: Prepare App Assets

#### App Icon (512x512 px)
- Must be PNG
- 32-bit with alpha
- Square, no rounded corners
- Google Play will apply its own styling

#### Feature Graphic (1024x500 px)
- PNG or JPEG
- Shows at top of store listing
- Should showcase app features

#### Screenshots (Phone - required, min 2)
- PNG or JPEG
- Min dimension: 320px
- Max dimension: 3840px
- Recommended: 1080x1920 (portrait) or 1920x1080 (landscape)

**Screenshot Ideas:**
1. Camera screen with item
2. AI analyzing photos
3. Generated listing
4. Platform selection
5. Posted listings

#### Screenshots (Tablet - optional)
- 7-inch: 1920x1200
- 10-inch: 2560x1600

### Step 3: Build Production APK/AAB

```bash
cd mobile_app/android

# Install EAS CLI if you haven't
npm install -g eas-cli

# Login to Expo account
eas login

# Configure EAS build
eas build:configure

# Build for production (AAB - Android App Bundle)
eas build --platform android --profile production
```

This will:
1. Upload your code to Expo's servers
2. Build the app in the cloud
3. Provide a download link for the AAB file

**Alternative: Build locally**
```bash
# Generate Android signing key
keytool -genkey -v -keystore ai-cross-poster.keystore -alias ai-cross-poster -keyalg RSA -keysize 2048 -validity 10000

# Build AAB
npx expo build:android -t app-bundle
```

### Step 4: Create App in Google Play Console

1. **Go to Play Console** → "All apps" → "Create app"

2. **App details:**
   - App name: "AI Cross-Poster"
   - Default language: English (United States)
   - App or game: App
   - Free or paid: Free (or Paid if you want upfront cost)

3. **Declarations:**
   - [ ] Check "I declare this app complies with Google Play policies"
   - [ ] Check "I declare this app complies with US export laws"

4. Click "Create app"

### Step 5: Set Up Store Listing

Navigate to "Store presence" → "Main store listing"

#### App details
```
App name: AI Cross-Poster
Short description:
Take photos, let AI create listings, post to eBay & Mercari instantly!

Full description:
🚀 Sell faster with AI-powered listings!

AI Cross-Poster helps resellers create professional listings in seconds using the power of artificial intelligence.

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

Start selling smarter today!

Premium features available with subscription:
• Unlimited listings
• Advanced AI analysis
• Bulk listing tools
• Priority support

Terms: https://yourapp.com/terms
Privacy: https://yourapp.com/privacy
```

#### App category
- Category: Shopping
- Tags: add relevant keywords

#### Contact details
- Email: support@yourapp.com
- Phone: (optional)
- Website: https://yourapp.com

#### Graphics
- Upload all your prepared assets
- App icon
- Feature graphic
- Phone screenshots
- Tablet screenshots (optional)

### Step 6: Set Up Content Rating

Navigate to "Policy" → "App content"

Click "Start questionnaire"

**Answer questions honestly:**
- Violence: None
- Blood: None
- Sexual content: None
- Language: None
- Controlled substances: None
- Gambling: None
- User interaction: Yes (users can share data)

Submit questionnaire to get your rating.

### Step 7: Privacy Policy

**Required for all apps!**

1. Create privacy policy (use generator: https://app-privacy-policy-generator.firebaseapp.com/)

2. Host it on:
   - Your website
   - GitHub Pages
   - Google Sites (free)

3. Add URL in "App content" → "Privacy policy"

**Sample Privacy Policy sections:**
- What data you collect (photos, listing info)
- How you use it (AI analysis, posting to platforms)
- Third-party services (eBay, Mercari, Claude AI)
- Data storage and security
- User rights (delete account, export data)

### Step 8: Data Safety

Navigate to "Policy" → "Data safety"

**Data collected:**
- [ ] Location: No
- [ ] Personal info: Yes (email, name)
- [ ] Financial info: No
- [ ] Photos and videos: Yes (product photos)
- [ ] Files and docs: No
- [ ] Messages: No
- [ ] App activity: Yes (listings created)
- [ ] App info and performance: Yes (crashes, diagnostics)
- [ ] Device or other IDs: No

**Data usage:**
- App functionality
- Analytics
- Advertising (if applicable)

**Data sharing:**
- No data shared with third parties (unless you do)

**Data security:**
- [ ] Data encrypted in transit (HTTPS)
- [ ] Data encrypted at rest
- [ ] Users can request data deletion

### Step 9: Upload APK/AAB

Navigate to "Release" → "Production"

1. Click "Create new release"

2. **App signing:**
   - Recommended: Use Google Play App Signing (they manage the key)
   - Advanced: Upload your own signing key

3. **Upload AAB:**
   - Drag and drop your .aab file
   - Wait for upload and processing

4. **Release name:**
   - Example: "1.0.0 - Initial Release"

5. **Release notes:**
```
What's new in version 1.0:
• Take photos with your phone camera
• AI-powered listing generation
• Post to eBay and Mercari
• Track storage locations
• Save drafts
• View active listings
```

6. Click "Next" → "Save"

### Step 10: Set Up Pricing & Distribution

Navigate to "Release" → "Production" → "Countries/regions"

1. **Select countries:**
   - Start with: United States, Canada, United Kingdom
   - Expand later based on demand

2. **Pricing:**
   - Free to download
   - In-app purchases (for subscriptions)

3. **Distribution settings:**
   - [ ] Google Play for Education: No (unless educational)
   - [ ] US export laws: Declare compliance

### Step 11: Review and Publish

1. Go to "Publishing overview"
2. Make sure all sections have green checkmarks
3. Click "Send for review"

**Review timeline:**
- First review: 7-14 days
- Updates: 1-3 days

### Step 12: Set Up In-App Purchases (For Subscriptions)

Navigate to "Monetize" → "In-app products" → "Subscriptions"

1. **Create subscription products:**

**Pro Subscription ($9.99/month):**
```
Product ID: pro_monthly
Name: Pro Monthly Subscription
Description: Unlimited listings, advanced AI, cloud sync
Price: $9.99/month
Free trial: 7 days
Grace period: 3 days
```

**Business Subscription ($29.99/month):**
```
Product ID: business_monthly
Name: Business Monthly Subscription
Description: Everything in Pro + bulk tools, API access, priority support
Price: $29.99/month
Free trial: 14 days
Grace period: 3 days
```

2. **Integrate in your app:**
```typescript
import * as InAppPurchases from 'expo-in-app-purchases';

// Connect to store
await InAppPurchases.connectAsync();

// Get products
const products = await InAppPurchases.getProductsAsync(['pro_monthly', 'business_monthly']);

// Purchase
await InAppPurchases.purchaseItemAsync('pro_monthly');
```

### Step 13: Marketing & Launch

#### Pre-launch checklist
- [ ] Set up Google Analytics for Firebase
- [ ] Create social media accounts
- [ ] Prepare launch announcement
- [ ] Reach out to influencers in reselling community
- [ ] Create demo videos for YouTube

#### Launch day
- [ ] Post on social media
- [ ] Share in relevant communities (r/Flipping, r/Mercari, etc.)
- [ ] Contact tech/reselling blogs
- [ ] Run Google Ads campaign (optional)

#### Post-launch
- [ ] Monitor reviews and respond
- [ ] Track analytics
- [ ] Fix bugs quickly
- [ ] Release updates regularly

## 🔄 Publishing Updates

When you have a new version:

```bash
# Increment version in app.json
{
  "expo": {
    "version": "1.0.1",
    "android": {
      "versionCode": 2  // Must increment
    }
  }
}

# Build new AAB
eas build --platform android --profile production

# Upload to Play Console
# Go to Production → Create new release
# Upload new AAB with release notes
```

## 📊 Marketing Materials

### App Store Optimization (ASO)

**Title optimization:**
- "AI Cross-Poster - Sell on eBay & Mercari"
- Include main keywords: AI, eBay, Mercari, sell

**Keywords to target:**
- reselling app
- ebay listing tool
- mercari seller
- cross posting
- ai listing generator
- thrift flip
- inventory management
- photo listing

**Competitor research:**
- Search similar apps
- See what keywords they rank for
- Improve your description based on gaps

### Promo Video (30 seconds)

Script:
```
[0-5s] "Tired of spending hours creating listings?"
[5-10s] Show person taking photo with app
[10-15s] "AI Cross-Poster generates professional listings instantly"
[15-20s] Show AI analyzing, generating title & description
[20-25s] "Post to eBay and Mercari with one tap"
[25-30s] "Download now and start selling smarter!"
```

## 💡 Tips for Success

1. **Respond to reviews quickly** - Users love responsive developers
2. **Fix bugs ASAP** - Bad reviews hurt downloads
3. **Request reviews in-app** - After user posts their 3rd successful listing
4. **Track analytics** - See what features users love
5. **Build community** - Discord, Facebook group, etc.
6. **Content marketing** - Blog posts, YouTube tutorials
7. **Referral program** - Give users free credits for referrals

## 🚨 Common Rejection Reasons

1. **Broken functionality** - Test thoroughly before submitting
2. **Missing privacy policy** - Must be accessible and complete
3. **Misleading content** - Don't overpromise features
4. **Crashes** - Test on multiple devices
5. **Policy violations** - Read policies carefully
6. **Permissions issues** - Only request necessary permissions

## 📞 Support Resources

- Google Play Console Help: https://support.google.com/googleplay/android-developer
- Expo Documentation: https://docs.expo.dev
- EAS Build: https://docs.expo.dev/build/introduction/
- Google Play Policies: https://play.google.com/about/developer-content-policy/

## 💰 Revenue Estimates

**Conservative scenario (first year):**
- 1000 downloads
- 5% conversion to Pro ($9.99/month)
- 50 paying users × $9.99 × 12 months = $5,994/year

**Optimistic scenario (first year):**
- 10,000 downloads
- 10% conversion to Pro/Business
- 1000 paying users × average $12/month × 12 = $144,000/year

**Keys to growth:**
- Great user experience
- Responsive support
- Regular updates
- Community building
- Content marketing

---

## 🎉 You're Ready!

Follow this guide step-by-step, and you'll have your app live on Google Play!

Good luck! 🚀
