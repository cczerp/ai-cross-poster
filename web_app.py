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
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from src.schema import UnifiedListing, Photo, Price, ListingCondition, Shipping, ItemSpecifics
from src.sync import MultiPlatformSyncManager
from src.database import get_db
from src.notifications import NotificationManager

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
sync_manager = None
notification_manager = None

try:
    sync_manager = MultiPlatformSyncManager.from_env()
    notification_manager = NotificationManager.from_env()
except Exception as e:
    print(f"Warning: Service initialization issue: {e}")


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/create')
def create_listing():
    """Create new listing page"""
    return render_template('create.html')


@app.route('/drafts')
def drafts():
    """View saved drafts"""
    drafts_list = db.get_drafts(limit=100)
    return render_template('drafts.html', drafts=drafts_list)


@app.route('/listings')
def listings():
    """View active listings"""
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT l.*, GROUP_CONCAT(pl.platform || ':' || pl.status) as platform_statuses
        FROM listings l
        LEFT JOIN platform_listings pl ON l.id = pl.listing_id
        WHERE l.status != 'draft'
        GROUP BY l.id
        ORDER BY l.created_at DESC
        LIMIT 50
    """)
    listings_list = [dict(row) for row in cursor.fetchall()]
    return render_template('listings.html', listings=listings_list)


@app.route('/notifications')
def notifications():
    """View notifications"""
    if notification_manager:
        notifs = notification_manager.get_recent_notifications(limit=50)
    else:
        notifs = []
    return render_template('notifications.html', notifications=notifs)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/upload-photos', methods=['POST'])
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


@app.route('/api/post-listing', methods=['POST'])
def post_listing():
    """Post listing to platforms"""
    data = request.json
    photo_paths = session.get('photo_paths', [])

    if not photo_paths:
        return jsonify({'error': 'No photos uploaded'}), 400

    if not sync_manager:
        return jsonify({'error': 'Sync manager not initialized'}), 500

    try:
        # Create photo objects
        photo_objects = [
            Photo(url="", local_path=p, order=i, is_primary=(i == 0))
            for i, p in enumerate(photo_paths)
        ]

        # Create listing
        listing = UnifiedListing(
            title=data.get('title', 'Untitled'),
            description=data.get('description', ''),
            price=Price(amount=float(data.get('price', 0))),
            condition=ListingCondition(data.get('condition', 'good')),
            photos=photo_objects,
            item_specifics=ItemSpecifics(
                brand=data.get('brand'),
                size=data.get('size'),
                color=data.get('color'),
            ),
            shipping=Shipping(
                cost=float(data.get('shipping_cost', 0))
            ),
            quantity=int(data.get('quantity', 1)),
            location=data.get('storage_location'),
        )

        # Get selected platforms
        platforms = data.get('platforms', ['ebay', 'mercari'])

        # Post to platforms
        result = sync_manager.post_to_all_platforms(
            listing,
            platforms=platforms,
            cost=float(data.get('cost')) if data.get('cost') else None,
        )

        # Clear session
        session.pop('photo_paths', None)

        return jsonify({
            'success': True,
            'listing_id': result['listing_id'],
            'results': {k: {'success': v.success, 'error': v.error} for k, v in result['results'].items()}
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mark-sold', methods=['POST'])
def mark_sold():
    """Mark listing as sold"""
    data = request.json

    if not sync_manager:
        return jsonify({'error': 'Sync manager not initialized'}), 500

    try:
        result = sync_manager.mark_sold(
            listing_id=int(data['listing_id']),
            sold_platform=data['platform'],
            sold_price=float(data.get('sold_price')) if data.get('sold_price') else None,
            quantity_sold=int(data.get('quantity_sold', 1)),
        )

        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-draft/<int:listing_id>', methods=['DELETE'])
def delete_draft(listing_id):
    """Delete a draft"""
    try:
        listing = db.get_listing(listing_id)

        if listing:
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
