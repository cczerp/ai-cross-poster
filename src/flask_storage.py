"""
Flask Session Storage for Supabase Auth
Based on: https://supabase.com/blog/oauth2-login-python-flask-apps
"""

from gotrue import SyncSupportedStorage
from flask import session


class FlaskSessionStorage(SyncSupportedStorage):
    """
    Custom storage adapter for Supabase Auth to use Flask sessions.

    This tells the Supabase authentication library (gotrue) how to
    retrieve, store and remove sessions (JWT tokens) in Flask's session.
    """

    def __init__(self):
        self.storage = session

    def get_item(self, key: str) -> str | None:
        """Retrieve item from Flask session"""
        if key in self.storage:
            return self.storage[key]
        return None

    def set_item(self, key: str, value: str) -> None:
        """Store item in Flask session"""
        self.storage[key] = value

    def remove_item(self, key: str) -> None:
        """Remove item from Flask session"""
        if key in self.storage:
            self.storage.pop(key, None)
