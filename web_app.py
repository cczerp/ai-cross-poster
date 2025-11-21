#!/usr/bin/env python3
"""
AI Cross-Poster Web App
========================
Mobile-friendly web interface for inventory management and cross-platform listing.

Run with:
    python web_app.py
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
    cursor = db._get_cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    result = cursor.fetchone()
    user_count = result['count'] if isinstance(result, dict) else result[0]

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
            VALUES (%s, %s, %s, %s, %s, %s)
        """, ('admin', 'admin@resellgenius.local', password_hash, True, True, True))
        db.conn.commit()

create_default_admin()

# Initialize notification manager (optional)
notification_manager = None
try:
    from src.notifications import NotificationManager
    notification_manager = NotificationManager.from_env()
except Exception:
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
        self._is_active = is_active

    @property
    def is_active(self):
        return self._is_active

    @staticmethod
    def get(user_id):
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
    return User.get(int(user_id))


# ============================================================================
# ADMIN DECORATOR
# ============================================================================

from functools import wraps

def admin_required(f):
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
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')

        user_data = db.get_user_by_username(username)

        if user_data and check_password_hash(user_data['password_hash'], password):
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
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

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
            password_hash = generate_password_hash(password)
            user_id = db.create_user(username, email, password_hash)

            db.log_activity(
                action='register',
                user_id=user_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )

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
    if request.method == 'POST':
        email = request.form.get('email')
        user = db.get_user_by_email(email)
        
        if user:
            import secrets
            token = secrets.token_urlsafe(32)
            db.set_reset_token(user['id'], token, expiry_hours=24)
            reset_link = url_for('reset_password', token=token, _external=True)
            print(f"\n{'='*60}")
            print(f"PASSWORD RESET LINK FOR {email}:")
            print(f"{reset_link}")
            print(f"{'='*60}\n")

        flash('If that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('login'))

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
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

        password_hash = generate_password_hash(password)
        db.update_password(user['id'], password_hash)

        flash('Password reset successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


# ============================================================================
# MAIN UI ROUTES
# ============================================================================

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('index.html', is_guest=True)
    return render_template('index.html', is_guest=False)


@app.route('/create')
def create_listing():
    is_guest = not current_user.is_authenticated
    draft_id = request.args.get('draft_id', type=int)
    return render_template('create.html', is_guest=is_guest, draft_id=draft_id)


@app.route('/drafts')
@login_required
def drafts():
    drafts_list = db.get_drafts(limit=100, user_id=current_user.id)
    return render_template('drafts.html', drafts=drafts_list)


@app.route('/listings')
@login_required
def listings():
    cursor = db._get_cursor()
    cursor.execute("""
        SELECT l.*, STRING_AGG(pl.platform || ':' || pl.status, ',') as platform_statuses
        FROM listings l
        LEFT JOIN platform_listings pl ON l.id = pl.listing_id
        WHERE l.status != 'draft' AND l.user_id = %s
        GROUP BY l.id
        ORDER BY l.created_at DESC
        LIMIT 50
    """, (current_user.id,))
    listings_list = [dict(row) for row in cursor.fetchall()]
    return render_template('listings.html', listings=listings_list)


@app.route('/notifications')
@login_required
def notifications():
    if notification_manager:
        try:
            notifs = notification_manager.get_recent_notifications(limit=50)
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


@app.route('/storage')
@login_required
def storage():
    storage_map = db.get_storage_map(current_user.id)
    return render_template('storage.html', storage_map=storage_map)


@app.route('/storage/clothing')
@login_required
def storage_clothing():
    bins = db.get_storage_bins(current_user.id, bin_type='clothing')
    return render_template('storage_clothing.html', bins=bins)


@app.route('/storage/cards')
@login_required
def storage_cards():
    bins = db.get_storage_bins(current_user.id, bin_type='cards')
    if not bins:
        bin_id = db.create_storage_bin(current_user.id, 'A', 'cards', 'Default card bin')
        bins = db.get_storage_bins(current_user.id, bin_type='cards')
    return render_template('storage_cards.html', bins=bins)


@app.route('/storage/map')
@login_required
def storage_map():
    storage_map = db.get_storage_map(current_user.id)
    return render_template('storage_map.html', storage_map=storage_map)


@app.route('/settings')
@login_required
def settings():
    user = db.get_user_by_id(current_user.id)
    marketplace_creds = db.get_all_marketplace_credentials(current_user.id)
    creds_dict = {cred['platform']: cred for cred in marketplace_creds}

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


@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = db.get_system_stats()
    users = db.get_all_users(include_inactive=True)
    recent_activity = db.get_activity_logs(limit=20)
    return render_template('admin/dashboard.html', stats=stats, users=users, recent_activity=recent_activity)


@app.route('/admin/users')
@admin_required
def admin_users():
    users = db.get_all_users(include_inactive=True)
    return render_template('admin/users.html', users=users)


@app.route('/admin/activity')
@admin_required
def admin_activity():
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
    user = db.get_user_by_id(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin_users'))

    cursor = db._get_cursor()
    cursor.execute("SELECT * FROM listings WHERE user_id = %s ORDER BY created_at DESC LIMIT 50", (user_id,))
    listings = [dict(row) for row in cursor.fetchall()]
    activity = db.get_activity_logs(user_id=user_id, limit=50)

    return render_template('admin/user_detail.html', user=user, listings=listings, activity=activity)


@app.route('/cards')
@login_required  
def cards_collection():
    return render_template('cards.html')


# Note: API routes are split across routes_main.py, routes_cards.py, etc.
# They should be registered as blueprints. If you get "blueprint not registered" errors,
# uncomment and add:
# from routes_main import main as main_bp
# app.register_blueprint(main_bp)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
