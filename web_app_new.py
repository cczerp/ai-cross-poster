#!/usr/bin/env python3
"""
AI Cross-Poster Web App - Main Entry Point
============================================
PostgreSQL-compatible web application for inventory management.

This file contains:
- App initialization and configuration
- Authentication routes (login, register, logout, password reset)
- User model and Flask-Login setup
"""

import os
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
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

# Initialize database (PostgreSQL)
db = get_db()

# Create default admin account if no users exist
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

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
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
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login - PostgreSQL compatible"""
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
    """User registration - PostgreSQL compatible"""
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
    """User logout"""
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
            import secrets
            token = secrets.token_urlsafe(32)
            db.set_reset_token(user['id'], token, expiry_hours=24)

            reset_link = url_for('reset_password', token=token, _external=True)
            print(f"\n{'='*60}")
            print(f"PASSWORD RESET LINK FOR {email}:")
            print(f"{reset_link}")
            print(f"{'='*60}\n")

            flash('If that email exists, a password reset link has been sent.', 'info')
        else:
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

        password_hash = generate_password_hash(password)
        db.update_password(user['id'], password_hash)

        flash('Password reset successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


# ============================================================================
# MAIN PAGE ROUTE
# ============================================================================

@app.route('/')
def index():
    """Home page - accessible to guests"""
    if not current_user.is_authenticated:
        return render_template('index.html', is_guest=True)
    return render_template('index.html', is_guest=False)


# ============================================================================
# REGISTER BLUEPRINTS
# ============================================================================

from routes.listing_routes import listing_bp
from routes.admin_routes import admin_bp

app.register_blueprint(listing_bp)
app.register_blueprint(admin_bp)

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
