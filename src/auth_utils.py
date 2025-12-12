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


def get_google_oauth_url(session_storage: dict = None, redirect_override: Optional[str] = None) -> Optional[Tuple[str, str, str]]:
    """
    Generate Google OAuth URL via Supabase using OAuth 2.1 Authorization Code flow with PKCE.
    
    Implements OAuth 2.1 specification:
    - Step 1: Generate PKCE parameters (code_verifier, code_challenge)
    - Step 2: Redirect to authorization endpoint with PKCE parameters
    - Uses state parameter for CSRF protection
    
    Returns:
        Tuple (oauth_url, flow_id, state) or None if Supabase is not configured
    """
    # Strip whitespace/newlines from environment variables
    supabase_url = os.getenv("SUPABASE_URL", "").strip()

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

    if not supabase_url:
        return None

    try:
        print(f"[OAUTH 2.1] Generating OAuth URL for redirect: {redirect_url}")

        # Step 1: Generate PKCE parameters (OAuth 2.1 requirement)
        code_verifier, code_challenge = generate_pkce_pair()
        print(f"[OAUTH 2.1] Generated PKCE code_verifier (length: {len(code_verifier)}) and code_challenge")

        # Generate state parameter for CSRF protection (OAuth 2.1 requirement)
        state = generate_state()
        print(f"[OAUTH 2.1] Generated state parameter for CSRF protection")

        # Generate random flow_id to link verifier across workers (internal tracking)
        flow_id = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')

        # Store PKCE verifier and state in session (OAuth 2.1 requirement)
        if session_storage is not None:
            session_storage['oauth_code_verifier'] = code_verifier
            session_storage['oauth_state'] = state
            session_storage['oauth_flow_id'] = flow_id
            print(f"[OAUTH 2.1] Stored code_verifier and state in session")

        # Also store in filesystem as backup for local development
        from pathlib import Path
        state_dir = Path('./data/oauth_state')
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
            state_file = state_dir / f"{flow_id}.txt"
            # Store both verifier and state, separated by newline
            state_file.write_text(f"{code_verifier}\n{state}")
            print(f"[OAUTH 2.1] Also stored in filesystem (local dev): {state_file.absolute()}")
        except Exception as e:
            print(f"[OAUTH 2.1] Filesystem storage failed (expected on cloud): {e}")

        # Append flow_id to redirect_to URL so it survives the OAuth round-trip
        from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
        parsed = urlparse(redirect_url)
        query_dict = parse_qs(parsed.query)
        query_dict['flow_id'] = [flow_id]
        new_query = urlencode(query_dict, doseq=True)
        redirect_with_flow = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

        # Step 2: Construct OAuth 2.1 authorization request
        # Note: Supabase provider OAuth uses /auth/v1/authorize with provider parameter
        # For standard OAuth 2.1 server, would use /auth/v1/oauth/authorize
        params = {
            'provider': 'google',  # Supabase provider OAuth
            'redirect_to': redirect_with_flow,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',  # OAuth 2.1 requires uppercase S256
            'state': state  # CSRF protection
        }
        oauth_url = f"{supabase_url}/auth/v1/authorize?{urlencode(params)}"

        print(f"[OAUTH 2.1] Generated OAuth URL with PKCE (S256) and state")
        print(f"[OAUTH 2.1] Redirect URL with flow_id: {redirect_with_flow}")
        print(f"[OAUTH 2.1] Full OAuth URL: {oauth_url[:150]}...")
        return oauth_url, flow_id, state

    except Exception as e:
        print(f"[OAUTH 2.1] Error generating OAuth URL: {e}")
        import traceback
        traceback.print_exc()
        return None


def exchange_code_for_session(auth_code: str, code_verifier: str = None, redirect_uri: str = None, state: str = None) -> Optional[Dict]:
    """
    Exchange OAuth authorization code for tokens using OAuth 2.1 Authorization Code flow with PKCE.
    
    Implements OAuth 2.1 Step 5: Token Exchange
    - Uses grant_type=authorization_code
    - Includes code, code_verifier, redirect_uri, and client_id
    - Returns access_token, refresh_token, id_token, and expires_in

    Args:
        auth_code: OAuth authorization code from callback
        code_verifier: PKCE code verifier from the initial OAuth request (required)
        redirect_uri: Redirect URI used in authorization request (for validation)
        state: State parameter from authorization request (for CSRF validation)

    Returns:
        Dict with tokens (access_token, refresh_token, id_token) and user data, or None if failed
    """
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "").strip()

    if not supabase_url or not supabase_key:
        print("[OAUTH 2.1] Error: Supabase not configured")
        return None

    if not code_verifier:
        print("[OAUTH 2.1] Error: code_verifier is required for PKCE flow")
        return {"error": "Missing code_verifier"}

    try:
        print(f"[OAUTH 2.1] Exchanging authorization code for tokens")
        print(f"  Code length: {len(auth_code)}, Verifier length: {len(code_verifier)}")
        print(f"  Code: {auth_code[:20]}...")
        print(f"  Verifier: {code_verifier[:20]}...")

        # Make direct HTTP request to Supabase Auth API
        import httpx

        # OAuth 2.1 token exchange endpoint
        # Note: Supabase provider OAuth uses /auth/v1/token with grant_type=pkce
        # For standard OAuth 2.1 server, would use /auth/v1/oauth/token with grant_type=authorization_code
        url = f"{supabase_url}/auth/v1/token?grant_type=pkce"
        headers = {
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # OAuth 2.1 token exchange payload
        # Supabase uses "auth_code" for provider OAuth, standard OAuth 2.1 uses "code"
        payload = {
            "auth_code": auth_code,
            "code_verifier": code_verifier
        }
        
        # Add redirect_uri if provided (for validation)
        if redirect_uri:
            payload["redirect_uri"] = redirect_uri

        print(f"[OAUTH 2.1] Making token exchange request to: {url}")
        print(f"[OAUTH 2.1] Payload: {{'auth_code': '...', 'code_verifier': '...'}}")

        response = httpx.post(url, headers=headers, json=payload, timeout=30.0)

        print(f"[OAUTH 2.1] Response status: {response.status_code}")
        print(f"[OAUTH 2.1] Response body: {response.text[:200]}")

        if response.status_code == 200:
            token_data = response.json()
            print(f"[OAUTH 2.1] Token exchange successful!")
            print(f"[OAUTH 2.1] Received access_token, refresh_token, and user data")
            return token_data
        else:
            error_text = response.text[:500]
            print(f"[OAUTH 2.1] Token exchange failed with status {response.status_code}: {error_text}")
            return {"error": f"HTTP {response.status_code}: {error_text}"}

    except Exception as e:
        print(f"[OAUTH 2.1] Failed to exchange code for tokens: {e}")
        import traceback
        traceback.print_exc()
        return None


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
