# Mercari Automation Debugging Guide

## ⭐ BEST SOLUTION: Use Cookie-Based Login (Bypasses Bot Detection!)

Instead of logging in every time (which Mercari detects as automation), save your login session once:

### Step 1: Save Your Cookies
```bash
python save_mercari_cookies.py
```

This will:
1. Open a browser window
2. Let YOU log in manually to Mercari (like a real person)
3. Save your session cookies to `data/mercari_cookies.json`

### Step 2: Done!
From now on, the automation will use your saved cookies instead of logging in. This bypasses bot detection completely! 🎉

**When to refresh cookies:**
- If you get logged out
- If posting starts failing
- Every few weeks (cookies expire)

Just run `python save_mercari_cookies.py` again to refresh.

---

## Running Browser in Visible Mode

To see the browser while it's running (for debugging login issues), add this to your `.env` file:

```
MERCARI_HEADLESS=false
```

This will open a visible Chrome window so you can see exactly what's happening during login.

## Common Login Issues

### 1. **2FA/Verification Required**
If Mercari requires 2-step verification or sends a code to your email/phone:
- **Solution**: Disable 2FA on your Mercari account temporarily, or use an account without 2FA

### 2. **CAPTCHA/Bot Detection**
If you see a CAPTCHA or "Verify you're human" page:
- **Solution**: Mercari has detected automation. Try:
  - Running in non-headless mode (`MERCARI_HEADLESS=false`)
  - Using a different IP address (VPN)
  - Logging in manually first in a regular browser, then try automation

### 3. **Invalid Credentials**
If login keeps failing:
- Double-check `MERCARI_EMAIL` and `MERCARI_PASSWORD` in `.env`
- Try logging in manually at https://www.mercari.com/login/ to verify credentials
- Make sure there are no extra spaces in your `.env` file

### 4. **Screenshot Debugging**
When login fails, a screenshot is automatically saved as `mercari_login_error_<timestamp>.png` in your project directory. Check this to see what page appeared.

## Environment Variables

Required:
```
MERCARI_EMAIL=your_email@example.com
MERCARI_PASSWORD=your_password
```

Optional (for debugging):
```
MERCARI_HEADLESS=false   # Set to false to see browser window
```

## Testing Your Credentials

1. Add `MERCARI_HEADLESS=false` to `.env`
2. Run `python gui.py`
3. Try posting a listing to Mercari
4. Watch the browser window to see where it's failing
5. Check the terminal output for detailed error messages

## Recent Improvements (v2)

✅ Increased timeouts from 10s to 60s for slow connections
✅ Added multiple selector fallbacks for email/password/submit fields
✅ Enhanced anti-detection measures (better browser fingerprinting)
✅ Added screenshot capture on login failure
✅ Detailed error messages with troubleshooting steps
✅ Support for visible browser mode (`MERCARI_HEADLESS=false`)

## Still Having Issues?

If you're still experiencing login problems:
1. Check the screenshot saved when login fails
2. Try logging in manually to see if Mercari requires additional verification
3. Consider using a dedicated Mercari account without 2FA for automation
4. Check if your IP is being rate-limited (try from a different network)
