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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['UPLOAD_FOLDER'] = './data/uploads'

# Ensure upload folder exists
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

# Initialize database (PostgreSQL)
db = get_db()

# ============================================================================
# CREATE DEFAULT ADMIN
# ============================================================================

def create_default_admin():
    """Create default admin account (admin/admin) if no users exist"""
    cursor = db._get_cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users")
    result = cursor.fetchone()
    # Handle PostgreSQL RealDictCursor
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

# ============================================================================
# USER MODEL FOR FLASK-LOGIN
# ============================================================================

class User(UserMixin):
    """User model for Flask-Login - PostgreSQL compatible"""

    def __init__(self, user_id, username, email, is_admin=False, is_active=True):
        self.id = user_id
        self.username = username
        self.email = email
        self.is_admin = is_admin
        self._is_active = is_active

    @property
    def is_active(self):
        """Override Flask-Login's is_active to use database value"""
        return self._is_active

    @staticmethod
    def get(user_id):
        """Get user by ID from PostgreSQL"""
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
    return User.get(int(user_id))

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

# Initialize blueprints with database and User class
init_auth(db, User)
init_admin(db)
init_cards(db)
init_main(db)

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
    return render_template('drafts.html')

@app.route('/listings')
@login_required
def listings():
    """Listings page"""
    cursor = db._get_cursor()
    cursor.execute("""
        SELECT * FROM listings
        WHERE user_id = %s AND status != 'draft'
        ORDER BY created_at DESC
    """, (current_user.id,))
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
    return render_template('storage/index.html')

@app.route('/storage/clothing')
@login_required
def storage_clothing():
    """Clothing storage"""
    return render_template('storage/clothing.html')

@app.route('/storage/cards')
@login_required
def storage_cards():
    """Card storage"""
    return redirect(url_for('cards.cards_collection'))

@app.route('/storage/map')
@login_required
def storage_map():
    """Storage map"""
    return render_template('storage/map.html')

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
