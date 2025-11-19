"""
Quick script to create admin account or check existing users
Run this with: python create_admin.py
"""
import sqlite3
from werkzeug.security import generate_password_hash

db_path = 'data/cross_poster.db'

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check existing users
cursor.execute("SELECT id, username, email, is_admin FROM users")
users = cursor.fetchall()

print("\n" + "="*60)
print("CURRENT USERS:")
print("="*60)
if users:
    for user in users:
        admin_status = "ADMIN" if user[3] else "User"
        print(f"ID: {user[0]} | Username: {user[1]} | Email: {user[2]} | Role: {admin_status}")
else:
    print("No users found!")
print("="*60)

# Create admin if no users exist
if len(users) == 0:
    print("\nCreating default admin account...")
    password_hash = generate_password_hash('admin')
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, is_admin, is_active, email_verified)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ('admin', 'admin@resellgenius.local', password_hash, 1, 1, 1))
    conn.commit()
    print("\n✓ Admin account created!")
    print("Username: admin")
    print("Password: admin")
    print("\nYou can now login at http://localhost:5000/login")
else:
    print("\nUsers already exist.")
    print("\nTo make an existing user admin, run:")
    print(f"  python create_admin.py USERNAME")

print("="*60 + "\n")

conn.close()

# If argument provided, make that user admin
import sys
if len(sys.argv) > 1:
    username = sys.argv[1]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
    if cursor.rowcount > 0:
        conn.commit()
        print(f"\n✓ User '{username}' is now an admin!")
    else:
        print(f"\n✗ User '{username}' not found")
    conn.close()
