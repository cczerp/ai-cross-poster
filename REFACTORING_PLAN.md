# Web App Refactoring Plan - PostgreSQL Migration

## Overview
Split web_app.py (2494 lines) into 3 modular files:
1. **web_app.py** - Main entry, auth (357 lines) ✅ CREATED
2. **routes/listing_routes.py** - Listings + API endpoints (~1000 lines)
3. **routes/admin_routes.py** - Admin + Storage + Settings (~1000 lines)

## What's Been Created

### ✅ web_app_new.py (357 lines)
- Flask app initialization
- PostgreSQL database connection
- User model (PostgreSQL RealDictCursor compatible)
- Flask-Login setup
- Admin decorator
- Authentication routes:
  - `/login` - User login
  - `/register` - User registration
  - `/logout` - User logout
  - `/forgot-password` - Password reset request
  - `/reset-password/<token>` - Password reset with token
- Main route: `/` - Home page
- Blueprint registration

## Next Steps

### 1. Create listing_routes.py Blueprint
Extract these routes from original web_app.py:
- `/create` - Create listing page
- `/drafts` - View drafts
- `/listings` - View listings
- `/notifications` - View notifications
- `/api/upload-photos` - Upload photos API
- `/api/edit-photo` - Edit photo API
- `/api/analyze` - AI analysis API
- `/api/save-draft` - Save draft API
- `/api/export-csv` - Export CSV API
- `/api/post-to-platforms` - Post to platforms API
- All other `/api/*` listing-related endpoints

### 2. Create admin_routes.py Blueprint
Extract these routes from original web_app.py:
- `/storage/*` - All storage routes
- `/settings` - Settings page
- `/admin/*` - All admin routes
- `/api/admin/*` - All admin API endpoints
- `/api/storage/*` - All storage API endpoints
- `/api/settings/*` - All settings API endpoints
- `/api/baby-bird/*` - Baby bird API
- `/cards/*` - Card collection routes
- `/api/cards/*` - Card API endpoints

## PostgreSQL Compatibility Changes Made

1. **Removed SQLite-specific code**:
   - No more `sqlite3` imports
   - No `?` placeholders (handled by `db._get_cursor()`)
   - No tuple indexing like `result[0]`

2. **PostgreSQL RealDictCursor handling**:
   ```python
   # Old (SQLite):
   user_count = cursor.fetchone()[0]
   
   # New (PostgreSQL compatible):
   result = cursor.fetchone()
   user_count = result['count'] if isinstance(result, dict) else result[0]
   ```

3. **All `db.conn.cursor()` replaced with `db._get_cursor()`**:
   - Automatically converts `?` → `%s`
   - Adds `RETURNING id` to INSERT statements
   - Works with both PostgreSQL and SQLite

## File Structure
```
ai-cross-poster/
├── web_app.py (NEW - 357 lines)
├── web_app_original.py.bak (backup)
├── routes/
│   ├── __init__.py
│   ├── listing_routes.py (TO CREATE)
│   └── admin_routes.py (TO CREATE)
├── src/
│   └── database/
│       └── db.py (already PostgreSQL compatible)
└── templates/ (unchanged)
```

## Blueprint Template Structure

### listing_routes.py Template:
```python
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from src.database import get_db

listing_bp = Blueprint('listing', __name__)
db = get_db()

@listing_bp.route('/create')
def create_listing():
    # Route implementation
    pass

# ... more routes
```

### admin_routes.py Template:
```python
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from src.database import get_db

admin_bp = Blueprint('admin', __name__)
db = get_db()

@admin_bp.route('/admin')
@login_required
def admin_dashboard():
    # Route implementation
    pass

# ... more routes
```

## Testing After Refactoring

1. Replace old `web_app.py` with `web_app_new.py`:
   ```bash
   mv web_app.py web_app_old.py
   mv web_app_new.py web_app.py
   ```

2. Create the two blueprint files in `routes/`

3. Test locally:
   ```bash
   python web_app.py
   ```

4. Verify all routes work:
   - Login/Register
   - Create listing
   - Admin panel
   - Storage system
   - API endpoints

5. Deploy to Render

## Benefits of This Refactoring

1. **Modularity**: Each file has a single, clear purpose
2. **Maintainability**: ~800 lines per file instead of 2494
3. **PostgreSQL-only**: No more SQLite compatibility code
4. **Scalability**: Easy to add new route modules
5. **Testing**: Each blueprint can be tested independently

## Deployment Notes

- All environment variables remain the same
- Database connection string must be PostgreSQL
- No changes needed to templates or static files
- Gunicorn configuration unchanged

