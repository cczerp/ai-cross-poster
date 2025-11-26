# Google OAuth Setup Guide

## Issue: Getting 404 Error When Signing in with Google

If you're seeing a 404 error when clicking "Sign in with Google", it means the OAuth redirect URL isn't properly configured in Supabase.

---

## ⚠️ Root Cause

The app redirects to Supabase for Google authentication, but Supabase doesn't know where to redirect back to after authentication succeeds. This causes a 404 error.

---

## ✅ Solution: Configure Supabase Redirect URLs

### Step 1: Get Your Render App URL

1. Go to your Render dashboard
2. Find your web service
3. Copy the URL (e.g., `https://your-app.onrender.com`)

### Step 2: Configure Supabase

1. **Go to Supabase Dashboard:**
   - Visit https://app.supabase.com
   - Select your project

2. **Navigate to Authentication Settings:**
   - Click "Authentication" in the left sidebar
   - Click "URL Configuration"

3. **Add Redirect URL:**
   - Find "Redirect URLs" section
   - Click "Add URL"
   - Add: `https://your-app.onrender.com/auth/callback`
   - Example: `https://resell-rebel.onrender.com/auth/callback`
   - Click "Save"

4. **Add Site URL (optional but recommended):**
   - Set "Site URL" to: `https://your-app.onrender.com`

### Step 3: Set Environment Variables in Render

Make sure these are set in Render:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_REDIRECT_URL=https://your-app.onrender.com/auth/callback
```

**Note:** `SUPABASE_REDIRECT_URL` is optional if you're using `RENDER_EXTERNAL_URL` (which Render sets automatically).

---

## 🔍 Debugging Google OAuth

After deploying, check Render logs when clicking "Sign in with Google":

You should see:
```
Google OAuth: Using redirect URL: https://your-app.onrender.com/auth/callback
Google OAuth: Redirecting to: https://your-project.supabase.co/auth/v1/authorize?provider=google&redirect_to=...
```

If you see errors:
- `SUPABASE_URL or SUPABASE_ANON_KEY not configured` → Set environment variables
- `Failed to generate Google OAuth URL` → Check Supabase configuration
- 404 error → Redirect URL not whitelisted in Supabase

---

## 📋 Complete Checklist

Before testing Google OAuth:

- [ ] Supabase project created
- [ ] Google OAuth provider enabled in Supabase (Authentication → Providers → Google)
- [ ] Google OAuth credentials configured in Supabase
- [ ] Redirect URL added to Supabase whitelist: `https://your-app.onrender.com/auth/callback`
- [ ] `SUPABASE_URL` set in Render environment variables
- [ ] `SUPABASE_ANON_KEY` set in Render environment variables
- [ ] Deployed to Render
- [ ] Test Google sign-in
- [ ] Check Render logs for OAuth debug messages

---

## 🔧 Testing Locally

For local development (http://localhost:5000):

1. **Add localhost to Supabase redirect URLs:**
   - Add: `http://localhost:5000/auth/callback`

2. **Set environment variables in `.env`:**
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key-here
   SUPABASE_REDIRECT_URL=http://localhost:5000/auth/callback
   ```

3. **Restart your local server**

4. **Test Google sign-in** at http://localhost:5000/login

---

## 🚨 Common Errors & Solutions

### Error: "Google login is not configured"
**Cause:** Missing `SUPABASE_URL` or `SUPABASE_ANON_KEY`
**Fix:** Set environment variables in Render dashboard

### Error: 404 after clicking "Sign in with Google"
**Cause:** Redirect URL not whitelisted in Supabase
**Fix:** Add `https://your-app.onrender.com/auth/callback` to Supabase redirect URLs

### Error: "Invalid authorization code"
**Cause:** OAuth flow timing out or code already used
**Fix:** Try signing in again (OAuth codes are single-use)

### Error: "Failed to exchange code for session"
**Cause:** Supabase client error or invalid API key
**Fix:** Check `SUPABASE_ANON_KEY` is correct

---

## 📖 Additional Resources

- [Supabase OAuth Documentation](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Google OAuth Setup](https://support.google.com/cloud/answer/6158849)

---

## ✅ Verification Steps

After setup:

1. **Click "Sign in with Google"** on login page
2. **Should redirect to Google** (not show error)
3. **Grant permissions** in Google consent screen
4. **Should redirect back to app** (not 404)
5. **Should see success message** and be logged in
6. **Check Render logs** for OAuth debug messages

If any step fails, check the corresponding section above.

---

**Last Updated:** 2025-11-26
