# Credentials Management System

## Overview

AI Lister uses a **secure, multi-user credential management system** where marketplace logins are stored per-user in the database, NOT in `.env` files.

This approach provides:
- ✅ **Security**: User credentials never stored in configuration files
- ✅ **Multi-User Support**: Each user manages their own marketplace accounts
- ✅ **Scalability**: One server supports unlimited users
- ✅ **Simplicity**: Clean `.env` file with only app-wide settings
- ✅ **Privacy**: Users' marketplace credentials are completely separate

---

## How It Works

### 1. App-Wide Settings (in `.env`)

The `.env` file contains ONLY:

```env
# AI API Keys
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key
GEMINI_API_KEY=your-gemini-key

# App Flags
AUTO_ENHANCE=true
USE_SANDBOX=false
AUTO_PROCESS_PHOTOS=false

# Central SMTP (for sending notifications TO users)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=webapp.notification.email@gmail.com
SMTP_PASSWORD=your_gmail_app_password

# Flask Security
FLASK_SECRET_KEY=your-secret-key
```

**What's NOT in `.env`:**
- ❌ eBay credentials
- ❌ Mercari credentials
- ❌ Poshmark credentials
- ❌ Any marketplace logins
- ❌ User-specific settings

### 2. Per-User Settings (in Database)

Each user stores their own:

**In `users` table:**
- `username` - Login username
- `email` - Login email
- `password_hash` - Hashed password
- `notification_email` - Where to receive sale alerts

**In `marketplace_credentials` table:**
- `user_id` - Links to user
- `platform` - Marketplace name (poshmark, depop, etc.)
- `username` - Marketplace login
- `password` - Marketplace password

---

## User Workflow

### Registration
1. User visits your app URL
2. Clicks "Register"
3. Enters:
   - Username
   - Email (for login)
   - Password
4. Account created!

### Adding Marketplace Logins
1. User logs in
2. Goes to Settings page (⚙️ icon in navigation)
3. For each marketplace they want to use:
   - Enters marketplace username/email
   - Enters marketplace password
   - Clicks "Save"
4. Credentials stored securely in database

### Receiving Notifications
1. User enters their notification email in Settings
2. App sends sale alerts to that email
3. Email sent FROM the central SMTP account (from `.env`)
4. Email sent TO the user's notification email

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    notification_email TEXT,  -- Where to send notifications
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### Marketplace Credentials Table
```sql
CREATE TABLE marketplace_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    platform TEXT NOT NULL,  -- 'poshmark', 'depop', etc.
    username TEXT,
    password TEXT,  -- Consider encryption in production
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, platform)
);
```

---

## Settings Page Features

The Settings page (`/settings`) allows users to:

### 1. View Account Info
- Username
- Email
- Member since date

### 2. Manage Notification Email
- Set where to receive sale alerts
- Update anytime
- Defaults to login email

### 3. Connect Marketplaces
Supported platforms:
- **Poshmark** - Fashion marketplace
- **Depop** - Vintage/streetwear marketplace
- **Mercari** - General marketplace
- **Facebook Marketplace** - Local/online marketplace
- **eBay** - Auction/fixed price marketplace
- **VarageSale** - Local marketplace
- **Nextdoor** - Neighborhood marketplace

For each platform:
- ✅ Add credentials
- ✅ Update credentials
- ✅ Remove credentials
- ✅ See connection status

---

## API Endpoints

### Save Notification Email
```http
POST /api/settings/notification-email
Content-Type: application/json

{
  "notification_email": "user@example.com"
}
```

### Save Marketplace Credentials
```http
POST /api/settings/marketplace-credentials
Content-Type: application/json

{
  "platform": "poshmark",
  "username": "user@example.com",
  "password": "user_password"
}
```

### Delete Marketplace Credentials
```http
DELETE /api/settings/marketplace-credentials/{platform}
```

---

## Using Credentials in Code

### Load User's Marketplace Credentials

```python
# In your automation scripts
from src.database import get_db

db = get_db()

# Get Poshmark credentials for current user
creds = db.get_marketplace_credentials(user_id, "poshmark")

if creds:
    username = creds['username']
    password = creds['password']

    # Use credentials for automation
    poshmark_bot.login(username, password)
else:
    print("User hasn't connected Poshmark yet")
```

### Get All User's Marketplaces

```python
# Get all connected marketplaces for user
all_creds = db.get_all_marketplace_credentials(user_id)

for cred in all_creds:
    platform = cred['platform']
    username = cred['username']
    print(f"User connected to {platform} as {username}")
```

### Send Notification to User

```python
import smtplib
import os
from email.mime.text import MIMEText

# Get user's notification preference
user = db.get_user_by_id(user_id)
recipient = user['notification_email'] or user['email']

# Send email using central SMTP (from .env)
smtp_host = os.getenv('SMTP_HOST')
smtp_port = int(os.getenv('SMTP_PORT', 587))
smtp_user = os.getenv('SMTP_USERNAME')
smtp_pass = os.getenv('SMTP_PASSWORD')

msg = MIMEText("Your item sold!")
msg['Subject'] = "Sale Alert!"
msg['From'] = smtp_user
msg['To'] = recipient

# Send it
server = smtplib.SMTP(smtp_host, smtp_port)
server.starttls()
server.login(smtp_user, smtp_pass)
server.send_message(msg)
server.quit()
```

---

## Security Considerations

### Current Implementation
- ✅ Passwords hashed for login (using PBKDF2-SHA256)
- ✅ Session-based authentication
- ✅ CSRF protection (Flask default)
- ✅ User isolation (can't access other users' data)
- ⚠️ Marketplace passwords stored in plaintext in database

### Production Recommendations

**1. Encrypt Marketplace Passwords**
```python
from cryptography.fernet import Fernet

# Generate key (store in .env)
key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt before saving
encrypted_password = cipher.encrypt(password.encode())
db.save_marketplace_credentials(user_id, platform, username, encrypted_password)

# Decrypt when using
decrypted_password = cipher.decrypt(encrypted_password).decode()
```

**2. Use OAuth Where Available**
- eBay supports OAuth 2.0
- Facebook supports OAuth 2.0
- Avoid storing passwords when possible

**3. Enable HTTPS**
- Use SSL/TLS in production
- Platforms like Render/Railway provide this automatically

**4. Add Rate Limiting**
- Prevent brute force attacks
- Use Flask-Limiter

**5. Regular Security Audits**
- Review access logs
- Monitor failed login attempts
- Update dependencies regularly

---

## Migration from Old System

If you have an existing `.env` with marketplace credentials:

### Step 1: Clean Up `.env`
Remove all marketplace credentials from your `.env` file:
```bash
# Remove these lines
EBAY_CLIENT_ID=...
MERCARI_EMAIL=...
POSHMARK_USERNAME=...
# etc.
```

### Step 2: Add Credentials via Settings
1. Login to the app
2. Go to Settings (⚙️ icon)
3. For each marketplace, enter your credentials
4. Click "Save"

### Step 3: Update Automation Scripts
Replace:
```python
# OLD WAY (reading from .env)
ebay_id = os.getenv('EBAY_CLIENT_ID')
```

With:
```python
# NEW WAY (reading from database)
creds = db.get_marketplace_credentials(user_id, 'ebay')
ebay_id = creds['username'] if creds else None
```

---

## Troubleshooting

### "No marketplace credentials found"
- User hasn't connected that marketplace yet
- Go to Settings → Connect the marketplace
- Enter credentials and save

### "SMTP Error when sending notifications"
- Check `.env` SMTP settings
- Verify SMTP_USERNAME and SMTP_PASSWORD are correct
- For Gmail, use an App Password (not your regular password)

### "Can't save credentials"
- Check that platform name is valid
- Supported: poshmark, depop, mercari, facebook, ebay, varagesale, nextdoor
- Platform names are case-insensitive

### "Other users can see my credentials"
- No, they can't! Credentials are filtered by `user_id`
- Each user only sees and manages their own marketplace logins

---

## Benefits Summary

### For Users
- ✅ Easy to manage marketplace connections
- ✅ Add/remove platforms anytime
- ✅ Update passwords easily
- ✅ Control notification preferences
- ✅ Complete privacy from other users

### For Developers
- ✅ Clean, maintainable `.env` file
- ✅ No hardcoded credentials
- ✅ Multi-user ready out of the box
- ✅ Scalable architecture
- ✅ Easy to add new platforms

### For Deployment
- ✅ One `.env` file for all users
- ✅ No per-user configuration needed
- ✅ Cloud-ready (Render, Railway, etc.)
- ✅ Easy backups (just database)
- ✅ Simple updates (no credential migration)

---

## Future Enhancements

Possible improvements:
- [ ] Encrypt marketplace passwords
- [ ] OAuth integration for supported platforms
- [ ] Two-factor authentication for app login
- [ ] Password strength requirements
- [ ] Credential health checks (test marketplace login)
- [ ] Audit log for credential changes
- [ ] Export/import credentials (encrypted)
- [ ] API keys instead of passwords where available

---

**Questions?** Check the main README or AUTHENTICATION.md for more information!
