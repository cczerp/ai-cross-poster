# routes_admin.py
# -------------------------------------------------------------------------
# Admin-only routes & admin API endpoints
# -------------------------------------------------------------------------

from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from app import db  # same db instance imported from app.py

admin_bp = Blueprint("admin_bp", __name__)


# -------------------------------------------------------------------------
# Helper: Require admin
# -------------------------------------------------------------------------

def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            flash("Admin access required", "error")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return wrapper


# -------------------------------------------------------------------------
# ADMIN DASHBOARD
# -------------------------------------------------------------------------

@admin_bp.route("/admin")
@admin_required
def admin_dashboard():
    stats = db.get_system_stats()
    users = db.get_all_users(include_inactive=True)
    recent_logs = db.get_activity_logs(limit=20)

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        users=users,
        recent_activity=recent_logs
    )


# -------------------------------------------------------------------------
# ADMIN — USER LIST
# -------------------------------------------------------------------------

@admin_bp.route("/admin/users")
@admin_required
def admin_users():
    users = db.get_all_users(include_inactive=True)
    return render_template("admin/users.html", users=users)


# -------------------------------------------------------------------------
# ADMIN — USER DETAILS
# -------------------------------------------------------------------------

@admin_bp.route("/admin/user/<int:user_id>")
@admin_required
def admin_user_detail(user_id):
    user = db.get_user_by_id(user_id)
    if not user:
        flash("User not found", "error")
        return redirect(url_for("admin_bp.admin_users"))

    # Get recent listings
    cursor = db._get_cursor()
    cursor.execute(
        "SELECT * FROM listings WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (user_id,)
    )
    listings = [dict(row) for row in cursor.fetchall()]

    # Get activity logs
    logs = db.get_activity_logs(user_id=user_id, limit=50)

    return render_template(
        "admin/user_detail.html",
        user=user,
        listings=listings,
        activity=logs
    )


# -------------------------------------------------------------------------
# ADMIN — ACTIVITY LOGS
# -------------------------------------------------------------------------

@admin_bp.route("/admin/activity")
@admin_required
def admin_activity():
    page = request.args.get("page", 1, type=int)
    limit = 50
    offset = (page - 1) * limit

    user_id = request.args.get("user_id", type=int)
    action = request.args.get("action")

    logs = db.get_activity_logs(user_id=user_id, action=action, limit=limit, offset=offset)

    return render_template("admin/activity.html", logs=logs, page=page)


# =========================================================================
# ADMIN API ENDPOINTS
# =========================================================================

# -------------------------------------------------------------------------
# Toggle admin
# -------------------------------------------------------------------------

@admin_bp.route("/api/admin/user/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def api_toggle_admin(user_id):
    if user_id == current_user.id:
        return jsonify({"error": "You cannot change your own admin status"}), 400

    try:
        ok = db.toggle_user_admin(user_id)
        if not ok:
            return jsonify({"error": "User not found"}), 404

        db.log_activity(
            action="toggle_admin",
            user_id=current_user.id,
            resource_type="user",
            resource_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# Toggle active status
# -------------------------------------------------------------------------

@admin_bp.route("/api/admin/user/<int:user_id>/toggle-active", methods=["POST"])
@admin_required
def api_toggle_active(user_id):
    if user_id == current_user.id:
        return jsonify({"error": "You cannot deactivate your own account"}), 400

    try:
        ok = db.toggle_user_active(user_id)
        if not ok:
            return jsonify({"error": "User not found"}), 404

        db.log_activity(
            action="toggle_active",
            user_id=current_user.id,
            resource_type="user",
            resource_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# Delete user
# -------------------------------------------------------------------------

@admin_bp.route("/api/admin/user/<int:user_id>/delete", methods=["DELETE"])
@admin_required
def api_delete_user(user_id):

    if user_id == current_user.id:
        return jsonify({"error": "You cannot delete your own account"}), 400

    try:
        db.log_activity(
            action="delete_user",
            user_id=current_user.id,
            resource_type="user",
            resource_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )

        db.delete_user(user_id)
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
