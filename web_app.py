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
        {'id': 'mercari', 'name': 'Mercari', 'icon': 'fas fa-box', 'color': 'text-warning'},
        {'id': 'ebay', 'name': 'eBay', 'icon': 'fab fa-ebay', 'color': 'text-primary'},
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
    Allows users to select specific items and platforms for posting.
    """
    data = request.json

    try:
        listing_ids = data.get('listing_ids', [])
        platforms = data.get('platforms', [])

        if not listing_ids:
            return jsonify({'error': 'No listings selected'}), 400

        if not platforms:
            return jsonify({'error': 'No platforms selected'}), 400

        results = []
        success_count = 0
        fail_count = 0

        for listing_id in listing_ids:
            # Get listing
            listing = db.get_listing(listing_id)

            if not listing:
                results.append({
                    'listing_id': listing_id,
                    'success': False,
                    'error': 'Listing not found'
                })
                fail_count += 1
                continue

            # Verify ownership
            if listing.get('user_id') != current_user.id:
                results.append({
                    'listing_id': listing_id,
                    'success': False,
                    'error': 'Unauthorized'
                })
                fail_count += 1
                continue

            # Post to each selected platform
            platform_results = {}
            listing_success = True

            for platform in platforms:
                try:
                    # Here you would integrate with each platform's API
                    # For now, we'll just update the database to track the posting

                    # Update platform_statuses field
                    current_statuses = listing.get('platform_statuses', '') or ''
                    status_list = [s for s in current_statuses.split(',') if s]

                    # Remove existing status for this platform
                    status_list = [s for s in status_list if not s.startswith(f"{platform}:")]

                    # Add new status
                    status_list.append(f"{platform}:pending")

                    new_statuses = ','.join(status_list)

                    # Update listing
                    db.update_listing(listing_id, {
                        'platform_statuses': new_statuses
                    })

                    platform_results[platform] = 'success'

                except Exception as e:
                    platform_results[platform] = f'failed: {str(e)}'
                    listing_success = False

            if listing_success:
                success_count += 1
            else:
                fail_count += 1

            results.append({
                'listing_id': listing_id,
                'title': listing.get('title'),
                'success': listing_success,
                'platforms': platform_results
            })

        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'total': len(listing_ids),
                'success': success_count,
                'failed': fail_count
            }
        })

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
            'ruby_lane', 'ecrater', 'bonanza', 'kijiji', 'mercari', 'ebay',
            'personal_website', 'grailed', 'vinted', 'mercado_libre',
            'tradesy', 'vestiaire', 'rebag', 'thredup', 'poshmark_ca',
            'ebay_uk', 'other'
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

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',  # Accessible from other devices on network
        port=5000,
        debug=True
    )
