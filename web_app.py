#!/usr/bin/env python3
"""
AI Cross-Poster Web App - Main Entry Point
============================================
PostgreSQL-compatible web application for inventory management.

This file serves as the entry point that:
- Initializes Flask app and database
- Sets up Flask-Login authentication
- Registers all route blueprints
"""

import os
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_required, current_user
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

from src.database import get_db

# Load environment
load_dotenv()

# ============================================================================
# FLASK APP INITIALIZATION
# ============================================================================

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['UPLOAD_FOLDER'] = './data/uploads'

# Ensure upload folder exists
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

# Lazy database initialization - don't create at import time
db = None

def get_db_instance():
    """Get database instance, creating it only when first needed"""
    global db
    if db is None:
        db = get_db()
    return db

# Initialize notification manager (optional)
notification_manager = None
try:
    from src.notifications import NotificationManager
    notification_manager = NotificationManager.from_env()
except Exception:
    pass

# ============================================================================
# USER MODEL FOR FLASK-LOGIN
# ============================================================================

class User(UserMixin):
    """User model for Flask-Login - PostgreSQL compatible"""

    def __init__(self, user_id, username, email, is_admin=False, is_active=True, tier="FREE"):
        self.id = user_id
        self.username = username
        self.email = email
        self.is_admin = is_admin
        self._is_active = is_active
        self.tier = tier

    @property
    def is_active(self):
        """Override Flask-Login's is_active to use database value"""
        return self._is_active

    def can_access(self, feature: str) -> bool:
        """Check if user can access a feature based on tier"""
        from src.database import can_access_feature
        return can_access_feature(self.tier, feature)

    @staticmethod
    def get(user_id):
        """Get user by ID from PostgreSQL"""
        user_data = get_db_instance().get_user_by_id(user_id)
        if user_data:
            return User(
                user_data['id'],
                user_data['username'],
                user_data['email'],
                user_data.get('is_admin', False),
                user_data.get('is_active', True),
                user_data.get('tier', 'FREE')
            )
        return None

# ============================================================================
# FLASK-LOGIN SETUP
# ============================================================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    try:
        # Handle different user_id types (int, str, etc.)
        if isinstance(user_id, str):
            # Try to convert to int if it's a numeric string
            try:
                user_id = int(user_id)
            except ValueError:
                return None
        elif not isinstance(user_id, int):
            # If it's already an int or other type, try to use it directly
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return None
        
        return User.get(user_id)
    except Exception as e:
        print(f"Error loading user: {e}")
        return None

# ============================================================================
# ADMIN DECORATOR
# ============================================================================

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

# Export for use in blueprints
app.admin_required = admin_required

# ============================================================================
# IMPORT AND REGISTER BLUEPRINTS
# ============================================================================

# Import blueprints
from routes_auth import auth_bp, init_routes as init_auth
from routes_admin import admin_bp, init_routes as init_admin
from routes_cards import cards_bp, init_routes as init_cards
from routes_main import main_bp, init_routes as init_main

# Initialize blueprints with database instance and User class
# Database is created lazily on first blueprint init
init_auth(get_db_instance(), User)
init_admin(get_db_instance())
init_cards(get_db_instance())
init_main(get_db_instance())

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(cards_bp)
app.register_blueprint(main_bp)

# ============================================================================
# MAIN ROUTES (not in blueprints)
# ============================================================================

@app.route('/')
def index():
    """Landing page / dashboard"""
    if current_user.is_authenticated:
        return render_template('index.html')
    else:
        return render_template('index.html')

@app.route('/create')
def create_listing():
    """Create new listing page"""
    return render_template('create.html')

@app.route('/drafts')
@login_required
def drafts():
    """Drafts page"""
    # Fetch all drafts for current user
    drafts_list = get_db_instance().get_drafts(user_id=current_user.id, limit=100)
    return render_template('drafts.html', drafts=drafts_list)

@app.route('/listings')
@login_required
def listings():
    """Listings page"""
    db_instance = get_db_instance()
    cursor = db_instance._get_cursor()
    # Cast user_id to handle UUID/INTEGER type mismatch
    cursor.execute("""
        SELECT * FROM listings
        WHERE user_id::text = %s::text AND status != 'draft'
        ORDER BY created_at DESC
    """, (str(current_user.id),))
    user_listings = [dict(row) for row in cursor.fetchall()]
    return render_template('listings.html', listings=user_listings)

@app.route('/notifications')
@login_required
def notifications():
    """Notifications page"""
    return render_template('notifications.html')

@app.route('/storage')
@login_required
def storage():
    """Storage overview"""
    storage_map = get_db_instance().get_storage_map(current_user.id)
    return render_template('storage.html', storage_map=storage_map)

@app.route('/storage/clothing')
@login_required
def storage_clothing():
    """Clothing storage"""
    return render_template('storage_clothing.html')

@app.route('/storage/cards')
@login_required
def storage_cards():
    """Card storage"""
    return redirect(url_for('cards.cards_collection'))

@app.route('/storage/map')
@login_required
def storage_map():
    """Storage map"""
    return render_template('storage_map.html')

@app.route('/settings')
@login_required
def settings():
    """User settings"""
    return render_template('settings.html')

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
