#!/usr/bin/env python3
"""
AI Cross-Poster Web App
========================
Mobile-friendly web interface for inventory management and cross-platform listing.

Run with:
    python web_app.py

Or deploy to:
    - Heroku
    - DigitalOcean
    - AWS
    - Your own server
"""

import os
import uuid
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from src.schema import UnifiedListing, Photo, Price, ListingCondition, Shipping, ItemSpecifics
from src.database import get_db
import csv
from io import StringIO, BytesIO

# Load environment
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['UPLOAD_FOLDER'] = './data/uploads'

# Ensure upload folder exists
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

# Initialize services
db = get_db()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'


# ============================================================================
# USER MODEL
# ============================================================================

class User(UserMixin):
    """User model for Flask-Login"""

    def __init__(self, user_id, username, email):
        self.id = user_id
        self.username = username
        self.email = email

    @staticmethod
    def get(user_id):
        """Get user by ID"""
        user_data = db.get_user_by_id(user_id)
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['email'])
        return None


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.get(int(user_id))


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')

        user_data = db.get_user_by_username(username)

        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'], user_data['username'], user_data['email'])
            login_user(user, remember=True)
            db.update_last_login(user_data['id'])

            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('index')})
            return redirect(url_for('index'))
        else:
            error_msg = 'Invalid username or password'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        # Validation
        if not username or not email or not password:
            error_msg = 'All fields are required'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('register.html')

        if len(password) < 6:
            error_msg = 'Password must be at least 6 characters'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('register.html')

        # Check if user exists
        if db.get_user_by_username(username):
            error_msg = 'Username already exists'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('register.html')

        if db.get_user_by_email(email):
            error_msg = 'Email already registered'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('register.html')

        # Create user
        password_hash = generate_password_hash(password)
        user_id = db.create_user(username, email, password_hash)

        # Auto-login
        user = User(user_id, username, email)
        login_user(user, remember=True)

        if request.is_json:
            return jsonify({'success': True, 'redirect': url_for('index')})
        flash('Account created successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
@login_required
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/create')
@login_required
def create_listing():
    """Create new listing page"""
    return render_template('create.html')


@app.route('/drafts')
@login_required
def drafts():
    """View saved drafts"""
    drafts_list = db.get_drafts(limit=100, user_id=current_user.id)
    return render_template('drafts.html', drafts=drafts_list)


@app.route('/listings')
@login_required
def listings():
    """View active listings"""
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT l.*, GROUP_CONCAT(pl.platform || ':' || pl.status) as platform_statuses
        FROM listings l
        LEFT JOIN platform_listings pl ON l.id = pl.listing_id
        WHERE l.status != 'draft' AND l.user_id = ?
        GROUP BY l.id
        ORDER BY l.created_at DESC
        LIMIT 50
    """, (current_user.id,))
    listings_list = [dict(row) for row in cursor.fetchall()]
    return render_template('listings.html', listings=listings_list)


@app.route('/notifications')
@login_required
def notifications():
    """View notifications"""
    if notification_manager:
        notifs = notification_manager.get_recent_notifications(limit=50)
    else:
        notifs = []
    return render_template('notifications.html', notifications=notifs)


@app.route('/settings')
@login_required
def settings():
    """User settings page"""
    user = db.get_user_by_id(current_user.id)
    marketplace_creds = db.get_all_marketplace_credentials(current_user.id)

    # Convert to dict for easier template access
    creds_dict = {cred['platform']: cred for cred in marketplace_creds}

    return render_template('settings.html', user=user, credentials=creds_dict)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/upload-photos', methods=['POST'])
@login_required
def upload_photos():
    """Handle photo uploads"""
    if 'photos' not in request.files:
        return jsonify({'error': 'No photos provided'}), 400

    files = request.files.getlist('photos')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No photos selected'}), 400

    # Save photos
    photo_paths = []
    for file in files:
        if file:
            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            photo_paths.append(filepath)

    # Store in session
    session['photo_paths'] = photo_paths

    return jsonify({
        'success': True,
        'count': len(photo_paths),
        'paths': photo_paths
    })


@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze_photos():
    """Analyze photos with AI"""
    photo_paths = session.get('photo_paths', [])

    if not photo_paths:
        return jsonify({'error': 'No photos to analyze'}), 400

    try:
        from src.ai.gemini_classifier import GeminiClassifier

        # Create photo objects
        photo_objects = [
            Photo(url="", local_path=p, order=i, is_primary=(i == 0))
            for i, p in enumerate(photo_paths)
        ]

        # Analyze with Gemini
        classifier = GeminiClassifier.from_env()
        analysis = classifier.analyze_item(photo_objects)

        if "error" in analysis:
            return jsonify({'error': analysis['error']}), 500

        return jsonify({
            'success': True,
            'analysis': analysis
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/save-draft', methods=['POST'])
@login_required
def save_draft():
    """Save listing as draft"""
    data = request.json
    photo_paths = session.get('photo_paths', [])

    if not photo_paths:
        return jsonify({'error': 'No photos uploaded'}), 400

    try:
        listing_uuid = str(uuid.uuid4())

        # Copy photos to permanent storage
        draft_photos_dir = Path("data/draft_photos") / listing_uuid
        draft_photos_dir.mkdir(parents=True, exist_ok=True)

        permanent_photo_paths = []
        for i, photo_path in enumerate(photo_paths):
            ext = Path(photo_path).suffix
            new_filename = f"photo_{i:02d}{ext}"
            permanent_path = draft_photos_dir / new_filename

            # Copy file
            import shutil
            shutil.copy2(photo_path, permanent_path)
            permanent_photo_paths.append(str(permanent_path))

        # Save to database
        listing_id = db.create_listing(
            listing_uuid=listing_uuid,
            title=data.get('title', 'Untitled'),
            description=data.get('description', ''),
            price=float(data.get('price', 0)),
            condition=data.get('condition', 'good'),
            photos=permanent_photo_paths,
            user_id=current_user.id,  # Add user_id
            cost=float(data.get('cost')) if data.get('cost') else None,
            quantity=int(data.get('quantity', 1)),
            storage_location=data.get('storage_location'),
            attributes={
                'brand': data.get('brand'),
                'size': data.get('size'),
                'color': data.get('color'),
                'shipping_cost': float(data.get('shipping_cost', 0)),
            }
        )

        # Clear session
        session.pop('photo_paths', None)

        return jsonify({
            'success': True,
            'listing_id': listing_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export-csv', methods=['GET'])
@login_required
def export_csv():
    """Export all drafts to CSV"""
    try:
        drafts = db.get_drafts(limit=1000, user_id=current_user.id)

        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['ID', 'Title', 'Description', 'Price', 'Cost', 'Condition',
                        'Brand', 'Size', 'Color', 'Storage Location', 'Quantity',
                        'Shipping Cost', 'Created'])

        # Data
        for draft in drafts:
            # Parse attributes
            attrs = {}
            if draft.get('attributes'):
                try:
                    attrs = json.loads(draft['attributes'])
                except:
                    pass

            writer.writerow([
                draft['id'],
                draft['title'],
                draft['description'],
                draft['price'],
                draft.get('cost', ''),
                draft['condition'],
                attrs.get('brand', ''),
                attrs.get('size', ''),
                attrs.get('color', ''),
                draft.get('storage_location', ''),
                draft.get('quantity', 1),
                attrs.get('shipping_cost', ''),
                draft['created_at']
            ])

        # Send file
        from flask import Response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=listings.csv'}
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/import-csv', methods=['POST'])
@login_required
def import_csv():
    """Import CSV to update storage locations"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Read CSV
        stream = StringIO(file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)

        updated = 0
        for row in reader:
            listing_id = row.get('ID')
            storage_location = row.get('Storage Location')

            if listing_id and storage_location:
                # Update storage location (only for user's own listings)
                cursor = db.conn.cursor()
                cursor.execute("""
                    UPDATE listings
                    SET storage_location = ?
                    WHERE id = ? AND user_id = ?
                """, (storage_location, listing_id, current_user.id))
                db.conn.commit()
                updated += 1

        return jsonify({
            'success': True,
            'updated': updated
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mark-sold', methods=['POST'])
@login_required
def mark_sold():
    """Mark listing as sold"""
    data = request.json

    try:
        listing_id = int(data['listing_id'])
        sold_price = float(data.get('sold_price')) if data.get('sold_price') else None
        quantity_sold = int(data.get('quantity_sold', 1))

        # Get listing
        listing = db.get_listing(listing_id)
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404

        # Verify ownership
        if listing.get('user_id') != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Update quantity
        current_quantity = listing.get('quantity', 1)
        remaining_quantity = max(0, current_quantity - quantity_sold)

        cursor = db.conn.cursor()
        if remaining_quantity == 0:
            # Mark as sold
            cursor.execute("""
                UPDATE listings
                SET status = 'sold',
                    quantity = 0,
                    sold_price = ?,
                    sold_date = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            """, (sold_price, listing_id, current_user.id))
        else:
            # Just reduce quantity
            cursor.execute("""
                UPDATE listings
                SET quantity = ?
                WHERE id = ? AND user_id = ?
            """, (remaining_quantity, listing_id, current_user.id))

        db.conn.commit()

        return jsonify({
            'success': True,
            'storage_location': listing.get('storage_location'),
            'remaining_quantity': remaining_quantity
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-draft/<int:listing_id>', methods=['DELETE'])
@login_required
def delete_draft(listing_id):
    """Delete a draft"""
    try:
        listing = db.get_listing(listing_id)

        if not listing:
            return jsonify({'error': 'Listing not found'}), 404

        # Verify ownership
        if listing.get('user_id') != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Delete photos directory
        import shutil
        if listing.get('listing_uuid'):
            draft_photos_dir = Path("data/draft_photos") / listing['listing_uuid']
            if draft_photos_dir.exists():
                shutil.rmtree(draft_photos_dir)

        db.delete_listing(listing_id)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/notification-email', methods=['POST'])
@login_required
def update_notification_email():
    """Update user's notification email"""
    try:
        data = request.json
        notification_email = data.get('notification_email')

        if not notification_email:
            return jsonify({'error': 'Notification email is required'}), 400

        db.update_notification_email(current_user.id, notification_email)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/marketplace-credentials', methods=['POST'])
@login_required
def save_marketplace_credentials():
    """Save marketplace credentials"""
    try:
        data = request.json
        platform = data.get('platform')
        username = data.get('username')
        password = data.get('password')

        if not platform:
            return jsonify({'error': 'Platform is required'}), 400

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        # Validate platform
        valid_platforms = ['poshmark', 'depop', 'varagesale', 'mercari', 'ebay', 'facebook', 'nextdoor']
        if platform.lower() not in valid_platforms:
            return jsonify({'error': 'Invalid platform'}), 400

        db.save_marketplace_credentials(current_user.id, platform.lower(), username, password)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/marketplace-credentials/<platform>', methods=['DELETE'])
@login_required
def delete_marketplace_credentials(platform):
    """Delete marketplace credentials"""
    try:
        db.delete_marketplace_credentials(current_user.id, platform.lower())
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',  # Accessible from other devices on network
        port=5000,
        debug=True
    )
