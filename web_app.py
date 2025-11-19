#!/usr/bin/env python3
"""
AI Cross-Poster Web App
========================
Mobile-friendly web interface for inventory management and cross-platform listing.

Run with:
    python web_app.py

Or deploy to:
    - Heroku
    - DigitalOcean
    - AWS
    - Your own server
"""

import os
import uuid
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from src.database import get_db
import csv
from io import StringIO, BytesIO
from PIL import Image
import base64

# Platform adapters
from src.adapters.poshmark_adapter import PoshmarkAdapter
from src.adapters.all_platforms import (
    EtsyAdapter, ShopifyAdapter, RubyLaneAdapter,
    WooCommerceAdapter, FacebookShopsAdapter
)
from src.schema.unified_listing import UnifiedListing, Price, Photo, ListingCondition, ItemSpecifics

# Load environment
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['UPLOAD_FOLDER'] = './data/uploads'

# Ensure upload folder exists
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

# Initialize services
db = get_db()

# Create default admin account if no users exist
def create_default_admin():
    """Create default admin account (admin/admin) if no users exist"""
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        print("\n" + "="*60)
        print("No users found. Creating default admin account...")
        print("Username: admin")
        print("Password: admin")
        print("IMPORTANT: Please change this password after first login!")
        print("="*60 + "\n")

        password_hash = generate_password_hash('admin')
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, is_admin, is_active, email_verified)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('admin', 'admin@resellgenius.local', password_hash, 1, 1, 1))
        db.conn.commit()

create_default_admin()

# Initialize notification manager (optional)
notification_manager = None
try:
    from src.notifications import NotificationManager
    notification_manager = NotificationManager.from_env()
except Exception:
    # Notifications are optional, app will work without them
    pass

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'


# ============================================================================
# PLATFORM POSTING HELPERS
# ============================================================================

# Platform types: 'api' (automated) or 'csv' (manual upload)
PLATFORM_CONFIG = {
    'poshmark': {
        'type': 'csv',
        'name': 'Poshmark',
        'instructions': [
            '1. Log into your Poshmark account',
            '2. Go to https://poshmark.com/sell/bulk',
            '3. Click "Upload CSV"',
            '4. Select the downloaded CSV file',
            '5. Review and publish your listings'
        ]
    },
    'rubylane': {
        'type': 'csv',
        'name': 'Ruby Lane',
        'instructions': [
            '1. Log into your Ruby Lane seller account',
            '2. Go to Seller Tools → Bulk Upload',
            '3. Upload the CSV file',
            '4. Review and activate listings'
        ]
    },
    'threadup': {
        'type': 'csv',
        'name': 'ThredUp',
        'instructions': [
            '1. Log into your ThredUp seller account',
            '2. Navigate to bulk listing tool',
            '3. Upload the CSV file',
            '4. Confirm listings'
        ]
    },
    'depop': {
        'type': 'csv',
        'name': 'Depop',
        'instructions': [
            '1. Depop does not support CSV bulk upload',
            '2. You must list items individually in the Depop app',
            '3. Use the listing details from your export as a guide'
        ]
    },
    'etsy': {
        'type': 'api',
        'name': 'Etsy',
        'requires_credentials': True
    },
    'shopify': {
        'type': 'api',
        'name': 'Shopify',
        'requires_credentials': True
    },
    'facebook': {
        'type': 'api',
        'name': 'Facebook Shops',
        'requires_credentials': True
    },
    'woocommerce': {
        'type': 'api',
        'name': 'WooCommerce',
        'requires_credentials': True
    }
}


def convert_listing_to_unified(listing_dict: dict) -> UnifiedListing:
    """Convert database listing to UnifiedListing format"""

    # Parse photos
    photos = []
    if listing_dict.get('photos'):
        photo_paths = json.loads(listing_dict['photos']) if isinstance(listing_dict['photos'], str) else listing_dict['photos']
        for i, path in enumerate(photo_paths):
            # Convert local path to URL if needed
            photo_url = path if path.startswith('http') else f"/uploads/{Path(path).name}"
            photos.append(Photo(
                url=photo_url,
                local_path=path,
                is_primary=(i == 0)
            ))

    # Map condition
    condition_map = {
        'new': ListingCondition.NEW,
        'like_new': ListingCondition.LIKE_NEW,
        'excellent': ListingCondition.EXCELLENT,
        'good': ListingCondition.GOOD,
        'fair': ListingCondition.FAIR,
        'poor': ListingCondition.POOR
    }
    condition = condition_map.get(listing_dict.get('condition', 'good'), ListingCondition.GOOD)

    # Create UnifiedListing
    return UnifiedListing(
        title=listing_dict.get('title', ''),
        description=listing_dict.get('description', ''),
        price=Price(amount=float(listing_dict.get('price', 0))),
        condition=condition,
        photos=photos,
        item_specifics=ItemSpecifics(
            brand=listing_dict.get('brand'),
            size=listing_dict.get('size'),
            color=listing_dict.get('color'),
            material=listing_dict.get('material')
        ),
        sku=listing_dict.get('sku')
    )


# ============================================================================
# USER MODEL
# ============================================================================

class User(UserMixin):
    """User model for Flask-Login"""

    def __init__(self, user_id, username, email, is_admin=False, is_active=True):
        self.id = user_id
        self.username = username
        self.email = email
        self.is_admin = is_admin
        self._is_active = is_active  # Store in private attribute

    @property
    def is_active(self):
        """Override Flask-Login's is_active to use database value"""
        return self._is_active

    @staticmethod
    def get(user_id):
        """Get user by ID"""
        user_data = db.get_user_by_id(user_id)
        if user_data:
            return User(
                user_data['id'],
                user_data['username'],
                user_data['email'],
                user_data.get('is_admin', False),
                user_data.get('is_active', True)
            )
        return None


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.get(int(user_id))


# ============================================================================
# ADMIN DECORATOR
# ============================================================================

from functools import wraps

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You need administrator privileges to access this page.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')

        user_data = db.get_user_by_username(username)

        if user_data and check_password_hash(user_data['password_hash'], password):
            # Check if account is active
            if not user_data.get('is_active', True):
                error_msg = 'Your account has been deactivated. Please contact an administrator.'
                if request.is_json:
                    return jsonify({'error': error_msg}), 401
                flash(error_msg, 'error')
                return render_template('login.html')

            user = User(
                user_data['id'],
                user_data['username'],
                user_data['email'],
                user_data.get('is_admin', False),
                user_data.get('is_active', True)
            )
            login_user(user, remember=True)
            db.update_last_login(user_data['id'])

            # Log activity
            db.log_activity(
                action='login',
                user_id=user_data['id'],
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )

            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('index')})
            return redirect(url_for('index'))
        else:
            error_msg = 'Invalid username or password'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        # Validation
        if not username or not email or not password:
            error_msg = 'All fields are required'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('register.html')

        if len(password) < 6:
            error_msg = 'Password must be at least 6 characters'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('register.html')

        # Check if user exists
        if db.get_user_by_username(username):
            error_msg = 'Username already exists'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('register.html')

        if db.get_user_by_email(email):
            error_msg = 'Email already registered'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('register.html')

        try:
            # Create user
            password_hash = generate_password_hash(password)
            user_id = db.create_user(username, email, password_hash)

            # Log activity
            db.log_activity(
                action='register',
                user_id=user_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )

            # Auto-login
            user = User(user_id, username, email, is_admin=False, is_active=True)
            login_user(user, remember=True)

            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('index')})
            flash('Account created successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            error_msg = f'Registration failed: {str(e)}'
            if request.is_json:
                return jsonify({'error': error_msg}), 500
            flash(error_msg, 'error')
            return render_template('register.html')

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    # Log activity before logout
    db.log_activity(
        action='logout',
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password"""
    if request.method == 'POST':
        email = request.form.get('email')

        user = db.get_user_by_email(email)
        if user:
            # Generate reset token
            import secrets
            token = secrets.token_urlsafe(32)
            db.set_reset_token(user['id'], token, expiry_hours=24)

            # In production, send email here
            # For now, print to console
            reset_link = url_for('reset_password', token=token, _external=True)
            print(f"\n{'='*60}")
            print(f"PASSWORD RESET LINK FOR {email}:")
            print(f"{reset_link}")
            print(f"{'='*60}\n")

            flash('If that email exists, a password reset link has been sent.', 'info')
        else:
            # Don't reveal if email exists
            flash('If that email exists, a password reset link has been sent.', 'info')

        return redirect(url_for('login'))

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    user = db.verify_reset_token(token)

    if not user:
        flash('Invalid or expired reset link', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not password or len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('reset_password.html', token=token)

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html', token=token)

        # Update password
        password_hash = generate_password_hash(password)
        db.update_password(user['id'], password_hash)

        flash('Password reset successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Home page - accessible to guests"""
    # Show guest landing page if not logged in
    if not current_user.is_authenticated:
        return render_template('index.html', is_guest=True)
    return render_template('index.html', is_guest=False)


@app.route('/create')
def create_listing():
    """Create new listing page - accessible to guests for AI demo"""
    is_guest = not current_user.is_authenticated
    draft_id = request.args.get('draft_id', type=int)
    return render_template('create.html', is_guest=is_guest, draft_id=draft_id)


@app.route('/drafts')
@login_required
def drafts():
    """View saved drafts"""
    drafts_list = db.get_drafts(limit=100, user_id=current_user.id)
    return render_template('drafts.html', drafts=drafts_list)


@app.route('/listings')
@login_required
def listings():
    """View active listings"""
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT l.*, GROUP_CONCAT(pl.platform || ':' || pl.status) as platform_statuses
        FROM listings l
        LEFT JOIN platform_listings pl ON l.id = pl.listing_id
        WHERE l.status != 'draft' AND l.user_id = ?
        GROUP BY l.id
        ORDER BY l.created_at DESC
        LIMIT 50
    """, (current_user.id,))
    listings_list = [dict(row) for row in cursor.fetchall()]
    return render_template('listings.html', listings=listings_list)


@app.route('/notifications')
@login_required
def notifications():
    """View notifications"""
    if notification_manager:
        try:
            notifs = notification_manager.get_recent_notifications(limit=50)
            # Parse JSON data field if it's a string
            for notif in notifs:
                if notif.get('data') and isinstance(notif['data'], str):
                    try:
                        notif['data'] = json.loads(notif['data'])
                    except:
                        notif['data'] = {}
        except Exception as e:
            print(f"Error loading notifications: {e}")
            notifs = []
    else:
        notifs = []
    return render_template('notifications.html', notifications=notifs)


# ========================================
# STORAGE ROUTES (Standalone Organization Tool)
# ========================================

@app.route('/storage')
@login_required
def storage():
    """Main storage page - choose mode"""
    storage_map = db.get_storage_map(current_user.id)
    return render_template('storage.html', storage_map=storage_map)


@app.route('/storage/clothing')
@login_required
def storage_clothing():
    """Clothing bin storage system"""
    bins = db.get_storage_bins(current_user.id, bin_type='clothing')
    return render_template('storage_clothing.html', bins=bins)


@app.route('/storage/cards')
@login_required
def storage_cards():
    """Card storage system (A1/A2)"""
    bins = db.get_storage_bins(current_user.id, bin_type='cards')

    # Create default Bin A if no bins exist
    if not bins:
        bin_id = db.create_storage_bin(current_user.id, 'A', 'cards', 'Default card bin')
        bins = db.get_storage_bins(current_user.id, bin_type='cards')

    return render_template('storage_cards.html', bins=bins)


@app.route('/storage/map')
@login_required
def storage_map():
    """Visual storage map"""
    storage_map = db.get_storage_map(current_user.id)
    return render_template('storage_map.html', storage_map=storage_map)


@app.route('/api/storage/create-bin', methods=['POST'])
@login_required
def create_storage_bin():
    """Create new storage bin"""
    data = request.json

    try:
        bin_name = data['bin_name']
        bin_type = data['bin_type']
        description = data.get('description')

        bin_id = db.create_storage_bin(current_user.id, bin_name, bin_type, description)

        return jsonify({'success': True, 'bin_id': bin_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/create-section', methods=['POST'])
@login_required
def create_storage_section():
    """Create section within bin"""
    data = request.json

    try:
        bin_id = int(data['bin_id'])
        section_name = data['section_name']
        capacity = data.get('capacity')

        section_id = db.create_storage_section(bin_id, section_name, capacity)

        return jsonify({'success': True, 'section_id': section_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/add-item', methods=['POST'])
@login_required
def add_storage_item():
    """Add item to storage"""
    data = request.json

    try:
        bin_id = int(data['bin_id'])
        section_id = int(data['section_id']) if data.get('section_id') else None
        item_type = data.get('item_type')
        category = data.get('category')
        title = data.get('title')
        description = data.get('description')
        quantity = int(data.get('quantity', 1))
        photos = data.get('photos', [])
        notes = data.get('notes')

        # Get bin info for ID generation
        bins = db.get_storage_bins(current_user.id)
        bin = next((b for b in bins if b['id'] == bin_id), None)

        if not bin:
            return jsonify({'error': 'Bin not found'}), 404

        # Get section name if section_id provided
        section_name = None
        if section_id:
            sections = db.get_storage_sections(bin_id)
            section = next((s for s in sections if s['id'] == section_id), None)
            if section:
                section_name = section['section_name']

        # Generate storage ID
        storage_id = db.generate_storage_id(
            current_user.id,
            bin['bin_name'],
            section_name,
            category
        )

        # Add item
        item_id = db.add_storage_item(
            current_user.id,
            storage_id,
            bin_id,
            section_id,
            item_type,
            category,
            title,
            description,
            quantity,
            photos,
            notes
        )

        return jsonify({
            'success': True,
            'item_id': item_id,
            'storage_id': storage_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/find', methods=['GET'])
@login_required
def find_storage_item():
    """Find item by storage ID"""
    storage_id = request.args.get('storage_id')

    if not storage_id:
        return jsonify({'error': 'storage_id required'}), 400

    item = db.find_storage_item(current_user.id, storage_id)

    if item:
        return jsonify({'success': True, 'item': item})
    else:
        return jsonify({'error': 'Item not found'}), 404


@app.route('/api/storage/items', methods=['GET'])
@login_required
def get_storage_items():
    """Get storage items with filters"""
    bin_id = request.args.get('bin_id', type=int)
    section_id = request.args.get('section_id', type=int)
    item_type = request.args.get('item_type')
    limit = request.args.get('limit', 100, type=int)

    items = db.get_storage_items(
        current_user.id,
        bin_id=bin_id,
        section_id=section_id,
        item_type=item_type,
        limit=limit
    )

    return jsonify({'success': True, 'items': items})


@app.route('/settings')
@login_required
def settings():
    """User settings page"""
    user = db.get_user_by_id(current_user.id)
    marketplace_creds = db.get_all_marketplace_credentials(current_user.id)

    # Convert to dict for easier template access
    creds_dict = {cred['platform']: cred for cred in marketplace_creds}

    # All supported platforms with icons and display names
    platforms = [
        {'id': 'etsy', 'name': 'Etsy', 'icon': 'fas fa-shopping-cart', 'color': 'text-warning'},
        {'id': 'poshmark', 'name': 'Poshmark', 'icon': 'fas fa-shopping-bag', 'color': 'text-primary'},
        {'id': 'depop', 'name': 'Depop', 'icon': 'fas fa-tshirt', 'color': 'text-info'},
        {'id': 'offerup', 'name': 'OfferUp', 'icon': 'fas fa-handshake', 'color': 'text-success'},
        {'id': 'shopify', 'name': 'Shopify', 'icon': 'fas fa-store', 'color': 'text-success'},
        {'id': 'craigslist', 'name': 'Craigslist', 'icon': 'fas fa-list', 'color': 'text-secondary'},
        {'id': 'facebook', 'name': 'Facebook Marketplace', 'icon': 'fab fa-facebook', 'color': 'text-primary'},
        {'id': 'tiktok_shop', 'name': 'TikTok Shop', 'icon': 'fab fa-tiktok', 'color': 'text-dark'},
        {'id': 'woocommerce', 'name': 'WooCommerce', 'icon': 'fab fa-wordpress', 'color': 'text-purple'},
        {'id': 'nextdoor', 'name': 'Nextdoor', 'icon': 'fas fa-home', 'color': 'text-success'},
        {'id': 'varagesale', 'name': 'VarageSale', 'icon': 'fas fa-store-alt', 'color': 'text-warning'},
        {'id': 'ruby_lane', 'name': 'Ruby Lane', 'icon': 'fas fa-gem', 'color': 'text-danger'},
        {'id': 'ecrater', 'name': 'eCRATER', 'icon': 'fas fa-box', 'color': 'text-info'},
        {'id': 'bonanza', 'name': 'Bonanza', 'icon': 'fas fa-star', 'color': 'text-warning'},
        {'id': 'kijiji', 'name': 'Kijiji', 'icon': 'fas fa-newspaper', 'color': 'text-danger'},
        {'id': 'grailed', 'name': 'Grailed', 'icon': 'fas fa-user-tie', 'color': 'text-dark'},
        {'id': 'vinted', 'name': 'Vinted', 'icon': 'fas fa-recycle', 'color': 'text-success'},
        {'id': 'mercado_libre', 'name': 'Mercado Libre', 'icon': 'fas fa-globe-americas', 'color': 'text-warning'},
        {'id': 'tradesy', 'name': 'Tradesy', 'icon': 'fas fa-exchange-alt', 'color': 'text-info'},
        {'id': 'vestiaire', 'name': 'Vestiaire Collective', 'icon': 'fas fa-crown', 'color': 'text-purple'},
        {'id': 'rebag', 'name': 'Rebag', 'icon': 'fas fa-shopping-bag', 'color': 'text-danger'},
        {'id': 'thredup', 'name': 'ThredUp', 'icon': 'fas fa-tshirt', 'color': 'text-primary'},
        {'id': 'personal_website', 'name': 'Personal Website', 'icon': 'fas fa-globe', 'color': 'text-secondary'},
        {'id': 'other', 'name': 'Other Platform', 'icon': 'fas fa-ellipsis-h', 'color': 'text-muted'},
    ]

    return render_template('settings.html', user=user, credentials=creds_dict, platforms=platforms)


# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    stats = db.get_system_stats()
    users = db.get_all_users(include_inactive=True)
    recent_activity = db.get_activity_logs(limit=20)
    return render_template('admin/dashboard.html', stats=stats, users=users, recent_activity=recent_activity)


@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin user management"""
    users = db.get_all_users(include_inactive=True)
    return render_template('admin/users.html', users=users)


@app.route('/admin/activity')
@admin_required
def admin_activity():
    """Admin activity logs"""
    page = request.args.get('page', 1, type=int)
    limit = 50
    offset = (page - 1) * limit

    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')

    logs = db.get_activity_logs(user_id=user_id, action=action, limit=limit, offset=offset)

    return render_template('admin/activity.html', logs=logs, page=page)


@app.route('/admin/user/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    """Admin user detail view"""
    user = db.get_user_by_id(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin_users'))

    # Get user's listings
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM listings WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", (user_id,))
    listings = [dict(row) for row in cursor.fetchall()]

    # Get user's activity
    activity = db.get_activity_logs(user_id=user_id, limit=50)

    return render_template('admin/user_detail.html', user=user, listings=listings, activity=activity)


# ============================================================================
# ADMIN API ENDPOINTS
# ============================================================================

@app.route('/api/admin/user/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def admin_toggle_user_admin(user_id):
    """Toggle user admin status"""
    try:
        # Prevent self-demotion
        if user_id == current_user.id:
            return jsonify({'error': 'You cannot change your own admin status'}), 400

        success = db.toggle_user_admin(user_id)

        if success:
            # Log activity
            db.log_activity(
                action='toggle_admin',
                user_id=current_user.id,
                resource_type='user',
                resource_id=user_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/user/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def admin_toggle_user_active(user_id):
    """Toggle user active status"""
    try:
        # Prevent self-deactivation
        if user_id == current_user.id:
            return jsonify({'error': 'You cannot deactivate your own account'}), 400

        success = db.toggle_user_active(user_id)

        if success:
            # Log activity
            db.log_activity(
                action='toggle_active',
                user_id=current_user.id,
                resource_type='user',
                resource_id=user_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/user/<int:user_id>/delete', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """Delete a user (admin)"""
    try:
        # Prevent self-deletion
        if user_id == current_user.id:
            return jsonify({'error': 'You cannot delete your own account'}), 400

        # Log activity before deletion
        db.log_activity(
            action='delete_user',
            user_id=current_user.id,
            resource_type='user',
            resource_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        db.delete_user(user_id)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/upload-photos', methods=['POST'])
def upload_photos():
    """Handle photo uploads - accessible to guests"""
    if 'photos' not in request.files:
        return jsonify({'error': 'No photos provided'}), 400

    files = request.files.getlist('photos')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No photos selected'}), 400

    # Save photos
    photo_paths = []
    for file in files:
        if file:
            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            photo_paths.append(filepath)

    # Store in session
    session['photo_paths'] = photo_paths

    return jsonify({
        'success': True,
        'count': len(photo_paths),
        'paths': photo_paths
    })


@app.route('/api/edit-photo', methods=['POST'])
def edit_photo():
    """
    Edit a photo - crop, remove background, resize
    FREE feature that competitors charge heavily for!
    """
    try:
        data = request.get_json()

        if not data or 'image' not in data or 'operation' not in data:
            return jsonify({'error': 'Missing image or operation'}), 400

        # Decode base64 image
        image_data = data['image']
        if image_data.startswith('data:image'):
            # Remove data URL prefix
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)
        img = Image.open(BytesIO(image_bytes))

        operation = data['operation']

        if operation == 'crop':
            # Crop image with provided coordinates
            crop_data = data.get('crop', {})
            x = int(crop_data.get('x', 0))
            y = int(crop_data.get('y', 0))
            width = int(crop_data.get('width', img.width))
            height = int(crop_data.get('height', img.height))

            img = img.crop((x, y, x + width, y + height))

        elif operation == 'remove-bg':
            # Remove background using rembg (FREE!)
            from rembg import remove

            # Convert PIL Image to bytes
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            # Remove background
            output = remove(img_byte_arr)

            # Convert back to PIL Image
            img = Image.open(BytesIO(output))

        elif operation == 'resize':
            # Resize/enlarge image
            new_width = int(data.get('width', img.width))
            new_height = int(data.get('height', img.height))
            img = img.resize((new_width, new_height), Image.LANCZOS)

        else:
            return jsonify({'error': f'Unknown operation: {operation}'}), 400

        # Save edited image to temp location
        filename = secure_filename(f"edited_{uuid.uuid4()}.png")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        img.save(filepath, 'PNG')

        # Convert to base64 for preview
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')

        return jsonify({
            'success': True,
            'image': f'data:image/png;base64,{img_base64}',
            'filepath': filepath
        })

    except Exception as e:
        print(f"Error editing photo: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_photos():
    """Analyze photos with AI - accessible to guests"""
    photo_paths = session.get('photo_paths', [])

    if not photo_paths:
        return jsonify({'error': 'No photos to analyze'}), 400

    try:
        from src.ai.gemini_classifier import GeminiClassifier
        from src.ai.market_analyzer import MarketAnalyzer
        from src.schema import Photo

        # Create photo objects
        photo_objects = [
            Photo(url="", local_path=p, order=i, is_primary=(i == 0))
            for i, p in enumerate(photo_paths)
        ]

        # Analyze with Gemini
        classifier = GeminiClassifier.from_env()
        analysis = classifier.analyze_item(photo_objects)

        if "error" in analysis:
            return jsonify({'error': analysis['error']}), 500

        # Add market analysis (sell-through rate)
        try:
            market_analyzer = MarketAnalyzer(db=db)
            market_data = market_analyzer.analyze_market(
                item_name=analysis.get('item_name', ''),
                brand=analysis.get('brand'),
                category=analysis.get('category'),
                price=analysis.get('suggested_price')
            )
            analysis['market_analysis'] = market_data
        except Exception as e:
            print(f"Market analysis failed: {e}")
            analysis['market_analysis'] = None

        return jsonify({
            'success': True,
            'analysis': analysis
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/save-draft', methods=['POST'])
@login_required
def save_draft():
    """Save listing as draft or post as active (create or update)"""
    data = request.json
    draft_id = data.get('draft_id')
    listing_uuid = data.get('listing_uuid')
    status = data.get('status', 'draft')  # 'draft' or 'active'

    # Get photos from session or use existing ones
    new_photo_paths = session.get('photo_paths', [])

    try:
        import shutil

        # EDITING EXISTING DRAFT
        if draft_id and listing_uuid:
            # Get existing listing
            listing = db.get_listing(draft_id)
            if not listing:
                return jsonify({'error': 'Listing not found'}), 404

            # Verify ownership
            if listing.get('user_id') != current_user.id:
                return jsonify({'error': 'Unauthorized'}), 403

            # Get existing photos
            existing_photos = []
            if listing.get('photos'):
                try:
                    existing_photos = json.loads(listing['photos']) if isinstance(listing['photos'], str) else listing['photos']
                except:
                    existing_photos = []

            # Handle photos
            draft_photos_dir = Path("data/draft_photos") / listing_uuid
            draft_photos_dir.mkdir(parents=True, exist_ok=True)

            # If new photos were uploaded, append them to existing ones
            if new_photo_paths:
                permanent_photo_paths = existing_photos.copy()
                start_index = len(existing_photos)

                for i, photo_path in enumerate(new_photo_paths):
                    ext = Path(photo_path).suffix
                    new_filename = f"photo_{start_index + i:02d}{ext}"
                    permanent_path = draft_photos_dir / new_filename

                    shutil.copy2(photo_path, permanent_path)
                    permanent_photo_paths.append(str(permanent_path))

                # Clear session
                session.pop('photo_paths', None)
            else:
                # No new photos, keep existing ones
                permanent_photo_paths = existing_photos

            # Update listing in database
            cursor = db.conn.cursor()
            cursor.execute("""
                UPDATE listings SET
                    title = ?,
                    description = ?,
                    price = ?,
                    cost = ?,
                    condition = ?,
                    item_type = ?,
                    quantity = ?,
                    storage_location = ?,
                    sku = ?,
                    upc = ?,
                    photos = ?,
                    attributes = ?,
                    status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            """, (
                data.get('title', 'Untitled'),
                data.get('description', ''),
                float(data.get('price', 0)),
                float(data.get('cost')) if data.get('cost') else None,
                data.get('condition', 'good'),
                data.get('item_type', 'general'),
                int(data.get('quantity', 1)),
                data.get('storage_location'),
                data.get('sku'),
                data.get('upc'),
                json.dumps(permanent_photo_paths),
                json.dumps({
                    'brand': data.get('brand'),
                    'size': data.get('size'),
                    'color': data.get('color'),
                    'shipping_cost': float(data.get('shipping_cost', 0)),
                }),
                status,
                draft_id,
                current_user.id
            ))
            db.conn.commit()

            msg = 'Listing posted successfully' if status == 'active' else 'Listing updated successfully'
            return jsonify({
                'success': True,
                'listing_id': draft_id,
                'message': msg
            })

        # CREATING NEW DRAFT
        else:
            if not new_photo_paths:
                return jsonify({'error': 'No photos uploaded'}), 400

            listing_uuid = str(uuid.uuid4())

            # Copy photos to permanent storage
            draft_photos_dir = Path("data/draft_photos") / listing_uuid
            draft_photos_dir.mkdir(parents=True, exist_ok=True)

            permanent_photo_paths = []
            for i, photo_path in enumerate(new_photo_paths):
                ext = Path(photo_path).suffix
                new_filename = f"photo_{i:02d}{ext}"
                permanent_path = draft_photos_dir / new_filename

                shutil.copy2(photo_path, permanent_path)
                permanent_photo_paths.append(str(permanent_path))

            # Save to database
            listing_id = db.create_listing(
                listing_uuid=listing_uuid,
                title=data.get('title', 'Untitled'),
                description=data.get('description', ''),
                price=float(data.get('price', 0)),
                condition=data.get('condition', 'good'),
                photos=permanent_photo_paths,
                user_id=current_user.id,
                cost=float(data.get('cost')) if data.get('cost') else None,
                item_type=data.get('item_type', 'general'),
                quantity=int(data.get('quantity', 1)),
                storage_location=data.get('storage_location'),
                sku=data.get('sku'),
                upc=data.get('upc'),
                status=status,  # Use status parameter
                attributes={
                    'brand': data.get('brand'),
                    'size': data.get('size'),
                    'color': data.get('color'),
                    'shipping_cost': float(data.get('shipping_cost', 0)),
                }
            )

            # Clear session
            session.pop('photo_paths', None)

            msg = 'Listing posted successfully' if status == 'active' else 'Listing created successfully'
            return jsonify({
                'success': True,
                'listing_id': listing_id,
                'message': msg
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export-csv', methods=['GET'])
@login_required
def export_csv():
    """Export all drafts to CSV"""
    try:
        drafts = db.get_drafts(limit=1000, user_id=current_user.id)

        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['ID', 'Title', 'Description', 'Price', 'Cost', 'Condition',
                        'Brand', 'Size', 'Color', 'Storage Location', 'Quantity',
                        'Shipping Cost', 'Photo Paths', 'Created'])

        # Data
        for draft in drafts:
            # Parse attributes
            attrs = {}
            if draft.get('attributes'):
                try:
                    attrs = json.loads(draft['attributes'])
                except:
                    pass

            # Parse photos and convert to full URLs
            photos = []
            if draft.get('photos'):
                try:
                    photos = json.loads(draft['photos']) if isinstance(draft['photos'], str) else draft['photos']
                except:
                    photos = []

            # Convert file paths to full URLs
            photo_urls = []
            for photo_path in photos:
                # Create full URL: http://localhost:5000/data/draft_photos/uuid/photo_00.jpg
                photo_url = request.host_url.rstrip('/') + '/' + photo_path
                photo_urls.append(photo_url)

            # Join photo URLs with semicolon
            photo_paths_str = ';'.join(photo_urls) if photo_urls else ''

            writer.writerow([
                draft['id'],
                draft['title'],
                draft['description'],
                draft['price'],
                draft.get('cost', ''),
                draft['condition'],
                attrs.get('brand', ''),
                attrs.get('size', ''),
                attrs.get('color', ''),
                draft.get('storage_location', ''),
                draft.get('quantity', 1),
                attrs.get('shipping_cost', ''),
                photo_paths_str,
                draft['created_at']
            ])

        # Send file
        from flask import Response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=listings.csv'}
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/import-csv', methods=['POST'])
@login_required
def import_csv():
    """Import CSV to update storage locations"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Read CSV
        stream = StringIO(file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)

        updated = 0
        for row in reader:
            listing_id = row.get('ID')
            storage_location = row.get('Storage Location')

            if listing_id and storage_location:
                # Update storage location (only for user's own listings)
                cursor = db.conn.cursor()
                cursor.execute("""
                    UPDATE listings
                    SET storage_location = ?
                    WHERE id = ? AND user_id = ?
                """, (storage_location, listing_id, current_user.id))
                db.conn.commit()
                updated += 1

        return jsonify({
            'success': True,
            'updated': updated
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bulk-post', methods=['POST'])
@login_required
def bulk_post():
    """
    Bulk post multiple listings to selected platforms.
    Supports both API automation and CSV generation.
    """
    data = request.json

    try:
        listing_ids = data.get('listing_ids', [])
        platforms = data.get('platforms', [])

        if not listing_ids:
            return jsonify({'error': 'No listings selected'}), 400

        if not platforms:
            return jsonify({'error': 'No platforms selected'}), 400

        # Separate platforms by type
        csv_platforms = [p for p in platforms if PLATFORM_CONFIG.get(p, {}).get('type') == 'csv']
        api_platforms = [p for p in platforms if PLATFORM_CONFIG.get(p, {}).get('type') == 'api']

        # Get all listings
        listings = []
        for listing_id in listing_ids:
            listing = db.get_listing(listing_id)
            if listing and listing.get('user_id') == current_user.id:
                listings.append(listing)

        if not listings:
            return jsonify({'error': 'No valid listings found'}), 404

        results = {
            'csv_files': {},
            'api_results': [],
            'success': True
        }

        # Generate CSV files for CSV platforms
        for platform in csv_platforms:
            try:
                # Convert to UnifiedListings
                unified_listings = [convert_listing_to_unified(l) for l in listings]

                # Generate CSV based on platform
                if platform == 'poshmark':
                    adapter = PoshmarkAdapter(output_dir='./data/csv_exports')
                    csv_path = adapter.generate_csv(unified_listings)
                elif platform == 'rubylane':
                    adapter = RubyLaneAdapter(output_dir='./data/csv_exports')
                    csv_path = adapter.generate_csv(unified_listings)
                elif platform in ['threadup', 'depop']:
                    # Generic CSV for platforms without specific adapters
                    csv_path = generate_generic_csv(unified_listings, platform)
                else:
                    continue

                # Save CSV file info
                results['csv_files'][platform] = {
                    'filename': Path(csv_path).name,
                    'path': csv_path,
                    'download_url': f'/api/download-csv/{Path(csv_path).name}',
                    'instructions': PLATFORM_CONFIG[platform]['instructions'],
                    'platform_name': PLATFORM_CONFIG[platform]['name']
                }

                # Update listing platform statuses
                for listing in listings:
                    current_statuses = listing.get('platform_statuses', '') or ''
                    status_list = [s for s in current_statuses.split(',') if s and s.strip()]
                    status_list = [s for s in status_list if not s.startswith(f"{platform}:")]
                    status_list.append(f"{platform}:csv_ready")
                    db.update_listing(listing['id'], {'platform_statuses': ','.join(status_list)})

            except Exception as e:
                results['csv_files'][platform] = {
                    'error': str(e),
                    'platform_name': PLATFORM_CONFIG[platform]['name']
                }
                results['success'] = False

        # Post to API platforms (when credentials are configured)
        for platform in api_platforms:
            platform_config = PLATFORM_CONFIG.get(platform, {})

            # Check if user has credentials for this platform
            creds_data = db.get_marketplace_credentials(current_user.id, f"api_{platform}")

            if not creds_data or not creds_data.get('password'):
                # No credentials configured
                for listing in listings:
                    results['api_results'].append({
                        'listing_id': listing['id'],
                        'platform': platform,
                        'status': 'credentials_required',
                        'message': f'Please configure {platform_config["name"]} API credentials in Settings to enable automated posting.',
                        'platform_name': platform_config['name']
                    })

                    # Update status to show credentials needed
                    current_statuses = listing.get('platform_statuses', '') or ''
                    status_list = [s for s in current_statuses.split(',') if s and s.strip()]
                    status_list = [s for s in status_list if not s.startswith(f"{platform}:")]
                    status_list.append(f"{platform}:needs_credentials")
                    db.update_listing(listing['id'], {'platform_statuses': ','.join(status_list)})
            else:
                # Credentials are configured - attempt API posting
                try:
                    credentials = json.loads(creds_data['password'])

                    # Initialize appropriate adapter
                    adapter = None
                    if platform == 'etsy':
                        adapter = EtsyAdapter(
                            api_key=credentials.get('api_key'),
                            shop_id=credentials.get('shop_id')
                        )
                    elif platform == 'shopify':
                        adapter = ShopifyAdapter(
                            store_url=credentials.get('store_url'),
                            access_token=credentials.get('access_token')
                        )
                    elif platform == 'woocommerce':
                        adapter = WooCommerceAdapter(
                            store_url=credentials.get('store_url'),
                            consumer_key=credentials.get('consumer_key'),
                            consumer_secret=credentials.get('consumer_secret')
                        )
                    elif platform == 'facebook':
                        adapter = FacebookShopsAdapter(
                            access_token=credentials.get('access_token'),
                            catalog_id=credentials.get('catalog_id')
                        )

                    if adapter:
                        # Post each listing
                        for listing in listings:
                            unified_listing = convert_listing_to_unified(listing)
                            post_result = adapter.publish_listing(unified_listing)

                            if post_result.get('success'):
                                results['api_results'].append({
                                    'listing_id': listing['id'],
                                    'platform': platform,
                                    'status': 'posted',
                                    'message': f'Successfully posted to {platform_config["name"]}!',
                                    'platform_name': platform_config['name'],
                                    'listing_url': post_result.get('listing_url')
                                })

                                # Update status
                                current_statuses = listing.get('platform_statuses', '') or ''
                                status_list = [s for s in current_statuses.split(',') if s and s.strip()]
                                status_list = [s for s in status_list if not s.startswith(f"{platform}:")]
                                status_list.append(f"{platform}:posted")
                                db.update_listing(listing['id'], {'platform_statuses': ','.join(status_list)})
                            else:
                                results['api_results'].append({
                                    'listing_id': listing['id'],
                                    'platform': platform,
                                    'status': 'failed',
                                    'message': f'Failed to post to {platform_config["name"]}: {post_result.get("error")}',
                                    'platform_name': platform_config['name']
                                })
                                results['success'] = False

                except Exception as e:
                    for listing in listings:
                        results['api_results'].append({
                            'listing_id': listing['id'],
                            'platform': platform,
                            'status': 'error',
                            'message': f'Error posting to {platform_config["name"]}: {str(e)}',
                            'platform_name': platform_config['name']
                        })
                    results['success'] = False

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


def generate_generic_csv(listings, platform_name):
    """Generate a generic CSV for platforms without specific adapters"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_dir = Path('./data/csv_exports')
    csv_dir.mkdir(parents=True, exist_ok=True)
    filepath = csv_dir / f"{platform_name}_{timestamp}.csv"

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Title', 'Description', 'Price', 'Brand', 'Size',
            'Color', 'Condition', 'Photo 1', 'Photo 2', 'Photo 3'
        ])
        writer.writeheader()

        for listing in listings:
            photos = listing.photos[:3] if listing.photos else []
            writer.writerow({
                'Title': listing.title,
                'Description': listing.description,
                'Price': f"${listing.price.amount:.2f}",
                'Brand': listing.item_specifics.brand or '',
                'Size': listing.item_specifics.size or '',
                'Color': listing.item_specifics.color or '',
                'Condition': listing.condition.value,
                'Photo 1': photos[0].url if len(photos) > 0 else '',
                'Photo 2': photos[1].url if len(photos) > 1 else '',
                'Photo 3': photos[2].url if len(photos) > 2 else '',
            })

    return str(filepath)


@app.route('/api/download-csv/<filename>', methods=['GET'])
@login_required
def download_csv(filename):
    """Download generated CSV file"""
    try:
        # Sanitize filename
        safe_filename = secure_filename(filename)
        filepath = Path('./data/csv_exports') / safe_filename

        if not filepath.exists():
            return jsonify({'error': 'File not found'}), 404

        return send_file(
            filepath,
            as_attachment=True,
            download_name=safe_filename,
            mimetype='text/csv'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mark-sold', methods=['POST'])
@login_required
def mark_sold():
    """Mark listing as sold"""
    data = request.json

    try:
        listing_id = int(data['listing_id'])
        sold_price = float(data.get('sold_price')) if data.get('sold_price') else None
        quantity_sold = int(data.get('quantity_sold', 1))

        # Get listing
        listing = db.get_listing(listing_id)
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404

        # Verify ownership
        if listing.get('user_id') != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Update quantity
        current_quantity = listing.get('quantity', 1)
        remaining_quantity = max(0, current_quantity - quantity_sold)

        cursor = db.conn.cursor()
        if remaining_quantity == 0:
            # Mark as sold
            cursor.execute("""
                UPDATE listings
                SET status = 'sold',
                    quantity = 0,
                    sold_price = ?,
                    sold_date = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            """, (sold_price, listing_id, current_user.id))
        else:
            # Just reduce quantity
            cursor.execute("""
                UPDATE listings
                SET quantity = ?
                WHERE id = ? AND user_id = ?
            """, (remaining_quantity, listing_id, current_user.id))

        db.conn.commit()

        return jsonify({
            'success': True,
            'storage_location': listing.get('storage_location'),
            'remaining_quantity': remaining_quantity
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/get-draft/<int:listing_id>', methods=['GET'])
@login_required
def get_draft(listing_id):
    """Get a draft for editing"""
    try:
        listing = db.get_listing(listing_id)

        if not listing:
            return jsonify({'error': 'Listing not found'}), 404

        # Verify ownership
        if listing.get('user_id') != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Parse photos and attributes
        photos = []
        if listing.get('photos'):
            try:
                photos = json.loads(listing['photos']) if isinstance(listing['photos'], str) else listing['photos']
            except:
                photos = []

        attributes = {}
        if listing.get('attributes'):
            try:
                attributes = json.loads(listing['attributes']) if isinstance(listing['attributes'], str) else listing['attributes']
            except:
                attributes = {}

        # Return draft data
        return jsonify({
            'success': True,
            'listing': {
                'id': listing['id'],
                'listing_uuid': listing.get('listing_uuid'),
                'title': listing.get('title', ''),
                'description': listing.get('description', ''),
                'price': listing.get('price', 0),
                'cost': listing.get('cost'),
                'condition': listing.get('condition', 'good'),
                'item_type': listing.get('item_type', 'general'),
                'quantity': listing.get('quantity', 1),
                'storage_location': listing.get('storage_location', ''),
                'sku': listing.get('sku', ''),
                'upc': listing.get('upc', ''),
                'photos': photos,
                'brand': attributes.get('brand', ''),
                'size': attributes.get('size', ''),
                'color': attributes.get('color', ''),
                'shipping_cost': attributes.get('shipping_cost', 0)
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/data/draft_photos/<path:filepath>')
@login_required
def serve_draft_photo(filepath):
    """Serve draft photos"""
    try:
        photo_path = Path('data/draft_photos') / filepath

        # Security check - ensure path doesn't escape draft_photos directory
        if not photo_path.resolve().is_relative_to(Path('data/draft_photos').resolve()):
            return jsonify({'error': 'Invalid path'}), 403

        if not photo_path.exists():
            return jsonify({'error': 'Photo not found'}), 404

        return send_file(photo_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/post-draft/<int:listing_id>', methods=['POST'])
@login_required
def post_draft(listing_id):
    """Post a draft (make it active)"""
    try:
        listing = db.get_listing(listing_id)

        if not listing:
            return jsonify({'error': 'Listing not found'}), 404

        # Verify ownership
        if listing.get('user_id') != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Update status to active
        cursor = db.conn.cursor()
        cursor.execute("""
            UPDATE listings
            SET status = 'active',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (listing_id, current_user.id))
        db.conn.commit()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-draft/<int:listing_id>', methods=['DELETE'])
@login_required
def delete_draft(listing_id):
    """Delete a draft"""
    try:
        listing = db.get_listing(listing_id)

        if not listing:
            return jsonify({'error': 'Listing not found'}), 404

        # Verify ownership
        if listing.get('user_id') != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Delete photos directory
        import shutil
        if listing.get('listing_uuid'):
            draft_photos_dir = Path("data/draft_photos") / listing['listing_uuid']
            if draft_photos_dir.exists():
                shutil.rmtree(draft_photos_dir)

        db.delete_listing(listing_id)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/notification-email', methods=['POST'])
@login_required
def update_notification_email():
    """Update user's notification email"""
    try:
        data = request.json
        notification_email = data.get('notification_email')

        if not notification_email:
            return jsonify({'error': 'Notification email is required'}), 400

        db.update_notification_email(current_user.id, notification_email)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/marketplace-credentials', methods=['POST'])
@login_required
def save_marketplace_credentials():
    """Save marketplace credentials"""
    try:
        data = request.json
        platform = data.get('platform')
        username = data.get('username')
        password = data.get('password')

        if not platform:
            return jsonify({'error': 'Platform is required'}), 400

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        # Validate platform - All 27+ supported platforms
        valid_platforms = [
            'etsy', 'poshmark', 'depop', 'offerup', 'shopify', 'craigslist',
            'facebook', 'tiktok_shop', 'woocommerce', 'nextdoor', 'varagesale',
            'ruby_lane', 'ecrater', 'bonanza', 'kijiji',
            'personal_website', 'grailed', 'vinted', 'mercado_libre',
            'tradesy', 'vestiaire', 'rebag', 'thredup', 'poshmark_ca',
            'other'
        ]
        if platform.lower() not in valid_platforms:
            return jsonify({'error': 'Invalid platform'}), 400

        db.save_marketplace_credentials(current_user.id, platform.lower(), username, password)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/marketplace-credentials/<platform>', methods=['DELETE'])
@login_required
def delete_marketplace_credentials(platform):
    """Delete marketplace credentials"""
    try:
        db.delete_marketplace_credentials(current_user.id, platform.lower())
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/api-credentials', methods=['POST'])
@login_required
def save_api_credentials():
    """Save API credentials for automated platforms"""
    try:
        data = request.json
        platform = data.get('platform')
        credentials = data.get('credentials')

        if not platform:
            return jsonify({'error': 'Platform is required'}), 400

        if not credentials:
            return jsonify({'error': 'Credentials are required'}), 400

        # Validate platform
        valid_api_platforms = ['etsy', 'shopify', 'woocommerce', 'facebook']
        if platform.lower() not in valid_api_platforms:
            return jsonify({'error': 'Invalid API platform'}), 400

        # Store API credentials as JSON in database
        # For now, we'll use the marketplace_credentials table but with a special format
        # In production, you'd want a separate api_credentials table
        credentials_json = json.dumps(credentials)
        db.save_marketplace_credentials(current_user.id, f"api_{platform.lower()}", "api_token", credentials_json)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/api-credentials/<platform>', methods=['GET'])
@login_required
def get_api_credentials(platform):
    """Get API credentials for a platform"""
    try:
        # Get stored credentials
        creds = db.get_marketplace_credentials(current_user.id, f"api_{platform.lower()}")

        if creds and creds.get('password'):
            # Password field contains the JSON credentials
            credentials = json.loads(creds['password'])
            return jsonify({
                'success': True,
                'credentials': credentials,
                'configured': True
            })
        else:
            return jsonify({
                'success': True,
                'configured': False
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# BABY BIRD (Knowledge Distillation) API
# ============================================================================

@app.route('/api/baby-bird/status', methods=['GET'])
@login_required
def baby_bird_status():
    """Get training progress for knowledge distillation"""
    try:
        from src.ai.knowledge_distillation import get_baby_bird_status

        status = get_baby_bird_status(db)
        return jsonify(status)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/baby-bird/export', methods=['POST'])
@admin_required
def baby_bird_export():
    """Export training dataset (admin only)"""
    try:
        output_path = request.json.get('output_path', './data/training_dataset.jsonl')

        sample_count = db.export_training_dataset(output_path, format="jsonl")

        return jsonify({
            'success': True,
            'sample_count': sample_count,
            'output_path': output_path,
            'message': f'Exported {sample_count} training samples. Ready to train the baby bird!'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# RUN SERVER

# ============================================================================
# CARD COLLECTION API ENDPOINTS
# ============================================================================

@app.route('/cards')
@login_required  
def cards_collection():
    """Card collection management page"""
    return render_template('cards.html')


@app.route('/api/analyze-card', methods=['POST'])
@login_required
def api_analyze_card():
    """
    Analyze uploaded photos to detect and classify cards.
    
    Returns card-specific details for TCG and sports cards.
    """
    try:
        from src.ai.gemini_classifier import analyze_card
        from src.schema.unified_listing import Photo
        
        data = request.get_json()
        photo_paths = data.get('photos', [])
        
        if not photo_paths:
            return jsonify({'error': 'No photos provided'}), 400
        
        # Convert paths to Photo objects
        photos = [Photo(local_path=path) for path in photo_paths]
        
        # Analyze with Gemini
        result = analyze_card(photos)
        
        if result.get('error'):
            return jsonify(result), 500
        
        return jsonify({
            'success': True,
            'card_data': result
        })
        
    except Exception as e:
        print(f"Card analysis error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards/add', methods=['POST'])
@login_required
def api_add_card():
    """
    Add a card to user's collection.
    
    Accepts either:
    - AI analysis result
    - Manual card data
    """
    try:
        from src.cards import add_card_to_collection, create_card_from_ai_analysis
        
        data = request.get_json()
        
        # Check if this is from AI analysis
        if data.get('ai_result'):
            ai_result = data['ai_result']
            photos = data.get('photos', [])
            storage_location = data.get('storage_location')
            
            # Add card from AI result
            card_id = add_card_to_collection(
                ai_result,
                current_user.id,
                photos=photos,
                storage_location=storage_location
            )
            
            if not card_id:
                return jsonify({'error': 'Failed to create card - not a valid card'}), 400
            
            return jsonify({
                'success': True,
                'card_id': card_id,
                'message': 'Card added to collection'
            })
        
        # Manual card entry
        else:
            from src.cards import CardCollectionManager, UnifiedCard
            
            manager = CardCollectionManager()
            
            # Create UnifiedCard from manual data
            card = UnifiedCard(
                card_type=data.get('card_type', 'unknown'),
                title=data.get('title', 'Unknown Card'),
                user_id=current_user.id,
                card_number=data.get('card_number'),
                quantity=data.get('quantity', 1),
                organization_mode=data.get('organization_mode', 'by_set'),
                
                # TCG fields
                game_name=data.get('game_name'),
                set_name=data.get('set_name'),
                set_code=data.get('set_code'),
                rarity=data.get('rarity'),
                
                # Sports fields
                sport=data.get('sport'),
                year=data.get('year'),
                brand=data.get('brand'),
                series=data.get('series'),
                player_name=data.get('player_name'),
                is_rookie_card=data.get('is_rookie_card', False),
                
                # Grading
                grading_company=data.get('grading_company'),
                grading_score=data.get('grading_score'),
                
                # Value & location
                estimated_value=data.get('estimated_value'),
                storage_location=data.get('storage_location'),
                photos=data.get('photos', []),
                notes=data.get('notes'),
            )
            
            card_id = manager.add_card(card)
            
            return jsonify({
                'success': True,
                'card_id': card_id,
                'message': 'Card added to collection'
            })
        
    except Exception as e:
        print(f"Add card error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards/list', methods=['GET'])
@login_required
def api_list_cards():
    """
    Get user's card collection with optional filters.
    
    Query params:
    - card_type: Filter by card type
    - organization_mode: Filter by organization mode
    - limit: Max cards to return
    - offset: Pagination offset
    """
    try:
        from src.cards import CardCollectionManager
        
        manager = CardCollectionManager()
        
        card_type = request.args.get('card_type')
        organization_mode = request.args.get('organization_mode')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        cards = manager.get_user_cards(
            current_user.id,
            card_type=card_type,
            organization_mode=organization_mode,
            limit=limit,
            offset=offset
        )
        
        # Convert to dicts
        cards_data = [card.to_dict() for card in cards]
        
        return jsonify({
            'success': True,
            'cards': cards_data,
            'count': len(cards_data)
        })
        
    except Exception as e:
        print(f"List cards error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards/organized', methods=['GET'])
@login_required
def api_get_organized_cards():
    """
    Get cards organized by category.
    
    Query params:
    - organization_mode: Required (by_set, by_year, etc.)
    - card_type: Optional filter
    
    Returns:
    - Dict mapping categories to lists of cards
    """
    try:
        from src.cards import CardCollectionManager
        
        manager = CardCollectionManager()
        
        organization_mode = request.args.get('organization_mode')
        card_type = request.args.get('card_type')
        
        if not organization_mode:
            return jsonify({'error': 'organization_mode is required'}), 400
        
        organized = manager.get_cards_by_organization(
            current_user.id,
            organization_mode,
            card_type=card_type
        )
        
        # Convert UnifiedCards to dicts
        result = {}
        for category, cards in organized.items():
            result[category] = [card.to_dict() for card in cards]
        
        return jsonify({
            'success': True,
            'organized': result,
            'categories': list(result.keys())
        })
        
    except Exception as e:
        print(f"Get organized cards error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards/search', methods=['GET'])
@login_required
def api_search_cards():
    """
    Search cards by title, player name, set, etc.
    
    Query params:
    - q: Search query
    - card_type: Optional filter
    """
    try:
        from src.cards import CardCollectionManager
        
        manager = CardCollectionManager()
        
        query = request.args.get('q', '')
        card_type = request.args.get('card_type')
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        cards = manager.search_cards(current_user.id, query, card_type=card_type)
        
        cards_data = [card.to_dict() for card in cards]
        
        return jsonify({
            'success': True,
            'cards': cards_data,
            'count': len(cards_data)
        })
        
    except Exception as e:
        print(f"Search cards error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards/export', methods=['GET'])
@login_required
def api_export_cards():
    """
    Export cards to CSV.
    
    Query params:
    - card_type: Optional filter
    - organization_mode: Optional filter
    """
    try:
        from src.cards import CardCollectionManager
        from flask import make_response
        
        manager = CardCollectionManager()
        
        card_type = request.args.get('card_type')
        organization_mode = request.args.get('organization_mode')
        
        csv_data = manager.export_to_csv(
            current_user.id,
            card_type=card_type,
            organization_mode=organization_mode
        )
        
        if not csv_data:
            return jsonify({'error': 'No cards to export'}), 404
        
        # Create CSV response
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=card_collection.csv'
        
        return response
        
    except Exception as e:
        print(f"Export cards error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards/import', methods=['POST'])
@login_required
def api_import_cards():
    """
    Import cards from CSV.
    
    Expects:
    - file: CSV file upload
    - card_type: Optional default card type
    """
    try:
        from src.cards import CardCollectionManager
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read CSV content
        csv_content = file.read().decode('utf-8')
        
        card_type = request.form.get('card_type')
        
        manager = CardCollectionManager()
        result = manager.import_from_csv(current_user.id, csv_content, card_type=card_type)
        
        return jsonify({
            'success': True,
            'imported': result['imported'],
            'errors': result['errors']
        })
        
    except Exception as e:
        print(f"Import cards error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards/switch-organization', methods=['POST'])
@login_required
def api_switch_organization():
    """
    Switch organization mode for user's cards.
    
    This re-categorizes all cards based on the new mode.
    
    Body:
    - new_mode: Organization mode (by_set, by_year, etc.)
    - card_type: Optional filter
    """
    try:
        from src.cards import CardCollectionManager
        
        data = request.get_json()
        new_mode = data.get('new_mode')
        card_type = data.get('card_type')
        
        if not new_mode:
            return jsonify({'error': 'new_mode is required'}), 400
        
        valid_modes = [
            'by_set', 'by_year', 'by_sport', 'by_brand', 'by_game',
            'by_rarity', 'by_number', 'by_grading', 'by_value', 'by_binder', 'custom'
        ]
        
        if new_mode not in valid_modes:
            return jsonify({'error': f'Invalid organization mode. Valid: {", ".join(valid_modes)}'}), 400
        
        manager = CardCollectionManager()
        manager.switch_organization_mode(current_user.id, new_mode, card_type=card_type)
        
        return jsonify({
            'success': True,
            'message': f'Organization mode switched to {new_mode}'
        })
        
    except Exception as e:
        print(f"Switch organization error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards/stats', methods=['GET'])
@login_required
def api_card_stats():
    """Get collection statistics"""
    try:
        from src.cards import CardCollectionManager
        
        manager = CardCollectionManager()
        stats = manager.get_collection_stats(current_user.id)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        print(f"Card stats error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards/<int:card_id>', methods=['GET'])
@login_required
def api_get_card(card_id):
    """Get a specific card by ID"""
    try:
        from src.cards import CardCollectionManager
        
        manager = CardCollectionManager()
        card = manager.get_card(card_id)
        
        if not card:
            return jsonify({'error': 'Card not found'}), 404
        
        # Verify ownership
        if card.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify({
            'success': True,
            'card': card.to_dict()
        })
        
    except Exception as e:
        print(f"Get card error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards/<int:card_id>', methods=['PUT'])
@login_required
def api_update_card(card_id):
    """Update a card"""
    try:
        from src.cards import CardCollectionManager, UnifiedCard
        
        manager = CardCollectionManager()
        
        # Get existing card
        card = manager.get_card(card_id)
        if not card:
            return jsonify({'error': 'Card not found'}), 404
        
        # Verify ownership
        if card.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Update fields from request
        data = request.get_json()
        
        # Update allowed fields
        if 'title' in data:
            card.title = data['title']
        if 'quantity' in data:
            card.quantity = data['quantity']
        if 'storage_location' in data:
            card.storage_location = data['storage_location']
        if 'notes' in data:
            card.notes = data['notes']
        if 'estimated_value' in data:
            card.estimated_value = data['estimated_value']
        if 'grading_company' in data:
            card.grading_company = data['grading_company']
        if 'grading_score' in data:
            card.grading_score = data['grading_score']
        
        manager.update_card(card_id, card)
        
        return jsonify({
            'success': True,
            'message': 'Card updated'
        })
        
    except Exception as e:
        print(f"Update card error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards/<int:card_id>', methods=['DELETE'])
@login_required
def api_delete_card(card_id):
    """Delete a card"""
    try:
        from src.cards import CardCollectionManager
        
        manager = CardCollectionManager()
        
        # Get existing card
        card = manager.get_card(card_id)
        if not card:
            return jsonify({'error': 'Card not found'}), 404
        
        # Verify ownership
        if card.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        manager.delete_card(card_id)
        
        return jsonify({
            'success': True,
            'message': 'Card deleted'
        })
        
    except Exception as e:
        print(f"Delete card error: {str(e)}")
        return jsonify({'error': str(e)}), 500




# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',  # Accessible from other devices on network
        port=5000,
        debug=True
    )
