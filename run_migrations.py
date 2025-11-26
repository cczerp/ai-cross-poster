#!/usr/bin/env python3
"""
Manual Database Migration Script
==================================
Run this script once to create tables and seed initial data.
Do NOT run this on every deployment - only when setting up
a new database or applying new migrations.

Usage:
    python run_migrations.py
"""

from src.database import get_db

if __name__ == "__main__":
    print("=" * 60)
    print("AI Cross-Poster - Database Migration")
    print("=" * 60)

    db = get_db()
    db.run_migrations()

    print("\n✅ All done! Database is ready to use.")
    print("=" * 60)
