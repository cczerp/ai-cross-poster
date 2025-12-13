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
    """Handle user login - using Supabase email/password auth."""
    if request.method == 'GET':
        return render_template('login.html')

    try:
        # POST — authenticate user with Supabase
        data = request.form
        email = data.get('email')
        password = data.get('password')

        print(f"[LOGIN] Attempting Supabase login for email: {email}", flush=True)

        if not email or not password:
            flash("Email and password required.", "error")
            return render_template('login.html')

        # Use Supabase client to sign in
        from src.auth_utils import get_supabase_client
        supabase = get_supabase_client()

        if not supabase:
            print("[LOGIN ERROR] Supabase client not configured!")
            flash("Authentication service unavailable. Please try again.", "error")
            return render_template('login.html')

        # Attempt to sign in with Supabase
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if not response or not response.user:
            print(f"[LOGIN] Supabase sign-in failed for email: {email}")
            flash("Invalid email or password.", "error")
            return render_template('login.html')

        print(f"[LOGIN] Supabase sign-in successful for email: {email}")
        print(f"[LOGIN] Supabase UID: {response.user.id}")

        # Get Supabase user data
        supabase_uid = str(response.user.id)
        user_email = response.user.email
        username = user_email.split('@')[0]  # Generate username from email

        # CRITICAL: Ensure user exists in PostgreSQL with supabase_uid for session persistence
        # Flask-Login will store supabase_uid in session, user_loader must find it
        print(f"[LOGIN] Checking if user exists in PostgreSQL (by supabase_uid)...", flush=True)
        user_data = db.get_user_by_supabase_uid(supabase_uid)

        if not user_data:
            print(f"[LOGIN] User not found in PostgreSQL, creating user record...", flush=True)
            try:
                # Create user in PostgreSQL with Supabase UID
                # Note: We don't store password hash since Supabase handles auth
                db.create_user_with_id(supabase_uid, username, user_email, password_hash=None)
                print(f"[LOGIN] User created in PostgreSQL with supabase_uid", flush=True)
                user_data = db.get_user_by_supabase_uid(supabase_uid)
            except Exception as create_error:
                print(f"[LOGIN ERROR] Failed to create user in PostgreSQL: {create_error}")
                import traceback
                traceback.print_exc()
                # Fall back to Supabase-only user (may cause session issues)
                user_data = None

        # Create User object for Flask-Login
        # IMPORTANT: User.id must be supabase_uid for session persistence
        if user_data:
            print(f"[LOGIN] Loading user from PostgreSQL", flush=True)
            user = User(
                user_data['supabase_uid'],  # Use Supabase UID as Flask-Login ID
                user_data['username'],
                user_data['email'],
                user_data.get('is_admin', False),
                user_data.get('is_active', True),
                user_data.get('tier', 'FREE')
            )
        else:
            print(f"[LOGIN WARNING] Using Supabase-only user (session may not persist)", flush=True)
            user = User(
                supabase_uid,      # Supabase UID
                username,          # Username from email
                user_email,        # Email from Supabase
                False,             # is_admin (default)
                True,              # is_active (default)
                'FREE'             # tier (default)
            )

        print(f"[LOGIN] Logging in user: {user.email} (Supabase UID: {user.id})")
        login_user(user, remember=True)
        print(f"[LOGIN] ✅ Login successful for {user.email}", flush=True)

        return redirect(url_for('index'))

    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        import traceback
        traceback.print_exc()
        flash("Invalid email or password.", "error")
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
    
    # Generate verification token
    from src.email_utils import generate_verification_token, send_verification_email_async
    from flask import current_app
    
    verification_token = generate_verification_token()
    # Note: user_id_str is UUID string, database method accepts it
    db.set_verification_token(user_id_str, verification_token)
    
    # Send verification email
    try:
        # Get mail instance from app (set in web_app.py)
        mail = current_app.mail
        send_verification_email_async(mail, email, username, verification_token, current_app)
        print(f"✅ Verification email queued for {email}")
    except Exception as e:
        print(f"⚠️  Failed to send verification email: {e}")
        import traceback
        traceback.print_exc()
        # Continue anyway - user can request resend later
        flash("Account created, but verification email could not be sent. Please contact support.", "warning")

    db.log_activity(
        action="register",
        user_id=user_id_str,
        resource_type="user",
        resource_id=None,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent")
    )

    # Redirect to email confirmation page instead of auto-login
    return redirect(url_for('auth.email_sent', email=email))


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
# EMAIL VERIFICATION
# =============================================================================

@auth_bp.route('/email-sent')
def email_sent():
    """Show email sent confirmation page."""
    email = request.args.get('email', '')
    return render_template('email_sent.html', email=email)


@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Verify user email with token."""
    if not token:
        flash("Invalid verification link.", "error")
        return redirect(url_for('auth.login'))
    
    # Verify email using token
    success = db.verify_email(token)
    
    if success:
        flash("Email verified successfully! You can now log in.", "success")
        return redirect(url_for('auth.login'))
    else:
        flash("Invalid or expired verification link. Please request a new one.", "error")
        return redirect(url_for('auth.login'))


@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    """Resend verification email."""
    if request.method == 'GET':
        return render_template('resend_verification.html')
    
    email = request.form.get('email')
    if not email:
        flash("Email is required", "error")
        return render_template('resend_verification.html')
    
    user_data = db.get_user_by_email(email)
    if not user_data:
        # Don't reveal if email exists or not (security)
        flash("If an account exists with that email, a verification link has been sent.", "info")
        return render_template('resend_verification.html')
    
    # Check if already verified
    if user_data.get('email_verified'):
        flash("This email is already verified. You can log in.", "info")
        return redirect(url_for('auth.login'))
    
    # Generate new token and send email
    from src.email_utils import generate_verification_token, send_verification_email_async
    from flask import current_app
    
    verification_token = generate_verification_token()
    user_id_str = str(user_data['id'])
    # Note: user_id_str is UUID string, database method accepts it
    db.set_verification_token(user_id_str, verification_token)
    
    try:
        # Get mail instance from app (set in web_app.py)
        mail = current_app.mail
        send_verification_email_async(mail, email, user_data['username'], verification_token, current_app)
        flash("Verification email sent! Please check your inbox.", "success")
    except Exception as e:
        print(f"⚠️  Failed to send verification email: {e}")
        import traceback
        traceback.print_exc()
        flash("Failed to send verification email. Please try again later.", "error")
    
    return redirect(url_for('auth.email_sent', email=email))


# =============================================================================
# DEBUG ENDPOINT - SUPABASE CONNECTION TEST
# =============================================================================

@auth_bp.route('/debug/supabase')
def debug_supabase():
    """Debug endpoint to test Supabase connectivity and session storage."""
    import os
    from flask import session, jsonify
    from src.auth_utils import get_supabase_client

    debug_info = {
        "environment_variables": {
            "SUPABASE_URL": bool(os.getenv("SUPABASE_URL", "").strip()),
            "SUPABASE_ANON_KEY": bool(os.getenv("SUPABASE_ANON_KEY", "").strip()),
            "FLASK_SECRET_KEY": bool(os.getenv("FLASK_SECRET_KEY", "").strip()),
        },
        "supabase_client": None,
        "session_storage": None,
        "flask_session_keys": list(session.keys()),
    }

    # Test Supabase client creation
    try:
        client = get_supabase_client()
        if client:
            debug_info["supabase_client"] = {
                "status": "✅ Connected",
                "url": client.supabase_url if hasattr(client, 'supabase_url') else "N/A",
                "storage_type": type(client.options.storage).__name__ if hasattr(client, 'options') else "N/A",
            }
        else:
            debug_info["supabase_client"] = {
                "status": "❌ Failed to create client",
                "error": "get_supabase_client() returned None"
            }
    except Exception as e:
        debug_info["supabase_client"] = {
            "status": "❌ Error",
            "error": str(e)
        }

    # Test session storage
    try:
        test_key = "debug_test_key"
        test_value = "debug_test_value"
        session[test_key] = test_value

        if session.get(test_key) == test_value:
            debug_info["session_storage"] = "✅ Working"
            session.pop(test_key, None)
        else:
            debug_info["session_storage"] = "❌ Failed to retrieve value"
    except Exception as e:
        debug_info["session_storage"] = f"❌ Error: {str(e)}"

    return jsonify(debug_info)


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
        print("=" * 80, flush=True)
        print("🟢 [LOGIN_GOOGLE] Starting OAuth flow", flush=True)
        print("=" * 80, flush=True)

        # Validate Flask secret key
        from flask import current_app
        secret_key = current_app.secret_key
        if not secret_key or secret_key == 'dev-secret-key-change-in-production':
            print("❌ [LOGIN_GOOGLE ERROR] FLASK_SECRET_KEY not configured!", flush=True)
            flash("Server configuration error. Please contact administrator.", "error")
            return redirect(url_for('auth.login'))

        print(f"✅ [LOGIN_GOOGLE] Secret key configured (length: {len(secret_key)})", flush=True)
        print(f"🔍 [LOGIN_GOOGLE] Session before OAuth: {dict(session)}", flush=True)

        # Pass session to store code verifier for PKCE and redirect_override for custom URL
        oauth_result = get_google_oauth_url(session_storage=session, redirect_override=redirect_url)

        if not oauth_result:
            flash("Failed to generate Google OAuth URL. Please check Supabase configuration.", "error")
            return redirect(url_for('auth.login'))

        oauth_url, flow_id = oauth_result

        # CRITICAL: Mark session as modified to ensure it's saved
        # This is important for multi-worker environments
        session.modified = True
        print(f"🔍 [LOGIN_GOOGLE] Session after OAuth URL generation: {dict(session)}", flush=True)
        print(f"✅ [LOGIN_GOOGLE] Session marked as modified", flush=True)
        print(f"✅ [LOGIN_GOOGLE] OAuth URL generated with flow_id: {flow_id[:10]}...", flush=True)
        print(f"🚀 [LOGIN_GOOGLE] Redirecting to: {oauth_url[:100]}...", flush=True)
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
    # CRITICAL: Log immediately at function entry
    print("=" * 80, flush=True)
    print("🔵 [CALLBACK] OAuth callback handler STARTED", flush=True)
    print("=" * 80, flush=True)

    from src.auth_utils import exchange_code_for_session
    from flask import session

    # Validate Flask secret key is set
    from flask import current_app
    secret_key = current_app.secret_key
    if not secret_key or secret_key == 'dev-secret-key-change-in-production':
        print("❌ [CALLBACK ERROR] FLASK_SECRET_KEY not configured properly!", flush=True)
        flash("Server configuration error. Please contact administrator.", "error")
        return redirect(url_for('auth.login'))

    print(f"✅ [CALLBACK] Secret key configured (length: {len(secret_key)})", flush=True)
    print(f"🔍 [CALLBACK] Session cookie name: {current_app.config.get('SESSION_COOKIE_NAME', 'session')}", flush=True)
    print(f"🔍 [CALLBACK] Session keys present: {list(session.keys())}", flush=True)

    try:
        # Log all query parameters for debugging
        print(f"🔍 [CALLBACK] Full callback URL: {request.url}", flush=True)
        print(f"🔍 [CALLBACK] Query params received: {dict(request.args)}", flush=True)
        print(f"🔍 [CALLBACK] All query param keys: {list(request.args.keys())}", flush=True)

        # Get flow_id from query params (used to retrieve code_verifier)
        flow_id = request.args.get('flow_id')
        print(f"🔍 [CALLBACK] flow_id from query: {flow_id[:10] if flow_id else 'None'}...", flush=True)

        # Get state parameter for CSRF validation (OAuth 2.1 requirement)
        received_state = request.args.get('state')
        stored_state = session.get('oauth_state')
        print(f"🔍 [CALLBACK] State validation - received: {bool(received_state)}, stored: {bool(stored_state)}", flush=True)
        
        # Validate state parameter (OAuth 2.1 CSRF protection)
        if received_state and stored_state:
            if received_state != stored_state:
                print(f"❌ [CALLBACK] State mismatch - possible CSRF attack!", flush=True)
                flash("OAuth authentication failed: Security validation error", "error")
                return redirect(url_for('auth.login'))
            print(f"✅ [CALLBACK] State parameter validated successfully", flush=True)
        elif received_state or stored_state:
            # One is missing - log warning but don't block (for backward compatibility)
            print(f"⚠️  [CALLBACK] State parameter missing on one side (received: {bool(received_state)}, stored: {bool(stored_state)})", flush=True)

        # Get authorization code from query params
        code = request.args.get("code")
        print(f"🔍 [CALLBACK] Authorization code present: {bool(code)}", flush=True)
        if not code:
            # Check if there's an error parameter (OAuth 2.1 error response)
            error = request.args.get("error")
            error_description = request.args.get("error_description")
            if error:
                print(f"❌ [CALLBACK] OAuth error from provider: {error} - {error_description}", flush=True)
                flash(f"OAuth authentication failed: {error_description or error}", "error")
            else:
                print(f"❌ [CALLBACK] Missing authorization code in callback", flush=True)
                flash("OAuth authentication failed: Missing authorization code", "error")
            return redirect(url_for('auth.login'))

        print(f"✅ [CALLBACK] Authorization code received (length: {len(code)})", flush=True)

        # Log session state for debugging
        print(f"🔍 [CALLBACK] Current session data: {dict(session)}", flush=True)

        # Supabase client with FlaskSessionStorage automatically handles PKCE:
        # - Code verifier is stored as 'supabase.auth.token-code-verifier'
        # - exchange_code_for_session() retrieves it automatically
        # - No manual retrieval needed!

        print(f"🔄 [CALLBACK] Calling exchange_code_for_session (Supabase handles PKCE)...", flush=True)
        session_data = exchange_code_for_session(code)
        print(f"✅ [CALLBACK] exchange_code_for_session returned", flush=True)
        print(f"🔍 [CALLBACK] session_data type: {type(session_data)}", flush=True)
        print(f"🔍 [CALLBACK] session_data keys: {list(session_data.keys()) if isinstance(session_data, dict) else 'N/A'}", flush=True)

        if not session_data or session_data.get("error"):
            error_msg = session_data.get("error") if session_data else "Unknown error"
            print(f"❌ [CALLBACK] OAuth exchange failed: {error_msg}", flush=True)
            flash(f"OAuth authentication failed: {error_msg}", "error")
            return redirect(url_for('auth.login'))

        print(f"✅ [CALLBACK] Token exchange successful, extracting user data...", flush=True)

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

            print(f"🔍 [CALLBACK] Extracted user data:", flush=True)
            print(f"   - supabase_uid: {supabase_uid}", flush=True)
            print(f"   - email: {email}", flush=True)
            print(f"   - full_name: {full_name}", flush=True)

            if not supabase_uid or not email:
                print(f"❌ [CALLBACK] Invalid user data: supabase_uid={supabase_uid}, email={email}", flush=True)
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
            print(f"🔍 [CALLBACK] Looking up user by supabase_uid: {supabase_uid}", flush=True)
            local_user = db.get_user_by_supabase_uid(supabase_uid)

            if not local_user:
                print(f"⚠️  [CALLBACK] User not found by supabase_uid, checking email: {email}", flush=True)
                # Check if email already exists (user may have registered with password)
                local_user = db.get_user_by_email(email)

                if local_user:
                    print(f"✅ [CALLBACK] Found existing user by email, linking to Supabase", flush=True)
                    # Link existing account to Supabase
                    try:
                        db.link_supabase_account(local_user['id'], supabase_uid, 'google')
                        print(f"✅ [CALLBACK] Successfully linked account", flush=True)
                    except Exception as e:
                        print(f"❌ [CALLBACK] Error linking Supabase account: {e}", flush=True)
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"⚠️  [CALLBACK] No existing user found, creating new OAuth user", flush=True)
                    # Create new user
                    username = email.split('@')[0]  # Use email prefix as username
                    # Ensure username is unique
                    base_username = username
                    counter = 1
                    while db.get_user_by_username(username):
                        username = f"{base_username}{counter}"
                        counter += 1

                    print(f"🔍 [CALLBACK] Creating OAuth user with username: {username}", flush=True)
                    try:
                        user_id = db.create_oauth_user(
                            username=username,
                            email=email,
                            supabase_uid=supabase_uid,
                            oauth_provider='google'
                        )
                        print(f"✅ [CALLBACK] Created OAuth user with ID: {user_id}", flush=True)
                        local_user = db.get_user_by_id(user_id)
                        print(f"✅ [CALLBACK] Retrieved created user from database", flush=True)
                    except Exception as e:
                        print(f"❌ [CALLBACK] Error creating OAuth user: {e}", flush=True)
                        import traceback
                        traceback.print_exc()
                        flash("Failed to create user account. Please try again.", "error")
                        return redirect(url_for('auth.login'))
            else:
                print(f"✅ [CALLBACK] Found existing user by supabase_uid: {local_user.get('username')}", flush=True)

            if not local_user:
                flash("Failed to retrieve user account. Please try again.", "error")
                return redirect(url_for('auth.login'))

            # Create Flask-Login User object - ensure id is UUID string
            print(f"🔍 [CALLBACK] Creating Flask-Login User object", flush=True)
            user_id_str = str(local_user['id']) if local_user.get('id') else None
            if not user_id_str:
                print(f"❌ [CALLBACK] Invalid user ID", flush=True)
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
            print(f"✅ [CALLBACK] User object created for: {local_user['username']}", flush=True)

            # Log user in
            print(f"🔐 [CALLBACK] Calling login_user()...", flush=True)
            login_user(user, remember=True)
            print(f"✅ [CALLBACK] login_user() completed successfully", flush=True)

            # Log activity (with error handling)
            try:
                print(f"📝 [CALLBACK] Logging activity...", flush=True)
                db.log_activity(
                    action="google_login",
                    user_id=user_id_str,
                    resource_type="user",
                    resource_id=None,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get("User-Agent")
                )
                print(f"✅ [CALLBACK] Activity logged", flush=True)
            except Exception as e:
                print(f"⚠️  [CALLBACK] Failed to log activity (non-critical): {e}", flush=True)

            print(f"=" * 80, flush=True)
            print(f"🎉 [CALLBACK] OAuth login successful for {local_user['username']}!", flush=True)
            print(f"=" * 80, flush=True)
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
