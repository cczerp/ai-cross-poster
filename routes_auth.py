"""
routes_auth.py
Authentication routes: login, logout, register, password reset, Google OAuth
"""
import os
from flask import Blueprint, request, jsonify, redirect, render_template, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# db and User will be set by init_routes() in web_app.py
db = None
User = None

def init_routes(database, user_class):
    """Initialize routes with database and User class"""
    global db, User
    db = database
    User = user_class


# =============================================================================
# LOGIN PAGE
# =============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'GET':
        return render_template('login.html')

    try:
        # POST — authenticate user
        data = request.form
        username = data.get('username')
        password = data.get('password')

        print(f"[LOGIN] Attempting login for username: {username}", flush=True)
        import time
        start_time = time.time()

        if not username or not password:
            flash("Username and password required.", "error")
            return render_template('login.html')

        # Check database connection first
        if db is None:
            print("[LOGIN ERROR] Database not initialized!")
            flash("Database connection error. Please try again.", "error")
            return render_template('login.html')

        user_data = db.get_user_by_username(username)

        if user_data is None:
            print(f"[LOGIN] User not found or database error for username: {username}")
            flash("User not found.", "error")
            return render_template('login.html')

        print(f"[LOGIN] User found: {username}, has password_hash: {bool(user_data.get('password_hash'))}")

        # Check if user has a password (OAuth users may not have password_hash)
        password_hash = user_data.get('password_hash')
        if not password_hash:
            flash("This account uses Google sign-in. Please use the 'Sign in with Google' button.", "error")
            return render_template('login.html')

        if not check_password_hash(password_hash, password):
            print(f"[LOGIN] Password verification failed for username: {username}")
            flash("Incorrect password.", "error")
            return render_template('login.html')

        print(f"[LOGIN] Password verified for username: {username}")

        # Create User object for Flask-Login - ensure id is UUID string
        user_id_str = str(user_data['id']) if user_data.get('id') else None
        if not user_id_str:
            print(f"[LOGIN ERROR] Invalid user ID for username: {username}")
            flash("Invalid user data. Please try again.", "error")
            return render_template('login.html')

        user = User(
            user_id_str,
            user_data['username'],
            user_data['email'],
            user_data.get('is_admin', False),
            user_data.get('is_active', True),
            user_data.get('tier', 'FREE')
        )

        print(f"[LOGIN] Logging in user: {username} (ID: {user_id_str})")
        login_user(user)
        print(f"[LOGIN] Flask-Login completed for username: {username}")

        # Log activity (with error handling)
        try:
            db.log_activity(
                action="login",
                user_id=user_id_str,
                resource_type="user",
                resource_id=None,  # Don't use user.id as resource_id since it's UUID
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent")
            )
            print(f"[LOGIN] Activity logged for username: {username}")
        except Exception as e:
            print(f"[LOGIN WARNING] Failed to log activity: {e}")

        elapsed = time.time() - start_time
        print(f"[LOGIN] ✅ Login successful for {username} (took {elapsed:.2f}s)", flush=True)
        return redirect(url_for('index'))
    
    except Exception as e:
        print(f"Login error: {e}")
        import traceback
        traceback.print_exc()
        flash("An error occurred during login. Please try again.", "error")
        return render_template('login.html')


# =============================================================================
# REGISTER PAGE
# =============================================================================

@auth_bp.route('/register', methods=['GET', 'POST'])
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

    user_data = db.get_user_by_id(user_id)
    if not user_data:
        flash("Failed to retrieve user data. Please try again.", "error")
        return render_template('register.html')
    
    # Ensure id is UUID string
    user_id_str = str(user_data['id']) if user_data.get('id') else None
    if not user_id_str:
        flash("Invalid user data. Please try again.", "error")
        return render_template('register.html')
    
    user = User(
        user_id_str,
        user_data['username'],
        user_data['email'],
        user_data.get('is_admin', False),
        user_data.get('is_active', True),
        user_data.get('tier', 'FREE')
    )
    login_user(user)

    db.log_activity(
        action="register",
        user_id=user_id_str,
        resource_type="user",
        resource_id=None,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent")
    )

    return redirect(url_for('index'))


# =============================================================================
# LOGOUT
# =============================================================================

@auth_bp.route('/logout')
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
    return redirect(url_for('auth.login'))


# =============================================================================
# API — CHECK SESSION
# =============================================================================

@auth_bp.route('/api/auth/session')
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

@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    """Login through fetch/XHR with JSON."""
    data = request.json or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    user_data = db.get_user_by_username(username)
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    # Check if user has a password (OAuth users may not have password_hash)
    password_hash = user_data.get('password_hash')
    if not password_hash:
        return jsonify({"error": "This account uses Google sign-in. Please use the 'Sign in with Google' button."}), 400

    if not check_password_hash(password_hash, password):
        return jsonify({"error": "Invalid password"}), 401

    # Ensure id is UUID string
    user_id_str = str(user_data['id']) if user_data.get('id') else None
    if not user_id_str:
        return jsonify({"error": "Invalid user data"}), 500
    
    user = User(
        user_id_str,
        user_data['username'],
        user_data['email'],
        user_data.get('is_admin', False),
        user_data.get('is_active', True),
        user_data.get('tier', 'FREE')
    )
    login_user(user)

    db.log_activity(
        action="api_login",
        user_id=user_id_str,
        resource_type="user",
        resource_id=None,
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

@auth_bp.route('/api/auth/logout')
@login_required
def api_logout():
    """Logout via fetch request."""
    logout_user()
    return jsonify({"success": True})


# =============================================================================
# FORGOT PASSWORD
# =============================================================================

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Show password reset form OR handle reset requests."""
    if request.method == 'GET':
        return render_template('forgot_password.html')

    email = request.form.get("email")
    if not email:
        flash("Email is required", "error")
        return render_template('forgot_password.html')

    user_data = db.get_user_by_email(email)
    if not user_data:
        flash("No account with that email.", "error")
        return render_template('forgot_password.html')

    # In full version, generate token + email instructions here
    db.log_activity(
        action="password_reset_requested",
        user_id=user_data['id'],
        resource_type="user",
        resource_id=user_data['id'],
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent")
    )

    flash("Password reset instructions sent to your email.", "info")
    return render_template('forgot_password.html')


# =============================================================================
# RESET PASSWORD
# =============================================================================

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token."""
    if request.method == 'GET':
        return render_template('reset_password.html', token=token)

    new_password = request.form.get('password')
    if not new_password:
        flash("Password is required", "error")
        return render_template('reset_password.html', token=token)

    # In full version, validate token and reset password
    flash("Password reset successful. Please login.", "success")
    return redirect(url_for('auth.login'))


# =============================================================================
# GOOGLE OAUTH WITH SUPABASE
# =============================================================================

@auth_bp.route('/login/google')
def login_google():
    """
    Initiate Google OAuth flow via Supabase.

    Redirects user to Supabase Google OAuth consent screen.
    """
    from src.auth_utils import get_google_oauth_url
    from flask import request as flask_request, session

    # Check if Supabase is configured (strip whitespace/newlines)
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "").strip()

    if not supabase_url or not supabase_key:
        print("Google OAuth Error: SUPABASE_URL or SUPABASE_ANON_KEY not configured")
        flash("Google login is not configured. Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables.", "error")
        return redirect(url_for('auth.login'))

    # Construct callback URL (strip whitespace/newlines)
    # Priority: SUPABASE_REDIRECT_URL > RENDER_EXTERNAL_URL > current request
    redirect_url = os.getenv("SUPABASE_REDIRECT_URL", "").strip()

    if not redirect_url:
        # Try RENDER_EXTERNAL_URL (for Render deployments)
        render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip()
        if render_url:
            redirect_url = f"{render_url}/auth/callback"
        else:
            # Construct from current request (for local/custom deployments)
            base_url = f"{flask_request.scheme}://{flask_request.host}"
            redirect_url = f"{base_url}/auth/callback"

    # Log the redirect URL for debugging
    print(f"Google OAuth: Using redirect URL: {redirect_url}")

    try:
        # Pass session to store code verifier for PKCE and redirect_override for custom URL
        oauth_url = get_google_oauth_url(session_storage=session, redirect_override=redirect_url)

        if not oauth_url:
            flash("Failed to generate Google OAuth URL. Please check Supabase configuration.", "error")
            return redirect(url_for('auth.login'))

        print(f"Google OAuth: Redirecting to: {oauth_url}")
        return redirect(oauth_url)
    except Exception as e:
        print(f"Error in Google OAuth initiation: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Google sign-in error: {str(e)}", "error")
        return redirect(url_for('auth.login'))


@auth_bp.route('/auth/callback')
def auth_callback():
    """
    Handle OAuth callback from Supabase.

    Exchanges authorization code for user session, then logs user in.
    """
    from src.auth_utils import exchange_code_for_session
    from flask import session

    try:
        # Log all query parameters for debugging
        print(f"OAuth callback received with query params: {dict(request.args)}")

        # Get authorization code from query params
        code = request.args.get("code")
        if not code:
            # Check if there's an error parameter
            error = request.args.get("error")
            error_description = request.args.get("error_description")
            if error:
                print(f"OAuth error: {error} - {error_description}")
                flash(f"OAuth authentication failed: {error_description or error}", "error")
            else:
                flash("OAuth authentication failed: Missing authorization code", "error")
            return redirect(url_for('auth.login'))

        # Retrieve code verifier from session (for PKCE)
        code_verifier = session.get('oauth_code_verifier')
        if code_verifier:
            print(f"Retrieved code verifier from session")
            # Clean up the session
            session.pop('oauth_code_verifier', None)
        else:
            print(f"Warning: No code verifier found in session")

        # Exchange code for session
        session_data = exchange_code_for_session(code, code_verifier)

        if not session_data or session_data.get("error"):
            error_msg = session_data.get("error") if session_data else "Unknown error"
            print(f"OAuth exchange failed: {error_msg}")
            flash(f"OAuth authentication failed: {error_msg}", "error")
            return redirect(url_for('auth.login'))

        # Extract user data from session
        try:
            # Handle different response formats from Supabase
            if isinstance(session_data, dict):
                user_data = session_data.get("user", {})
                if not user_data and "data" in session_data:
                    # Sometimes Supabase wraps it in 'data'
                    user_data = session_data.get("data", {}).get("user", {})
            else:
                # If it's an object with attributes
                user_data = getattr(session_data, 'user', {})
                if not user_data:
                    user_data = getattr(session_data, 'data', {}).get('user', {}) if hasattr(session_data, 'data') else {}
            
            supabase_uid = user_data.get("id") if isinstance(user_data, dict) else getattr(user_data, 'id', None)
            email = user_data.get("email") if isinstance(user_data, dict) else getattr(user_data, 'email', None)
            full_name = ""
            if isinstance(user_data, dict):
                metadata = user_data.get("user_metadata", {})
                full_name = metadata.get("full_name", "") if isinstance(metadata, dict) else ""
            else:
                metadata = getattr(user_data, 'user_metadata', {})
                full_name = getattr(metadata, 'full_name', '') if hasattr(metadata, 'full_name') else ''

            if not supabase_uid or not email:
                print(f"Invalid user data: supabase_uid={supabase_uid}, email={email}")
                flash("OAuth authentication failed: Invalid user data", "error")
                return redirect(url_for('auth.login'))

        except Exception as e:
            print(f"Error extracting user data: {e}")
            import traceback
            traceback.print_exc()
            flash(f"OAuth authentication failed: {str(e)}", "error")
            return redirect(url_for('auth.login'))

        # Find or create user in local database
        try:
            local_user = db.get_user_by_supabase_uid(supabase_uid)

            if not local_user:
                # Check if email already exists (user may have registered with password)
                local_user = db.get_user_by_email(email)

                if local_user:
                    # Link existing account to Supabase
                    try:
                        db.link_supabase_account(local_user['id'], supabase_uid, 'google')
                    except Exception as e:
                        print(f"Error linking Supabase account: {e}")
                else:
                    # Create new user
                    username = email.split('@')[0]  # Use email prefix as username
                    # Ensure username is unique
                    base_username = username
                    counter = 1
                    while db.get_user_by_username(username):
                        username = f"{base_username}{counter}"
                        counter += 1

                    try:
                        user_id = db.create_oauth_user(
                            username=username,
                            email=email,
                            supabase_uid=supabase_uid,
                            oauth_provider='google'
                        )
                        local_user = db.get_user_by_id(user_id)
                    except Exception as e:
                        print(f"Error creating OAuth user: {e}")
                        import traceback
                        traceback.print_exc()
                        flash("Failed to create user account. Please try again.", "error")
                        return redirect(url_for('auth.login'))

            if not local_user:
                flash("Failed to retrieve user account. Please try again.", "error")
                return redirect(url_for('auth.login'))

            # Create Flask-Login User object - ensure id is UUID string
            user_id_str = str(local_user['id']) if local_user.get('id') else None
            if not user_id_str:
                flash("Invalid user data. Please try again.", "error")
                return redirect(url_for('auth.login'))
            
            user = User(
                user_id_str,
                local_user['username'],
                local_user['email'],
                local_user.get('is_admin', False),
                local_user.get('is_active', True),
                local_user.get('tier', 'FREE')
            )

            # Log user in
            login_user(user, remember=True)

            # Log activity (with error handling)
            try:
                db.log_activity(
                    action="google_login",
                    user_id=user_id_str,
                    resource_type="user",
                    resource_id=None,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get("User-Agent")
                )
            except Exception as e:
                print(f"Failed to log activity: {e}")

            flash(f"Welcome{', ' + full_name if full_name else ''}! You're now logged in with Google.", "success")
            return redirect(url_for('index'))
        
        except Exception as e:
            print(f"Database error in OAuth callback: {e}")
            import traceback
            traceback.print_exc()
            flash("An error occurred during authentication. Please try again.", "error")
            return redirect(url_for('auth.login'))
    
    except Exception as e:
        print(f"Unexpected error in OAuth callback: {e}")
        import traceback
        traceback.print_exc()
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('auth.login'))
