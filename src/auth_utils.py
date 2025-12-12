"""
Supabase Authentication Utilities
===================================
Google OAuth integration with Supabase
Based on: https://supabase.com/blog/oauth2-login-python-flask-apps
"""

import os
import base64
import secrets
from typing import Optional, Dict, Tuple
from flask import g
from werkzeug.local import LocalProxy
from supabase.client import Client, ClientOptions
from src.flask_storage import FlaskSessionStorage


def get_supabase_client() -> Client:
    """
    Get or create Supabase client with PKCE flow support.

    Uses Flask's global 'g' object to store client instance per request.
    Configures client with:
    - FlaskSessionStorage for session management
    - flow_type="pkce" for OAuth PKCE flow

    Returns:
        Supabase Client instance or None if not configured
    """
    if "supabase" not in g:
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        supabase_key = os.getenv("SUPABASE_ANON_KEY", "").strip()

        if not supabase_url or not supabase_key:
            return None

        try:
            g.supabase = Client(
                supabase_url,
                supabase_key,
                options=ClientOptions(
                    storage=FlaskSessionStorage(),
                    flow_type="pkce"  # Critical for OAuth PKCE flow
                ),
            )
        except Exception as e:
            print(f"[OAUTH] Failed to create Supabase client: {e}")
            return None

    return g.supabase


# Create thread-safe proxy to supabase client
supabase: Client = LocalProxy(get_supabase_client)


def get_google_oauth_url(session_storage: dict = None, redirect_override: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """
    Generate Google OAuth URL via Supabase Python client.

    The Supabase client with flow_type="pkce" automatically handles:
    - Generating code_verifier
    - Storing it in Flask session via FlaskSessionStorage
    - Creating the OAuth URL with proper parameters

    Returns:
        Tuple (oauth_url, flow_id) or None if Supabase is not configured
    """
    # Get redirect URL from environment, or try to construct from request
    redirect_url = redirect_override or os.getenv("SUPABASE_REDIRECT_URL", "").strip()
    # If not set, try to use RENDER_EXTERNAL_URL or construct from request
    if not redirect_url:
        # On Render, use RENDER_EXTERNAL_URL if available
        render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip()
        if render_url:
            redirect_url = f"{render_url}/auth/callback"
        else:
            # Fallback to localhost for local development
            redirect_url = "http://localhost:5000/auth/callback"

    # Get Supabase client
    client = get_supabase_client()
    if not client:
        print("[OAUTH] Supabase client not configured")
        return None

    try:
        print(f"[OAUTH] Generating OAuth URL for redirect: {redirect_url}")

        # Generate random flow_id for tracking (optional, not required by Supabase)
        flow_id = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')

        # Store flow_id in session for tracking
        if session_storage is not None:
            session_storage['oauth_flow_id'] = flow_id
            print(f"[OAUTH] Stored flow_id in session")

        # Use Supabase client to generate OAuth URL
        # The client with flow_type="pkce" automatically:
        # - Generates code_verifier
        # - Stores it in FlaskSessionStorage
        # - Returns the OAuth URL
        response = client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url
            }
        })

        oauth_url = response.url
        print(f"[OAUTH] Generated OAuth URL using Supabase client with PKCE")
        print(f"[OAUTH] Redirect URL: {redirect_url}")
        print(f"[OAUTH] OAuth URL: {oauth_url[:150]}...")

        return oauth_url, flow_id

    except Exception as e:
        print(f"[OAUTH] Error generating OAuth URL: {e}")
        import traceback
        traceback.print_exc()
        return None


def exchange_code_for_session(auth_code: str, code_verifier: str = None, redirect_uri: str = None, state: str = None) -> Optional[Dict]:
    """
    Exchange OAuth authorization code for session using Supabase Python client.

    The Supabase client with flow_type="pkce" automatically:
    - Retrieves code_verifier from FlaskSessionStorage
    - Exchanges the code for tokens using PKCE
    - Stores the session in Flask session

    Args:
        auth_code: OAuth authorization code from callback
        code_verifier: (Deprecated - client handles this) PKCE code verifier
        redirect_uri: (Unused) Redirect URI used in authorization request
        state: (Unused) State parameter from authorization request

    Returns:
        Dict with tokens (access_token, refresh_token) and user data, or None if failed
    """
    # Get Supabase client
    client = get_supabase_client()
    if not client:
        print("[OAUTH] Error: Supabase client not configured")
        return None

    try:
        print(f"[OAUTH] Exchanging authorization code for session")
        print(f"  Code: {auth_code[:20]}...")

        # Use Supabase client to exchange code for session
        # The client with flow_type="pkce" automatically:
        # - Retrieves code_verifier from FlaskSessionStorage
        # - Sends it with the code exchange request
        # - Stores the resulting session
        response = client.auth.exchange_code_for_session({"auth_code": auth_code})

        print(f"[OAUTH] Token exchange successful!")
        print(f"[OAUTH] Session established with user data")

        # Return session data
        return {
            "user": response.user.__dict__ if hasattr(response.user, '__dict__') else response.user,
            "session": response.session.__dict__ if hasattr(response.session, '__dict__') else response.session
        }

    except Exception as e:
        print(f"[OAUTH] Failed to exchange code for session: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
