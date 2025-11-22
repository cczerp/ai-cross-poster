"""
routes_main.py
Main application routes: listings, drafts, notifications, storage, settings
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from pathlib import Path
from functools import wraps
import json
import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
import io


# Create blueprint
main_bp = Blueprint('main', __name__)

# db will be set by init_routes() in web_app.py
db = None

def init_routes(database):
    """Initialize routes with database"""
    global db
    db = database


# ============================================================================
# ADMIN DECORATOR
# ============================================================================

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        from flask import redirect, url_for, flash
        if not current_user.is_admin:
            flash('You need administrator privileges to access this page.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------------------------------------------------
# DELETE DRAFT
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# PHOTO UPLOAD API ENDPOINTS
# -------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'heic'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compress_image(image_file, max_size_mb=2, quality=85):
    """Compress image to reduce file size"""
    try:
        # Read image
        img = Image.open(image_file)

        # Convert RGBA to RGB if needed
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Resize if too large (max 2048px on longest side)
        max_dimension = 2048
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Save compressed image to bytes
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)

        # If still too large, reduce quality
        if len(output.getvalue()) > max_size_mb * 1024 * 1024 and quality > 60:
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=60, optimize=True)
            output.seek(0)

        return output, 'jpg'
    except Exception as e:
        print(f"Compression error: {e}")
        # Return original if compression fails
        image_file.seek(0)
        return image_file, image_file.filename.rsplit('.', 1)[1].lower()


@main_bp.route("/api/upload-photos", methods=["POST"])
@login_required
def api_upload_photos():
    """Handle photo uploads for listings with compression"""
    try:
        if 'photos' not in request.files:
            return jsonify({"error": "No photos provided"}), 400

        files = request.files.getlist('photos')
        if not files or files[0].filename == '':
            return jsonify({"error": "No files selected"}), 400

        # Create uploads directory if it doesn't exist
        upload_dir = Path('./data/uploads')
        upload_dir.mkdir(parents=True, exist_ok=True)

        uploaded_paths = []
        for file in files:
            if file and allowed_file(file.filename):
                # Compress image before saving
                compressed_file, ext = compress_image(file)

                # Generate unique filename
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = upload_dir / filename

                # Save compressed file
                with open(filepath, 'wb') as f:
                    f.write(compressed_file.read())

                # Return web-accessible path
                uploaded_paths.append(f"/uploads/{filename}")

        if not uploaded_paths:
            return jsonify({"error": "No valid images uploaded"}), 400

        return jsonify({
            "success": True,
            "paths": uploaded_paths,
            "count": len(uploaded_paths)
        })

    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/uploads/<filename>")
def serve_upload(filename):
    """Serve uploaded files"""
    try:
        from flask import send_from_directory
        upload_dir = Path('./data/uploads')
        return send_from_directory(upload_dir, filename)
    except Exception as e:
        return jsonify({"error": "File not found"}), 404


@main_bp.route("/api/edit-photo", methods=["POST"])
@login_required
def api_edit_photo():
    """Handle photo editing (crop, resize, background removal)"""
    try:
        data = request.json
        operation = data.get('operation')
        image_path = data.get('image')

        if not operation or not image_path:
            return jsonify({"error": "Missing parameters"}), 400

        # Extract filename from path (e.g., "/uploads/abc123.jpg" -> "abc123.jpg")
        filename = image_path.split('/')[-1]
        upload_dir = Path('./data/uploads')
        filepath = upload_dir / filename

        if not filepath.exists():
            return jsonify({"error": "Image file not found"}), 404

        # Open the image
        img = Image.open(filepath)

        # Handle different operations
        if operation == 'crop':
            # Get crop parameters
            crop_data = data.get('cropData', {})
            x = int(crop_data.get('x', 0))
            y = int(crop_data.get('y', 0))
            width = int(crop_data.get('width', img.width))
            height = int(crop_data.get('height', img.height))

            # Crop the image
            img = img.crop((x, y, x + width, y + height))

        elif operation == 'resize':
            # Get resize parameters (e.g., 2x = enlarge by 2x)
            scale = data.get('scale', 2.0)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        elif operation == 'remove-bg':
            # Background removal using simple thresholding
            # For better results, you could integrate rembg library
            # This is a basic implementation
            try:
                # Try to import rembg if available
                from rembg import remove
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                result = remove(img_bytes.read())
                img = Image.open(io.BytesIO(result))
            except ImportError:
                # Fallback: convert to RGBA and make white background transparent
                img = img.convert('RGBA')
                data_img = img.getdata()
                new_data = []
                for item in data_img:
                    # Change white (also shades of whites) to transparent
                    if item[0] > 200 and item[1] > 200 and item[2] > 200:
                        new_data.append((255, 255, 255, 0))
                    else:
                        new_data.append(item)
                img.putdata(new_data)

        else:
            return jsonify({"error": f"Unknown operation: {operation}"}), 400

        # Save edited image (create new file to preserve original)
        new_filename = f"{uuid.uuid4().hex}.{'png' if operation == 'remove-bg' else 'jpg'}"
        new_filepath = upload_dir / new_filename

        if operation == 'remove-bg':
            img.save(new_filepath, format='PNG')
        else:
            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            img.save(new_filepath, format='JPEG', quality=85, optimize=True)

        return jsonify({
            "success": True,
            "filepath": f"/uploads/{new_filename}",
            "message": f"Photo {operation} completed successfully"
        })

    except Exception as e:
        print(f"Photo editing error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# STORAGE API ENDPOINTS
# -------------------------------------------------------------------------

@main_bp.route("/api/storage/find", methods=["GET"])
@login_required
def api_find_storage_item():
    """Find a storage item by ID"""
    try:
        storage_id = request.args.get("storage_id", "").strip()
        if not storage_id:
            return jsonify({"error": "Storage ID required"}), 400

        item = db.find_storage_item(current_user.id, storage_id)

        if item:
            return jsonify({"success": True, "item": item})
        else:
            return jsonify({"success": False, "error": "Item not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/save-draft", methods=["POST"])
@login_required
def api_save_draft():
    """Save or update a draft listing"""
    try:
        data = request.json

        # Extract form data with safe type conversions
        title = data.get('title', 'Untitled')
        description = data.get('description', '')

        # Safe float conversion for price
        try:
            price_val = data.get('price', '0')
            price = float(price_val) if price_val not in [None, ''] else 0.0
        except (ValueError, TypeError):
            price = 0.0

        # Safe float conversion for cost
        try:
            cost_val = data.get('cost', '')
            cost = float(cost_val) if cost_val not in [None, ''] else None
        except (ValueError, TypeError):
            cost = None

        condition = data.get('condition', 'good')
        item_type = data.get('item_type', 'general')

        # Safe int conversion for quantity
        try:
            quantity_val = data.get('quantity', '1')
            quantity = int(quantity_val) if quantity_val not in [None, ''] else 1
        except (ValueError, TypeError):
            quantity = 1

        storage_location = data.get('storage_location', '')
        sku = data.get('sku', '')
        upc = data.get('upc', '')
        status = data.get('status', 'draft')

        # Get photos array (should already be web paths like "/uploads/abc123.jpg")
        photos = data.get('photos', [])

        # Build attributes from additional fields
        attributes = {
            'brand': data.get('brand', ''),
            'size': data.get('size', ''),
            'color': data.get('color', ''),
            'shipping_cost': data.get('shipping_cost', 0)
        }

        # Check if we're updating an existing draft
        draft_id = data.get('draft_id')
        listing_uuid = data.get('listing_uuid')

        if draft_id:
            # Update existing draft
            db.update_listing(
                listing_id=draft_id,
                title=title,
                description=description,
                price=price,
                cost=cost,
                condition=condition,
                item_type=item_type,
                attributes=attributes,
                photos=photos,
                quantity=quantity,
                storage_location=storage_location,
                sku=sku,
                upc=upc,
                status=status
            )
            return jsonify({
                "success": True,
                "listing_id": draft_id,
                "listing_uuid": listing_uuid,
                "message": "Draft updated successfully"
            })
        else:
            # Create new draft
            listing_uuid = uuid.uuid4().hex
            listing_id = db.create_listing(
                listing_uuid=listing_uuid,
                user_id=current_user.id,
                title=title,
                description=description,
                price=price,
                cost=cost,
                condition=condition,
                item_type=item_type,
                attributes=attributes,
                photos=photos,
                quantity=quantity,
                storage_location=storage_location,
                sku=sku,
                upc=upc,
                status=status
            )
            return jsonify({
                "success": True,
                "listing_id": listing_id,
                "listing_uuid": listing_uuid,
                "message": "Draft saved successfully"
            })

    except Exception as e:
        print(f"Save draft error: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/get-draft/<int:listing_id>", methods=["GET"])
@login_required
def api_get_draft(listing_id):
    """Retrieve a draft listing for editing"""
    try:
        listing = db.get_listing(listing_id)

        if not listing:
            return jsonify({"error": "Draft not found"}), 404

        if listing["user_id"] != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        # Parse JSON fields
        if listing.get('photos'):
            if isinstance(listing['photos'], str):
                listing['photos'] = json.loads(listing['photos'])
        else:
            listing['photos'] = []

        if listing.get('attributes'):
            if isinstance(listing['attributes'], str):
                attributes = json.loads(listing['attributes'])
            else:
                attributes = listing['attributes']

            # Merge attributes into main listing object for frontend
            listing['brand'] = attributes.get('brand', '')
            listing['size'] = attributes.get('size', '')
            listing['color'] = attributes.get('color', '')
            listing['shipping_cost'] = attributes.get('shipping_cost', 0)
        else:
            listing['brand'] = ''
            listing['size'] = ''
            listing['color'] = ''
            listing['shipping_cost'] = 0

        return jsonify({
            "success": True,
            "listing": listing
        })

    except Exception as e:
        print(f"Get draft error: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/delete-draft/<int:listing_id>", methods=["DELETE"])
@login_required
def delete_draft(listing_id):
    """Delete a draft and all stored photos."""
    try:
        listing = db.get_listing(listing_id)
        if not listing:
            return jsonify({"error": "Listing not found"}), 404
        if listing["user_id"] != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        # Remove photos directory
        try:
            import shutil
            if listing.get("listing_uuid"):
                photo_dir = Path("data/draft_photos") / listing["listing_uuid"]
                if photo_dir.exists():
                    shutil.rmtree(photo_dir)
        except Exception:
            pass  # Not fatal

        db.delete_listing(listing_id)
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# USER SETTINGS — NOTIFICATION EMAIL
# -------------------------------------------------------------------------

@main_bp.route("/api/settings/notification-email", methods=["POST"])
@login_required
def update_notification_email():
    try:
        data = request.json
        email = data.get("notification_email")
        if not email:
            return jsonify({"error": "Notification email required"}), 400

        db.update_notification_email(current_user.id, email)
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# MARKETPLACE CREDENTIALS CRUD
# -------------------------------------------------------------------------

VALID_MARKETPLATFORMS = [
    "etsy", "poshmark", "depop", "offerup", "shopify", "craigslist",
    "facebook", "tiktok_shop", "woocommerce", "nextdoor", "varagesale",
    "ruby_lane", "ecrater", "bonanza", "kijiji", "personal_website",
    "grailed", "vinted", "mercado_libre", "tradesy", "vestiaire",
    "rebag", "thredup", "poshmark_ca", "other"
]


@main_bp.route("/api/settings/marketplace-credentials", methods=["POST"])
@login_required
def save_marketplace_credentials():
    try:
        data = request.json
        platform = data.get("platform", "").lower()
        username = data.get("username")
        password = data.get("password")

        if platform not in VALID_MARKETPLATFORMS:
            return jsonify({"error": "Invalid platform"}), 400
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        db.save_marketplace_credentials(
            current_user.id, platform, username, password
        )
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/settings/marketplace-credentials/<platform>", methods=["DELETE"])
@login_required
def delete_marketplace_credentials(platform):
    try:
        platform = platform.lower()
        db.delete_marketplace_credentials(current_user.id, platform)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# API CREDENTIALS CRUD (Etsy/Shopify/WooCommerce/Facebook)
# -------------------------------------------------------------------------

VALID_API_PLATFORMS = ["etsy", "shopify", "woocommerce", "facebook"]


@main_bp.route("/api/settings/api-credentials", methods=["POST"])
@login_required
def save_api_credentials():
    try:
        data = request.json
        platform = data.get("platform", "").lower()
        credentials = data.get("credentials")

        if platform not in VALID_API_PLATFORMS:
            return jsonify({"error": "Invalid API platform"}), 400
        if not credentials:
            return jsonify({"error": "Credentials required"}), 400

        db.save_marketplace_credentials(
            current_user.id,
            f"api_{platform}",
            "api_token",
            json.dumps(credentials)
        )

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/settings/api-credentials/<platform>", methods=["GET"])
@login_required
def get_api_credentials(platform):
    try:
        platform = platform.lower()
        creds = db.get_marketplace_credentials(
            current_user.id, f"api_{platform}"
        )

        if creds and creds.get("password"):
            return jsonify({
                "success": True,
                "configured": True,
                "credentials": json.loads(creds["password"])
            })

        return jsonify({"success": True, "configured": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# BABY BIRD — KNOWLEDGE DISTILLATION API
# -------------------------------------------------------------------------

@main_bp.route("/api/baby-bird/status", methods=["GET"])
@login_required
def baby_bird_status():
    try:
        from src.ai.knowledge_distillation import get_baby_bird_status
        return jsonify(get_baby_bird_status(db))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/baby-bird/export", methods=["POST"])
@admin_required
def baby_bird_export():
    try:
        path = request.json.get("output_path", "./data/training_dataset.jsonl")
        count = db.export_training_dataset(path, format="jsonl")
        return jsonify({
            "success": True,
            "sample_count": count,
            "output_path": path,
            "message": f"Exported {count} training samples!"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# CARD COLLECTION DASHBOARD
# -------------------------------------------------------------------------

@main_bp.route("/cards")
@login_required
def cards_collection():
    return render_template("cards.html")


# -------------------------------------------------------------------------
# CARD ANALYSIS (TCG + Sports)
# -------------------------------------------------------------------------

@main_bp.route("/api/analyze", methods=["POST"])
@login_required
def api_analyze():
    """Analyze general items (non-cards) with AI"""
    try:
        from src.ai.gemini_classifier import GeminiClassifier
        from src.schema.unified_listing import Photo

        data = request.get_json()
        paths = data.get("photos", [])
        if not paths:
            return jsonify({"error": "No photos provided"}), 400

        photos = [Photo(local_path=p) for p in paths]
        classifier = GeminiClassifier.from_env()
        result = classifier.analyze_item(photos)

        if result.get("error"):
            return jsonify(result), 500

        return jsonify({"success": True, "analysis": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/analyze-card", methods=["POST"])
@login_required
def api_analyze_card():
    try:
        from src.ai.gemini_classifier import analyze_card
        from src.schema.unified_listing import Photo

        data = request.get_json()
        paths = data.get("photos", [])
        if not paths:
            return jsonify({"error": "No photos provided"}), 400

        photos = [Photo(local_path=p) for p in paths]
        result = analyze_card(photos)

        if result.get("error"):
            return jsonify(result), 500

        return jsonify({"success": True, "card_data": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# ADD CARD (AI or Manual)
# -------------------------------------------------------------------------

@main_bp.route("/api/cards/add", methods=["POST"])
@login_required
def api_add_card():
    try:
        from src.cards import add_card_to_collection, CardCollectionManager, UnifiedCard

        data = request.get_json()

        # AI path
        if data.get("ai_result"):
            card_id = add_card_to_collection(
                data["ai_result"],
                current_user.id,
                photos=data.get("photos", []),
                storage_location=data.get("storage_location")
            )
            if not card_id:
                return jsonify({"error": "Invalid card"}), 400

            return jsonify({"success": True, "card_id": card_id})

        # Manual path
        manager = CardCollectionManager()
        entry = data.get("manual_entry", data)

        card = UnifiedCard(
            user_id=current_user.id,
            card_type=entry.get("card_type", "unknown"),
            title=entry.get("title", "Unknown Card"),
            card_number=entry.get("card_number"),
            quantity=entry.get("quantity", 1),
            organization_mode=entry.get("organization_mode", "by_set"),

            # TCG
            game_name=entry.get("game_name"),
            set_name=entry.get("set_name"),
            set_code=entry.get("set_code"),
            rarity=entry.get("rarity"),

            # Sports
            sport=entry.get("sport"),
            year=entry.get("year"),
            brand=entry.get("brand"),
            series=entry.get("series"),
            player_name=entry.get("player_name"),
            is_rookie_card=entry.get("is_rookie_card", False),

            # Grading
            grading_company=entry.get("grading_company"),
            grading_score=entry.get("grading_score"),

            # Other
            estimated_value=entry.get("estimated_value"),
            storage_location=entry.get("storage_location"),
            photos=entry.get("photos", []),
            notes=entry.get("notes")
        )

        card_id = manager.add_card(card)
        return jsonify({"success": True, "card_id": card_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# LIST CARDS
# -------------------------------------------------------------------------

@main_bp.route("/api/cards/list", methods=["GET"])
@login_required
def api_list_cards():
    try:
        from src.cards import CardCollectionManager

        manager = CardCollectionManager()

        cards = manager.get_user_cards(
            current_user.id,
            card_type=request.args.get("card_type"),
            organization_mode=request.args.get("organization_mode"),
            limit=int(request.args.get("limit", 100)),
            offset=int(request.args.get("offset", 0))
        )

        return jsonify({
            "success": True,
            "cards": [c.to_dict() for c in cards],
            "count": len(cards)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# ORGANIZED CARD GROUPS
# -------------------------------------------------------------------------

@main_bp.route("/api/cards/organized", methods=["GET"])
@login_required
def api_get_organized_cards():
    try:
        from src.cards import CardCollectionManager

        manager = CardCollectionManager()

        mode = request.args.get("organization_mode")
        card_type = request.args.get("card_type")

        if not mode:
            return jsonify({"error": "organization_mode required"}), 400

        groups = manager.get_cards_by_organization(
            current_user.id, mode, card_type=card_type
        )

        return jsonify({
            "success": True,
            "organized": {
                category: [card.to_dict() for card in cards]
                for category, cards in groups.items()
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# CARD SEARCH
# -------------------------------------------------------------------------

@main_bp.route("/api/cards/search", methods=["GET"])
@login_required
def api_search_cards():
    try:
        from src.cards import CardCollectionManager

        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"error": "Search query required"}), 400

        manager = CardCollectionManager()
        cards = manager.search_cards(
            current_user.id,
            query=query,
            card_type=request.args.get("card_type")
        )

        return jsonify({
            "success": True,
            "cards": [c.to_dict() for c in cards]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# EXPORT CARDS CSV
# -------------------------------------------------------------------------

@main_bp.route("/api/cards/export", methods=["GET"])
@login_required
def api_export_cards():
    try:
        from src.cards import CardCollectionManager
        from flask import make_response

        manager = CardCollectionManager()
        csv_data = manager.export_to_csv(
            current_user.id,
            card_type=request.args.get("card_type"),
            organization_mode=request.args.get("organization_mode")
        )

        if not csv_data:
            return jsonify({"error": "No cards to export"}), 404

        response = make_response(csv_data)
        response.headers["Content-Type"] = "text/csv"
        response.headers["Content-Disposition"] = "attachment; filename=card_collection.csv"
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# IMPORT CARDS CSV
# -------------------------------------------------------------------------

@main_bp.route("/api/cards/import", methods=["POST"])
@login_required
def api_import_cards():
    try:
        from src.cards import CardCollectionManager

        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "No file selected"}), 400

        csv_content = file.read().decode("utf-8")
        manager = CardCollectionManager()

        result = manager.import_from_csv(
            current_user.id,
            csv_content,
            card_type=request.form.get("card_type")
        )

        return jsonify({
            "success": True,
            "imported": result["imported"],
            "errors": result["errors"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# SWITCH ORGANIZATION MODE
# -------------------------------------------------------------------------

@main_bp.route("/api/cards/switch-organization", methods=["POST"])
@login_required
def api_switch_organization():
    try:
        from src.cards import CardCollectionManager

        data = request.json
        new_mode = data.get("new_mode")
        card_type = data.get("card_type")

        valid = [
            "by_set", "by_year", "by_sport", "by_brand", "by_game",
            "by_rarity", "by_number", "by_grading",
            "by_value", "by_binder", "custom"
        ]

        if new_mode not in valid:
            return jsonify({
                "error": f"Invalid mode. Valid: {', '.join(valid)}"
            }), 400

        manager = CardCollectionManager()
        manager.switch_organization_mode(
            current_user.id, new_mode, card_type=card_type
        )

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# CARD STATS
# -------------------------------------------------------------------------

@main_bp.route("/api/cards/stats", methods=["GET"])
@login_required
def api_card_stats():
    try:
        from src.cards import CardCollectionManager
        stats = CardCollectionManager().get_collection_stats(current_user.id)
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# GET CARD BY ID
# -------------------------------------------------------------------------

@main_bp.route("/api/cards/<int:card_id>", methods=["GET"])
@login_required
def api_get_card(card_id):
    try:
        from src.cards import CardCollectionManager
        manager = CardCollectionManager()

        card = manager.get_card(card_id)
        if not card:
            return jsonify({"error": "Card not found"}), 404
        if card.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        return jsonify({"success": True, "card": card.to_dict()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# UPDATE CARD
# -------------------------------------------------------------------------

@main_bp.route("/api/cards/<int:card_id>", methods=["PUT"])
@login_required
def api_update_card(card_id):
    try:
        from src.cards import CardCollectionManager
        manager = CardCollectionManager()

        card = manager.get_card(card_id)
        if not card:
            return jsonify({"error": "Card not found"}), 404
        if card.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        data = request.get_json()

        # Update fields
        for field in [
            "title", "quantity", "storage_location", "notes",
            "estimated_value", "grading_company", "grading_score"
        ]:
            if field in data:
                setattr(card, field, data[field])

        manager.update_card(card_id, card)

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# DELETE CARD
# -------------------------------------------------------------------------

@main_bp.route("/api/cards/<int:card_id>", methods=["DELETE"])
@login_required
def api_delete_card(card_id):
    try:
        from src.cards import CardCollectionManager
        manager = CardCollectionManager()

        card = manager.get_card(card_id)
        if not card:
            return jsonify({"error": "Card not found"}), 404
        if card.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        manager.delete_card(card_id)
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
