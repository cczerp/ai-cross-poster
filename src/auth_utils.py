"""
Supabase Authentication Utilities
===================================
Google OAuth integration with Supabase using OAuth 2.1 with PKCE
Implements OAuth 2.1 Authorization Code flow with PKCE as per Supabase Auth specification
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Dict, Tuple
from supabase import create_client, Client


def generate_pkce_pair():
    """
    Generate PKCE code verifier and code challenge following OAuth 2.1 spec.
    
    OAuth 2.1 requires:
    - code_verifier: 43-128 characters, URL-safe base64
    - code_challenge: SHA256 hash of verifier, base64url encoded
    - code_challenge_method: S256 (SHA-256)

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate a random code verifier (43-128 characters as per OAuth 2.1 spec)
    # Using 32 bytes = 256 bits, which when base64url encoded gives ~43 characters
    code_verifier_bytes = secrets.token_bytes(32)
    code_verifier = base64.urlsafe_b64encode(code_verifier_bytes).decode('utf-8').rstrip('=')

    # Generate code challenge from verifier using SHA256 (S256 method per OAuth 2.1)
    challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')

    return code_verifier, code_challenge


def generate_state():
    """
    Generate a random state parameter for CSRF protection (OAuth 2.1 requirement).
    
    Returns:
        Random state string
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

def get_supabase_client() -> Optional[Client]:
    """
    Create and return Supabase client for OAuth.

    Returns None if SUPABASE_URL or SUPABASE_ANON_KEY are not configured.
    """
    # Strip whitespace/newlines from environment variables
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "").strip()

    if not supabase_url or not supabase_key:
        return None

    try:
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"Failed to create Supabase client: {e}")
        return None


def get_google_oauth_url(session_storage: dict = None, redirect_override: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """
    Generate Google OAuth URL via Supabase Python client.

    The Supabase client handles PKCE automatically - no manual PKCE management needed.

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
    supabase = get_supabase_client()
    if not supabase:
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
        # The client automatically handles PKCE internally
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url
            }
        })

        oauth_url = response.url
        print(f"[OAUTH] Generated OAuth URL using Supabase client")
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

    The Supabase client automatically handles PKCE code_verifier internally.
    Note: code_verifier parameter is kept for backwards compatibility but not used.

    Args:
        auth_code: OAuth authorization code from callback
        code_verifier: (Deprecated - client handles this) PKCE code verifier
        redirect_uri: (Unused) Redirect URI used in authorization request
        state: (Unused) State parameter from authorization request

    Returns:
        Dict with tokens (access_token, refresh_token) and user data, or None if failed
    """
    # Get Supabase client
    supabase = get_supabase_client()
    if not supabase:
        print("[OAUTH] Error: Supabase client not configured")
        return None

    try:
        print(f"[OAUTH] Exchanging authorization code for session")
        print(f"  Code: {auth_code[:20]}...")

        # Use Supabase client to exchange code for session
        # The client automatically uses the stored code_verifier from PKCE flow
        response = supabase.auth.exchange_code_for_session({"auth_code": auth_code})

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


def refresh_access_token(refresh_token: str) -> Optional[Dict]:
    """
    Refresh access token using OAuth 2.1 Refresh Token flow.
    
    Implements OAuth 2.1 Refresh Token grant type:
    - Uses grant_type=refresh_token
    - Returns new access_token and optionally new refresh_token

    Args:
        refresh_token: Refresh token from previous token exchange

    Returns:
        Dict with new tokens (access_token, refresh_token, expires_in) or None if failed
    """
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "").strip()

    if not supabase_url or not supabase_key:
        print("[OAUTH 2.1] Error: Supabase not configured")
        return None

    try:
        print(f"[OAUTH 2.1] Refreshing access token")

        import httpx

        # OAuth 2.1 refresh token endpoint
        url = f"{supabase_url}/auth/v1/token?grant_type=refresh_token"
        headers = {
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "refresh_token": refresh_token
        }

        print(f"[OAUTH 2.1] Making refresh token request to: {url}")

        response = httpx.post(url, headers=headers, json=payload, timeout=30.0)

        print(f"[OAUTH 2.1] Response status: {response.status_code}")

        if response.status_code == 200:
            token_data = response.json()
            print(f"[OAUTH 2.1] Token refresh successful!")
            return token_data
        else:
            error_text = response.text[:500]
            print(f"[OAUTH 2.1] Token refresh failed: {error_text}")
            return {"error": f"HTTP {response.status_code}: {error_text}"}

    except Exception as e:
        print(f"[OAUTH 2.1] Failed to refresh token: {e}")
        import traceback
        traceback.print_exc()
        return None
