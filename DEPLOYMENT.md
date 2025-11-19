# ResellGenie - Production Deployment Guide

**IMPORTANT:** Render's free tier uses ephemeral storage. This guide shows how to set up **persistent storage** for photos and data.

---

## 🚨 The Problem

On Render's free tier:
- ❌ All files get deleted on every deployment
- ❌ Database resets when service restarts
- ❌ Photos disappear
- ❌ User data is lost

## ✅ The Solution

Use **managed services** for persistence:
1. **PostgreSQL** for database (FREE on Render)
2. **Cloudinary** for photos (FREE tier: 25GB, 25k transformations/month)

---

## Step 1: Set Up PostgreSQL Database

### In Render Dashboard:

1. Click **"New +"** → **"PostgreSQL"**
2. **Name:** `resellgenie-db`
3. **Database:** `resellgenie` (or any name)
4. **User:** (auto-generated)
5. **Region:** Same as your web service
6. **Plan:** **Free** (good for development)
7. Click **"Create Database"**

### Copy Database URL:

1. After creation, go to database **Info** tab
2. Copy the **Internal Database URL** (looks like `postgresql://user:pass@host/db`)
3. Go to your **Web Service** → **Environment**
4. Add new environment variable:
   ```
   DATABASE_URL=postgresql://user:pass@host/db
   ```
5. **Save** and redeploy

---

## Step 2: Set Up Cloudinary for Photos

### Sign Up for Free:

1. Go to: https://cloudinary.com/users/register_free
2. Sign up (free tier is generous!)
3. **FREE tier includes:**
   - 25 GB storage
   - 25 GB bandwidth/month
   - 25,000 transformations/month
   - More than enough for most resellers!

### Get Your Credentials:

1. After signup, go to **Dashboard**
2. You'll see:
   - **Cloud Name:** (like `dxyz123abc`)
   - **API Key:** (like `123456789012345`)
   - **API Secret:** (like `abcdefghijklmnopqrstuvwxyz`)

### Add to Render:

Go to your Web Service → **Environment** → Add these variables:

```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
USE_LOCAL_STORAGE=false
```

**Important:** Set `USE_LOCAL_STORAGE=false` to enable Cloudinary!

---

## Step 3: Update Environment Variables

### Complete Environment Variables List:

In Render → Your Web Service → **Environment**, you should have:

```bash
# Database (PostgreSQL)
DATABASE_URL=postgresql://user:pass@host/db

# Cloud Storage (Cloudinary)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
USE_LOCAL_STORAGE=false

# AI APIs
GEMINI_API_KEY=your_gemini_key

# Flask
FLASK_SECRET_KEY=auto_generated_by_render

# Email Notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=lyak.resell.genie@gmail.com
SMTP_PASSWORD=your_gmail_app_password
NOTIFICATION_FROM_EMAIL=lyak.resell.genie@gmail.com
```

---

## Step 4: Deploy!

1. Click **"Manual Deploy"** → **"Clear build cache & deploy"**
2. Watch the logs for:
   ```
   ✅ PostgreSQL connected
   ✅ Cloudinary configured for photo storage
   ```

---

## 🎉 You're Done!

Now your data is **persistent**:
- ✅ Photos stored in Cloudinary (won't disappear)
- ✅ Database in PostgreSQL (survives restarts)
- ✅ No more data loss!

---

## Local Development

For local development, create `.env` file:

```bash
# Use local storage for dev
USE_LOCAL_STORAGE=true

# Use SQLite for dev (no DATABASE_URL needed)

# AI APIs
GEMINI_API_KEY=your_gemini_key

# Flask
FLASK_SECRET_KEY=your-dev-secret-key

# Email (optional for dev)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=lyak.resell.genie@gmail.com
SMTP_PASSWORD=your_gmail_app_password
NOTIFICATION_FROM_EMAIL=lyak.resell.genie@gmail.com
```

Run locally:
```bash
python web_app.py
```

---

## Monitoring Storage Usage

### Cloudinary:
- Go to: https://cloudinary.com/console
- Check **Media Library** to see uploaded photos
- Monitor usage in **Dashboard**

### PostgreSQL:
- In Render Dashboard → Your Database
- Check **Metrics** tab for storage usage
- Free tier: 1GB storage (plenty for metadata)

---

## Cost Breakdown

| Service | Free Tier | Cost After Free |
|---------|-----------|-----------------|
| Render Web Service | Free | $7/mo for always-on |
| PostgreSQL | 1GB free | $7/mo for 10GB |
| Cloudinary | 25GB + 25k transforms | $99/mo for 100GB |

**Total for starting out:** $0/month (all free tiers!) 🎉

---

## Troubleshooting

### Photos not uploading:
- Check `USE_LOCAL_STORAGE=false` is set
- Verify Cloudinary credentials are correct
- Check Render logs for error messages

### Database connection errors:
- Verify `DATABASE_URL` is set correctly
- Ensure database and web service are in same region
- Check database is running (Render dashboard)

### Data disappeared after deployment:
- Make sure you followed ALL steps above
- Check environment variables are saved
- Verify Cloudinary is configured (`USE_LOCAL_STORAGE=false`)
