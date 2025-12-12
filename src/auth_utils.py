"""
Supabase Authentication Utilities
===================================
Google OAuth integration with Supabase
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Dict, Tuple
from supabase import create_client, Client


def generate_pkce_pair():
    """
    Generate PKCE code verifier and code challenge.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate a random code verifier (43-128 characters)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

    # Generate code challenge from verifier using SHA256
    challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')

    return code_verifier, code_challenge

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
    Generate Google OAuth URL via Supabase using PKCE flow.

    Returns:
        Tuple (oauth_url, state) or None if Supabase is not configured
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
        print(f"Generating OAuth URL for redirect: {redirect_url}")

        # Generate our own PKCE parameters
        code_verifier, code_challenge = generate_pkce_pair()
        print(f"Generated PKCE code verifier and challenge")

        # Generate random flow_id to link verifier across workers (avoid 'state' which Supabase owns)
        flow_id = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')

        # Store code verifier in session as fallback for single-worker deployments
        if session_storage is not None:
            session_storage['oauth_code_verifier'] = code_verifier
            session_storage['oauth_flow_id'] = flow_id
            print(f"Stored code verifier in session: {code_verifier[:10]}...")

        # Store verifier in database (survives multi-worker on Render/cloud platforms)
        # Use database instead of filesystem for cloud deployments
        try:
            from src.database import get_db
            db = get_db()
            cursor = db._get_cursor()
            try:
                # Create oauth_state table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS oauth_state (
                        flow_id TEXT PRIMARY KEY,
                        code_verifier TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Insert the code verifier
                cursor.execute("""
                    INSERT INTO oauth_state (flow_id, code_verifier)
                    VALUES (%s, %s)
                    ON CONFLICT (flow_id) DO UPDATE SET code_verifier = EXCLUDED.code_verifier
                """, (flow_id, code_verifier))
                db.conn.commit()
                print(f"✅ Stored code verifier in database for flow_id: {flow_id[:10]}...")
            finally:
                cursor.close()
        except Exception as e:
            print(f"⚠️ Failed to store in database, falling back to session: {e}")

        # ALSO keep filesystem as backup for local development
        from pathlib import Path
        state_dir = Path('./data/oauth_state')
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
            state_file = state_dir / f"{flow_id}.txt"
            state_file.write_text(code_verifier)
            print(f"✅ Also stored in filesystem (local dev): {state_file.absolute()}")
        except Exception as e:
            print(f"⚠️ Filesystem storage failed (expected on cloud): {e}")

        # Append flow_id to redirect_to URL so it survives the OAuth round-trip
        from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
        parsed = urlparse(redirect_url)
        query_dict = parse_qs(parsed.query)
        query_dict['flow_id'] = [flow_id]
        new_query = urlencode(query_dict, doseq=True)
        redirect_with_flow = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

        # Construct OAuth URL (let Supabase manage its own 'state' parameter)
        params = {
            'provider': 'google',
            'redirect_to': redirect_with_flow,
            'code_challenge': code_challenge,
            'code_challenge_method': 's256'
        }
        oauth_url = f"{supabase_url}/auth/v1/authorize?{urlencode(params)}"

        print(f"Generated OAuth URL with PKCE and flow_id: {flow_id[:10]}...")
        print(f"Redirect URL with flow_id: {redirect_with_flow}")
        print(f"Full OAuth URL: {oauth_url[:150]}...")
        return oauth_url, flow_id

    except Exception as e:
        print(f"Error generating OAuth URL: {e}")
        import traceback
        traceback.print_exc()
        return None


def exchange_code_for_session(auth_code: str, code_verifier: str = None) -> Optional[Dict]:
    """
    Exchange OAuth code for user session using PKCE.

    Args:
        auth_code: OAuth authorization code from callback
        code_verifier: PKCE code verifier from the initial OAuth request

    Returns:
        Dict with user data and session, or None if failed

    Note:
        PKCE token exchange only requires 'code' and 'code_verifier' parameters.
        The redirect_uri is NOT needed for PKCE flows (unlike standard OAuth 2.0).
    """
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "").strip()

    if not supabase_url or not supabase_key:
        print("Error: Supabase not configured")
        return None

    try:
        print(f"Exchanging code with verifier")
        print(f"  Code length: {len(auth_code)}, Verifier length: {len(code_verifier) if code_verifier else 0}")
        print(f"  Code: {auth_code[:20]}...")
        if code_verifier:
            print(f"  Verifier: {code_verifier[:20]}...")

        # Make direct HTTP request to Supabase Auth API
        import httpx

        url = f"{supabase_url}/auth/v1/token"
        headers = {
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        # PKCE token exchange: grant_type must be "authorization_code" with code_verifier present
        # Standard OAuth 2.0 PKCE extension uses authorization_code grant type
        payload = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "code_verifier": code_verifier
        }

        print(f"Making direct request to: {url}")
        print(f"Payload (PKCE): {payload}")

        response = httpx.post(url, headers=headers, json=payload, timeout=30.0)

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:200]}")

        if response.status_code == 200:
            print("Exchange successful!")
            return response.json()
        else:
            print(f"Exchange failed with status {response.status_code}")
            return {"error": f"HTTP {response.status_code}: {response.text}"}

    except Exception as e:
        print(f"Failed to exchange code for session: {e}")
        import traceback
        traceback.print_exc()
        return None
