"""
Supabase Authentication Utilities
===================================
Google OAuth integration with Supabase
Based on: https://supabase.com/blog/oauth2-login-python-flask-apps

Uses Redis (Upstash) for:
- Flask session storage (via Flask-Session)
- OAuth state/PKCE verifier storage (via direct Redis operations with TTL)
"""

import os
import base64
import secrets
from typing import Optional, Dict, Tuple
from flask import g
from werkzeug.local import LocalProxy
from supabase.client import Client, ClientOptions
from src.flask_storage import FlaskSessionStorage
import redis


# ============================================================================
# REDIS CLIENT FOR OAUTH STATE STORAGE
# ============================================================================

def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client for OAuth state/PKCE storage.

    Uses REDIS_URL from environment variables.
    Stores client in Flask's g object for request-scoped access.

    Returns:
        Redis client instance or None if not configured
    """
    if "redis_client" not in g:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            print("[REDIS] REDIS_URL not configured")
            return None

        # Parse Redis URL - handle CLI command format from Upstash
        if redis_url.startswith('redis-cli'):
            import re
            url_match = re.search(r'redis://[^\s]+', redis_url)
            if url_match:
                redis_url = url_match.group(0)
                redis_url = redis_url.replace('redis://', 'rediss://', 1)

        # Ensure we're using rediss:// for Upstash (TLS required)
        if redis_url.startswith('redis://') and 'upstash.io' in redis_url:
            redis_url = redis_url.replace('redis://', 'rediss://', 1)

        try:
            g.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,  # Decode responses to strings
                socket_connect_timeout=5,
                socket_timeout=5,
                ssl_cert_reqs=None  # Upstash: don't verify SSL cert
            )
            # Test connection
            g.redis_client.ping()
        except Exception as e:
            print(f"[REDIS] Failed to connect: {e}")
            return None

    return g.redis_client


def store_oauth_state(state: str, flow_id: str, ttl: int = 600) -> bool:
    """
    Store OAuth state in Redis with TTL.

    Args:
        state: OAuth state parameter (for CSRF protection)
        flow_id: Unique flow identifier
        ttl: Time to live in seconds (default: 10 minutes)

    Returns:
        True if stored successfully, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        key = f"resell_rebel:oauth:state:{state}"
        client.setex(key, ttl, flow_id)
        print(f"[REDIS] Stored OAuth state with TTL {ttl}s")
        return True
    except Exception as e:
        print(f"[REDIS] Failed to store OAuth state: {e}")
        return False


def verify_oauth_state(state: str) -> Optional[str]:
    """
    Verify and retrieve OAuth state from Redis.

    Args:
        state: OAuth state parameter to verify

    Returns:
        flow_id if state is valid, None otherwise
    """
    client = get_redis_client()
    if not client:
        return None

    try:
        key = f"resell_rebel:oauth:state:{state}"
        flow_id = client.get(key)
        if flow_id:
            # Delete after retrieval (one-time use)
            client.delete(key)
            print(f"[REDIS] OAuth state verified and consumed")
        return flow_id
    except Exception as e:
        print(f"[REDIS] Failed to verify OAuth state: {e}")
        return None


def store_pkce_verifier(flow_id: str, code_verifier: str, ttl: int = 600) -> bool:
    """
    Store PKCE code verifier in Redis with TTL.

    Args:
        flow_id: Unique flow identifier
        code_verifier: PKCE code verifier
        ttl: Time to live in seconds (default: 10 minutes)

    Returns:
        True if stored successfully, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        key = f"resell_rebel:oauth:pkce:{flow_id}"
        client.setex(key, ttl, code_verifier)
        print(f"[REDIS] Stored PKCE verifier with TTL {ttl}s")
        return True
    except Exception as e:
        print(f"[REDIS] Failed to store PKCE verifier: {e}")
        return False


def get_pkce_verifier(flow_id: str) -> Optional[str]:
    """
    Retrieve PKCE code verifier from Redis.

    Args:
        flow_id: Unique flow identifier

    Returns:
        code_verifier if found, None otherwise
    """
    client = get_redis_client()
    if not client:
        return None

    try:
        key = f"resell_rebel:oauth:pkce:{flow_id}"
        code_verifier = client.get(key)
        if code_verifier:
            # Delete after retrieval (one-time use)
            client.delete(key)
            print(f"[REDIS] PKCE verifier retrieved and consumed")
        return code_verifier
    except Exception as e:
        print(f"[REDIS] Failed to get PKCE verifier: {e}")
        return None


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
    - Storing it in Flask session (Redis-backed) via FlaskSessionStorage
    - Creating the OAuth URL with proper parameters

    Additionally stores OAuth state in Redis for extra CSRF protection.

    Returns:
        Tuple (oauth_url, flow_id, state) or None if Supabase is not configured
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

        # Generate random flow_id and state for CSRF protection
        flow_id = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')
        state = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')

        # Store flow_id in Flask session (Redis-backed) for tracking
        if session_storage is not None:
            session_storage['oauth_flow_id'] = flow_id
            session_storage['oauth_state'] = state
            print(f"[OAUTH] Stored flow_id and state in Redis session")

        # Also store state in Redis with TTL for extra security
        store_oauth_state(state, flow_id, ttl=600)  # 10 minutes

        # Use Supabase client to generate OAuth URL
        # The client with flow_type="pkce" automatically:
        # - Generates code_verifier
        # - Stores it in FlaskSessionStorage (which uses Redis via Flask-Session)
        # - Returns the OAuth URL with state parameter
        response = client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url,
                "query_params": {
                    "state": state  # Add state for CSRF protection
                }
            }
        })

        oauth_url = response.url
        print(f"[OAUTH] Generated OAuth URL using Supabase client with PKCE")
        print(f"[OAUTH] Redirect URL: {redirect_url}")
        print(f"[OAUTH] OAuth URL: {oauth_url[:150]}...")
        print(f"[OAUTH] State parameter: {state[:20]}...")

        return oauth_url, flow_id, state

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
