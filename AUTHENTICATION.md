# User Authentication System

The AI Lister web app now includes a complete user authentication system that separates data for each user.

## Features

### ✅ User Registration
- New users can create accounts with username, email, and password
- Passwords must be at least 6 characters
- Passwords are securely hashed using Werkzeug's password hashing
- Email validation ensures valid email addresses

### ✅ User Login
- Secure login with username and password
- "Remember me" functionality keeps users logged in
- Session management using Flask-Login
- Failed login attempts show error messages

### ✅ Data Separation
- Each user sees only their own listings
- Listings are linked to users via `user_id` foreign key
- Database queries automatically filter by logged-in user
- Users cannot access or modify other users' data

### ✅ Security Features
- Passwords hashed with PBKDF2-SHA256
- CSRF protection (Flask default)
- Session-based authentication
- @login_required decorator protects all routes
- Ownership verification before delete/edit operations

## How It Works

### Database Schema

**Users Table:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
)
```

**Listings Table (updated):**
```sql
CREATE TABLE listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,  -- Links to users table
    -- ... other columns ...
    FOREIGN KEY (user_id) REFERENCES users(id)
)
```

### Authentication Flow

1. **First Visit:**
   - User is redirected to `/login`
   - Can choose to login or register

2. **Registration:**
   - User fills out registration form
   - Password is hashed before storage
   - User is automatically logged in
   - Redirected to home page

3. **Login:**
   - User enters username and password
   - Password is verified against hash
   - Session is created
   - Last login timestamp updated
   - Redirected to home page

4. **Using the App:**
   - All routes require authentication
   - Listings automatically filtered by `current_user.id`
   - User sees only their own data

5. **Logout:**
   - User clicks logout in navigation
   - Session is cleared
   - Redirected to login page

## Cloud Deployment Benefits

### Multi-Tenant Architecture
When deployed to cloud platforms (Render, Railway, etc.), each user gets:

- ✅ **Separate Data:** Complete isolation from other users
- ✅ **Own Inventory:** Personal storage location tracking
- ✅ **Privacy:** Other users cannot see your listings
- ✅ **Scalability:** Support unlimited users on one server
- ✅ **Cost-Effective:** One server, many users

### No Setup Required for Users
Users just need to:
1. Visit your deployed URL
2. Click "Register"
3. Create an account
4. Start using the app immediately!

## Migration for Existing Data

When you first run the updated app with an existing database:

1. **Automatic Migration:**
   - `user_id` column is added to listings table
   - Default user (id=1) is created if no users exist
   - Existing listings are assigned to user_id=1

2. **Default Credentials:**
   - Username: `admin`
   - Email: `admin@localhost`
   - Password: (randomly generated, shown in console)
   - **IMPORTANT:** Change this password after first login!

## Usage Examples

### For Individual Users
Deploy on your own server, create one account, use it yourself.

### For Friends/Family
Deploy to cloud, share the URL:
- Friend 1: Creates account → sees only their inventory
- Friend 2: Creates account → sees only their inventory
- Complete data separation

### For Reseller Communities
Deploy one instance for your team:
- Each member creates an account
- Everyone manages their own inventory
- Optional: Export/share data via CSV

## Configuration

### Environment Variables

**Required for production:**
```env
FLASK_SECRET_KEY=your-super-secret-key-change-this
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Security Recommendations

**For Production:**
1. ✅ Use a strong `FLASK_SECRET_KEY`
2. ✅ Use HTTPS (automatic on Render/Railway)
3. ✅ Use a production WSGI server (gunicorn)
4. ✅ Enable rate limiting (optional)
5. ✅ Regular database backups

**Example production command:**
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 web_app:app
```

## API Endpoints

### Public (No Authentication Required)
- `GET /login` - Login page
- `POST /login` - Login submission
- `GET /register` - Registration page
- `POST /register` - Registration submission

### Protected (Authentication Required)
- `GET /` - Home page
- `GET /create` - Create listing page
- `GET /drafts` - View user's drafts
- `GET /listings` - View user's listings
- `POST /api/upload-photos` - Upload photos
- `POST /api/analyze` - Analyze with AI
- `POST /api/save-draft` - Save listing
- `GET /api/export-csv` - Export user's data
- `POST /api/import-csv` - Import user's data
- `POST /api/mark-sold` - Mark as sold
- `DELETE /api/delete-draft/:id` - Delete listing
- `GET /logout` - Logout

## Troubleshooting

### "Please log in to access this page"
- You're not logged in
- Session expired
- Solution: Go to `/login` and log in

### "Invalid username or password"
- Check username (case-sensitive)
- Check password
- Ensure caps lock is off

### "Username already exists"
- Someone already registered with that username
- Choose a different username

### "Email already registered"
- You or someone else already used that email
- Use a different email or login

### Lost Password
Currently there's no password reset feature. Options:
1. Remember your password
2. Contact server admin
3. Create new account with different email

## Future Enhancements

Possible features to add:
- [ ] Password reset via email
- [ ] Profile settings page
- [ ] Change password functionality
- [ ] Email verification
- [ ] Two-factor authentication
- [ ] OAuth login (Google, Facebook)
- [ ] Team/shared inventory features
- [ ] Admin dashboard

## Testing

To test the authentication system:

1. **Start the app:**
   ```bash
   python web_app.py
   ```

2. **Register a user:**
   - Visit `http://localhost:5000/register`
   - Fill out the form
   - Submit

3. **Create some listings:**
   - Use the app normally
   - Create a few test listings

4. **Logout and register another user:**
   - Click logout
   - Register with different username/email
   - Verify you see empty listings (data separation works!)

5. **Login as first user again:**
   - Verify your original listings are still there

## Support

For issues or questions:
- Check the main README.md
- Review this authentication guide
- Ensure you're using the latest code
- Check that migrations ran successfully

---

**Ready to deploy?** Check out `README_WEB_APP.md` for cloud deployment instructions!
