#!/usr/bin/env python3
"""
app_core.py
Core application setup for the AI Cross-Poster Web App.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from flask import Flask, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, current_user
from werkzeug.security import generate_password_hash


# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = "./data/uploads"
Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

# Initialize database
from src.database import get_db
db = get_db()

# Optional: Notification manager
try:
    from src.notifications import NotificationManager
    notification_manager = NotificationManager.from_env()
except Exception:
    notification_manager = None


# ---------------------------------------------------------
# Create default admin if no users exist
# ---------------------------------------------------------
def create_default_admin():
    cursor = db._get_cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    result = cursor.fetchone()
    count = result["count"] if isinstance(result, dict) else result[0]

    if count == 0:
        print("\n" + "=" * 60)
        print("No users found. Creating default admin: admin/admin")
        print("PLEASE CHANGE THIS PASSWORD IMMEDIATELY.")
        print("=" * 60 + "\n")

        password_hash = generate_password_hash("admin")
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, is_admin, is_active, email_verified)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            ("admin", "admin@resellgenius.local", password_hash, True, True, True),
        )
        db.conn.commit()


create_default_admin()


# ---------------------------------------------------------
# Login Manager + User Model
# ---------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "main.login"


class User(UserMixin):
    def __init__(self, user_id, username, email, is_admin=False, is_active=True):
        self.id = user_id
        self.username = username
        self.email = email
        self.is_admin = is_admin
        self._is_active = is_active

    @property
    def is_active(self):
        return self._is_active

    @staticmethod
    def get(user_id):
        user = db.get_user_by_id(user_id)
        if not user:
            return None
        return User(
            user["id"],
            user["username"],
            user["email"],
            user.get("is_admin", False),
            user.get("is_active", True),
        )


@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))


# ---------------------------------------------------------
# Admin decorator
# ---------------------------------------------------------
from functools import wraps
from flask import request, jsonify


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required", "error")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------
# Export app + db + objects
# ---------------------------------------------------------
__all__ = ["app", "db", "notification_manager", "User", "admin_required"]
