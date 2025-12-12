#!/usr/bin/env python3
"""
Minimal Login Test App
======================
Stripped down version to debug login issues.
Only includes authentication functionality.
"""

import os
import sys
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_required, current_user
from flask_session import Session
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

print("🚀 Starting minimal login test app...", flush=True)

from src.database import get_db

# Load environment
load_dotenv()
print("✅ Environment loaded", flush=True)

# ============================================================================
# FLASK APP INITIALIZATION
# ============================================================================

app = Flask(__name__)

# CRITICAL: Validate FLASK_SECRET_KEY is set
flask_secret = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
if not flask_secret or flask_secret == 'dev-secret-key-change-in-production':
    print("=" * 80, flush=True)
    print("⚠️  WARNING: FLASK_SECRET_KEY not set or using default value!", flush=True)
    print("⚠️  This will cause session loss in production with multiple workers!", flush=True)
    print("⚠️  Set FLASK_SECRET_KEY environment variable immediately!", flush=True)
    print("=" * 80, flush=True)

app.secret_key = flask_secret
print(f"✅ Flask secret key configured (length: {len(flask_secret)})", flush=True)

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

# Session configuration for Flask-Login and OAuth
# Detect production environment by checking for RENDER_EXTERNAL_URL or explicit FLASK_ENV
is_production = os.getenv('FLASK_ENV') == 'production' or bool(os.getenv('RENDER_EXTERNAL_URL'))

app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS attacks
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if is_production else 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True if is_production else False
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
app.config['REMEMBER_COOKIE_DURATION'] = 86400  # 24 hours

print(f"🔧 Session configuration:", flush=True)
print(f"   - Cookie SameSite: {app.config['SESSION_COOKIE_SAMESITE']}", flush=True)
print(f"   - Cookie Secure: {app.config['SESSION_COOKIE_SECURE']}", flush=True)
print(f"   - Cookie HTTPOnly: {app.config['SESSION_COOKIE_HTTPONLY']}", flush=True)

# ============================================================================
# FLASK-SESSION CONFIGURATION (Server-side session storage)
# ============================================================================
# CRITICAL: Use Redis for production to persist sessions across workers/restarts
# This fixes the "bad_oauth_state" error on Render's ephemeral filesystem

redis_url = os.getenv('REDIS_URL')

if redis_url:
    # Production: Use Redis for session storage (works with ephemeral filesystems)
    from redis import Redis

    print(f"🔧 Configuring Redis session storage...", flush=True)
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = Redis.from_url(redis_url)
    app.config['SESSION_PERMANENT'] = False  # Session expires when browser closes
    app.config['SESSION_USE_SIGNER'] = True  # Sign session cookies for security

    # Initialize Flask-Session
    Session(app)

    print(f"✅ Flask-Session initialized with Redis:", flush=True)
    print(f"   - Type: redis", flush=True)
    print(f"   - URL: {redis_url[:20]}...", flush=True)
    print(f"   - Permanent: False", flush=True)
    print(f"   - Use Signer: True", flush=True)
else:
    # Development: Fall back to filesystem for local development
    print(f"⚠️  REDIS_URL not set - using filesystem sessions (NOT for production!)", flush=True)

    session_dir = Path('./data/flask_session')
    session_dir.mkdir(parents=True, exist_ok=True)

    app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions on disk
    app.config['SESSION_FILE_DIR'] = str(session_dir)
    app.config['SESSION_PERMANENT'] = False  # Session expires when browser closes
    app.config['SESSION_USE_SIGNER'] = True  # Sign session cookies for security
    app.config['SESSION_FILE_THRESHOLD'] = 500  # Max number of session files

    # Initialize Flask-Session
    Session(app)

    print(f"✅ Flask-Session initialized with filesystem:", flush=True)
    print(f"   - Type: filesystem", flush=True)
    print(f"   - Directory: {session_dir.absolute()}", flush=True)

# Ensure oauth_state folder exists
Path('./data/oauth_state').mkdir(parents=True, exist_ok=True)

# Lazy database initialization
db = None

def get_db_instance():
    """Get database instance, creating it only when first needed"""
    global db
    if db is None:
        db = get_db()
    return db

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
    """Load user for Flask-Login - user_id is UUID string"""
    try:
        user_id_str = str(user_id) if user_id else None
        if not user_id_str:
            print(f"[USER_LOADER] No user_id provided")
            return None

        print(f"[USER_LOADER] Loading user with ID: {user_id_str}")
        user = User.get(user_id_str)

        if user:
            print(f"[USER_LOADER] Successfully loaded user: {user.username}")
        else:
            print(f"[USER_LOADER] User not found for ID: {user_id_str}")

        return user
    except (ValueError, TypeError) as e:
        print(f"[USER_LOADER ERROR] Invalid user_id: {e}")
        return None
    except Exception as e:
        print(f"[USER_LOADER ERROR] Error loading user: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# IMPORT AND REGISTER BLUEPRINTS
# ============================================================================

# Import auth blueprint only
from routes_auth import auth_bp, init_routes as init_auth

# Initialize auth blueprint with database instance and User class
try:
    print("🔌 Initializing database connection...", flush=True)
    db_instance = get_db_instance()
    print("✅ Database connected successfully", flush=True)

    print("📝 Initializing auth blueprint...", flush=True)
    init_auth(db_instance, User)
    print("✅ Auth blueprint initialized", flush=True)
except Exception as e:
    print(f"❌ FATAL ERROR during initialization: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Register auth blueprint
app.register_blueprint(auth_bp)

print("✅ Flask app initialized and ready to serve requests", flush=True)

# ============================================================================
# MAIN ROUTES (minimal)
# ============================================================================

@app.route('/debug-config')
def debug_config():
    """Debug endpoint to check Flask configuration"""
    import os
    config_info = {
        'FLASK_ENV': os.getenv('FLASK_ENV', 'NOT SET'),
        'is_production_check': os.getenv('FLASK_ENV') == 'production',
        'SESSION_COOKIE_SAMESITE': app.config.get('SESSION_COOKIE_SAMESITE'),
        'SESSION_COOKIE_SECURE': app.config.get('SESSION_COOKIE_SECURE'),
        'SESSION_COOKIE_HTTPONLY': app.config.get('SESSION_COOKIE_HTTPONLY'),
        'SESSION_TYPE': app.config.get('SESSION_TYPE'),
        'SECRET_KEY_LENGTH': len(app.secret_key) if app.secret_key else 0,
        'DATABASE_URL_SET': bool(os.getenv('DATABASE_URL')),
        'SUPABASE_URL_SET': bool(os.getenv('SUPABASE_URL')),
        'SUPABASE_ANON_KEY_SET': bool(os.getenv('SUPABASE_ANON_KEY')),
    }

    return jsonify(config_info)

@app.route('/')
def index():
    """Landing page / dashboard"""
    if current_user.is_authenticated:
        return render_template('index_minimal.html', user=current_user)
    else:
        return render_template('index_minimal.html', user=None)

@app.route('/protected')
@login_required
def protected():
    """Protected route to test login"""
    return f"<h1>Protected Page</h1><p>Hello {current_user.username}! You are logged in.</p><p><a href='/logout'>Logout</a></p>"

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
