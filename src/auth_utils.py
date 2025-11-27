"""
Supabase Authentication Utilities
===================================
Google OAuth integration with Supabase
"""

import os
from typing import Optional, Dict
from supabase import create_client, Client

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


def get_google_oauth_url(session_storage: dict = None) -> Optional[str]:
    """
    Generate Google OAuth URL via Supabase using PKCE flow.

    Args:
        session_storage: Dictionary to store the code verifier (Flask session)

    Returns:
        OAuth URL string or None if Supabase is not configured
    """
    # Strip whitespace/newlines from environment variables
    supabase_url = os.getenv("SUPABASE_URL", "").strip()

    # Get redirect URL from environment, or try to construct from request
    redirect_url = os.getenv("SUPABASE_REDIRECT_URL", "").strip()

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

    # Use Supabase client to initiate OAuth with PKCE
    try:
        supabase = get_supabase_client()
        if not supabase:
            print("Error: Could not create Supabase client")
            return None

        print(f"Attempting to generate OAuth URL for redirect: {redirect_url}")

        # Use sign_in_with_oauth which handles PKCE properly
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url
            }
        })

        print(f"OAuth response type: {type(response)}")

        # Try to extract code verifier and store in session
        if hasattr(response, 'code_verifier') and session_storage is not None:
            session_storage['oauth_code_verifier'] = response.code_verifier
            print(f"Stored code verifier in session")
        elif isinstance(response, dict) and 'code_verifier' in response and session_storage is not None:
            session_storage['oauth_code_verifier'] = response['code_verifier']
            print(f"Stored code verifier in session (from dict)")

        # Try different ways to get the URL
        if hasattr(response, 'url'):
            print(f"Found URL via .url attribute")
            return response.url
        elif isinstance(response, dict) and 'url' in response:
            print(f"Found URL in dict")
            return response['url']
        else:
            print(f"Could not find URL in response. Available attributes: {dir(response) if hasattr(response, '__dir__') else 'N/A'}")
            return None
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
    """
    supabase = get_supabase_client()
    if not supabase:
        return None

    try:
        # Build the exchange payload
        payload = {"code": auth_code}
        if code_verifier:
            payload["code_verifier"] = code_verifier
            print(f"Exchanging code with verifier")
        else:
            print(f"Warning: No code verifier provided for PKCE exchange")

        response = supabase.auth.exchange_code_for_session(payload)
        return response
    except Exception as e:
        print(f"Failed to exchange code for session: {e}")
        import traceback
        traceback.print_exc()
        return None
