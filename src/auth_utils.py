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


def get_google_oauth_url() -> Optional[str]:
    """
    Generate Google OAuth URL via Supabase using PKCE flow.

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
            return None

        # Use sign_in_with_oauth which handles PKCE properly
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url
            }
        })

        # Return the OAuth URL
        return response.url if hasattr(response, 'url') else None
    except Exception as e:
        print(f"Error generating OAuth URL: {e}")
        return None


def exchange_code_for_session(auth_code: str) -> Optional[Dict]:
    """
    Exchange OAuth code for user session.

    Args:
        auth_code: OAuth authorization code from callback

    Returns:
        Dict with user data and session, or None if failed
    """
    supabase = get_supabase_client()
    if not supabase:
        return None

    try:
        response = supabase.auth.exchange_code_for_session({"code": auth_code})
        return response
    except Exception as e:
        print(f"Failed to exchange code for session: {e}")
        return None
