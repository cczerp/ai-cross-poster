# routes_auth.py
# Authentication, login, logout, register, and session utilities.
# NO BLUEPRINTS — uses app directly.

from flask import request, jsonify, redirect, render_template, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db, User


# =============================================================================
# LOGIN PAGE
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'GET':
        return render_template('login.html')

    # POST — authenticate user
    data = request.form
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        flash("Username and password required.", "error")
        return render_template('login.html')

    user = db.get_user_by_username(username)

    if not user:
        flash("User not found.", "error")
        return render_template('login.html')

    if not check_password_hash(user.password_hash, password):
        flash("Incorrect password.", "error")
        return render_template('login.html')

    login_user(user)
    db.log_activity(
        action="login",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent")
    )

    return redirect(url_for('index'))


# =============================================================================
# REGISTER PAGE
# =============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user."""
    if request.method == 'GET':
        return render_template('register.html')

    data = request.form
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password or not email:
        flash("All fields are required", "error")
        return render_template('register.html')

    # Check if user already exists
    if db.get_user_by_username(username):
        flash("Username already taken", "error")
        return render_template('register.html')

    if db.get_user_by_email(email):
        flash("Email already registered", "error")
        return render_template('register.html')

    # Create user
    password_hash = generate_password_hash(password)
    user_id = db.create_user(username, email, password_hash)

    user = db.get_user_by_id(user_id)
    login_user(user)

    db.log_activity(
        action="register",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent")
    )

    return redirect(url_for('index'))


# =============================================================================
# LOGOUT
# =============================================================================

@app.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    db.log_activity(
        action="logout",
        user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent")
    )

    logout_user()
    return redirect(url_for('login'))


# =============================================================================
# API — CHECK SESSION
# =============================================================================

@app.route('/api/auth/session')
def api_check_session():
    """Check whether user is currently logged in."""
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "is_admin": current_user.is_admin
            }
        })
    else:
        return jsonify({"authenticated": False})


# =============================================================================
# API LOGIN (JSON)
# =============================================================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Login through fetch/XHR with JSON."""
    data = request.json or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    user = db.get_user_by_username(username)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid password"}), 401

    login_user(user)

    db.log_activity(
        action="api_login",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent")
    )

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        }
    })


# =============================================================================
# API LOGOUT
# =============================================================================

@app.route('/api/auth/logout')
@login_required
def api_logout():
    """Logout via fetch request."""
    logout_user()
    return jsonify({"success": True})


# =============================================================================
# FORGOT PASSWORD (Optional — included if in your original code)
# =============================================================================

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Show password reset form OR handle reset requests."""
    if request.method == 'GET':
        return render_template('forgot_password.html')

    email = request.form.get("email")
    if not email:
        flash("Email is required", "error")
        return render_template('forgot_password.html')

    user = db.get_user_by_email(email)
    if not user:
        flash("No account with that email.", "error")
        return render_template('forgot_password.html')

    # In full version, generate token + email instructions here
    db.log_activity(
        action="password_reset_requested",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent")
    )

    flash("Password reset instructions sent to your email.", "info")
    return render_template('forgot_password.html')
