"""
routes_main.py
Main application routes: listings, drafts, notifications, storage, settings
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from pathlib import Path
from functools import wraps
import json


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

@main_bp.route("/api/analyze-card", methods=["POST"])
def api_analyze_card():
    try:
        from src.ai.gemini_classifier import analyze_card
        from src.schema.unified_listing import Photo

        data = request.get_json()
        paths = data.get("photos", [])
        if not paths:
            return jsonify({"error": "No photos provided"}), 400

        photos = [Photo(url="", local_path=p) for p in paths]
        result = analyze_card(photos)

        # Check for API key errors
        if result.get("error"):
            error_msg = result.get("error", "Unknown error")
            if "API" in error_msg or "api_key" in error_msg.lower():
                return jsonify({
                    "error": "AI service not configured. Please check your GEMINI_API_KEY environment variable.",
                    "details": error_msg
                }), 503
            return jsonify(result), 500

        return jsonify({"success": True, "card_data": result})

    except ValueError as e:
        # Catch API key not set errors
        error_msg = str(e)
        if "API_KEY" in error_msg:
            return jsonify({
                "error": "AI service not configured. Please set GEMINI_API_KEY environment variable.",
                "details": error_msg
            }), 503
        return jsonify({"error": error_msg}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# GENERAL AI ANALYZE (Gemini -> Claude deep analysis)
# -------------------------------------------------------------------------


@main_bp.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Analyze item photos using Gemini (fast) and optionally Claude for deep collectible analysis."""
    try:
        from src.ai.gemini_classifier import GeminiClassifier
        from src.ai.claude_collectible_analyzer import ClaudeCollectibleAnalyzer
        from src.schema.unified_listing import Photo

        data = request.get_json() or {}
        photo_paths = data.get("photos") or []

        if not photo_paths:
            return jsonify({"error": "No photos provided"}), 400

        photos = [Photo(url="", local_path=p) for p in photo_paths]

        # Run fast classification
        try:
            classifier = GeminiClassifier()
            analysis = classifier.analyze_item(photos)
        except ValueError as e:
            # Handle missing API key
            error_msg = str(e)
            if "API_KEY" in error_msg:
                return jsonify({
                    "error": "AI service not configured. Please set GEMINI_API_KEY environment variable.",
                    "details": error_msg
                }), 503
            return jsonify({"error": f"Analyzer init failed: {e}"}), 500
        except Exception as e:
            return jsonify({"error": f"Analyzer init failed: {e}"}), 500

        # Check if analysis returned an error
        if analysis.get("error"):
            error_msg = analysis.get("error", "Unknown error")
            # Check for rate limit errors
            if analysis.get("error_type") == "rate_limit":
                return jsonify({
                    "success": False,
                    "error": error_msg,
                    "retry_after": analysis.get("retry_after", 60)
                }), 429
            # Other errors
            return jsonify({"success": False, "error": error_msg}), 500

        # If it's marked collectible OR force_enhanced is requested, run deep Claude analysis
        collectible_analysis = None
        force_enhanced = data.get("force_enhanced", False)

        if analysis.get("collectible") or force_enhanced:
            try:
                from src.database.db import get_db_instance
                db = get_db_instance()
                claude = ClaudeCollectibleAnalyzer.from_env()
                collectible_analysis = claude.deep_analyze_collectible(photos, analysis, db)
            except Exception as e:
                # Don't fail the whole request for deep analysis errors
                print(f"Enhanced analysis error: {e}")
                collectible_analysis = {"error": str(e)}

        response = {
            "success": True,
            "analysis": analysis,
            "collectible_analysis": collectible_analysis,
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# UPLOAD PHOTOS
# -------------------------------------------------------------------------

@main_bp.route('/api/upload-photos', methods=['POST'])
def api_upload_photos():
    """Upload photos for a listing"""
    try:
        import uuid
        from pathlib import Path
        from werkzeug.utils import secure_filename

        if 'photos' not in request.files:
            return jsonify({"error": "No photos provided"}), 400

        files = request.files.getlist('photos')
        if not files or len(files) == 0:
            return jsonify({"error": "No photos provided"}), 400

        # Create unique directory for this upload
        upload_uuid = str(uuid.uuid4())
        upload_dir = Path('data/draft_photos') / upload_uuid
        upload_dir.mkdir(parents=True, exist_ok=True)

        saved_paths = []
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Add timestamp to prevent collisions
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"

                filepath = upload_dir / filename
                file.save(str(filepath))

                # Return relative path for database storage
                relative_path = f"data/draft_photos/{upload_uuid}/{filename}"
                saved_paths.append(relative_path)

        return jsonify({
            "success": True,
            "paths": saved_paths,
            "count": len(saved_paths)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# EDIT PHOTO
# -------------------------------------------------------------------------

@main_bp.route('/api/edit-photo', methods=['POST'])
def api_edit_photo():
    """Edit photo (crop, remove background, resize)"""
    try:
        import base64
        import io
        from PIL import Image
        from pathlib import Path
        import uuid
        from datetime import datetime

        data = request.get_json()
        image_data = data.get('image')
        operation = data.get('operation')

        if not image_data or not operation:
            return jsonify({"error": "Missing image data or operation"}), 400

        # Parse base64 image
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]

        img_bytes = base64.b64decode(image_data)
        img = Image.open(io.BytesIO(img_bytes))

        # Perform operation
        if operation == 'crop':
            crop_data = data.get('crop', {})
            x = crop_data.get('x', 0)
            y = crop_data.get('y', 0)
            width = crop_data.get('width', img.width)
            height = crop_data.get('height', img.height)

            img = img.crop((x, y, x + width, y + height))

        elif operation == 'resize':
            new_width = int(data.get('width', img.width))
            new_height = int(data.get('height', img.height))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        elif operation == 'remove-bg':
            try:
                from rembg import remove
                img_bytes_io = io.BytesIO()
                img.save(img_bytes_io, format='PNG')
                img_bytes_io.seek(0)
                output = remove(img_bytes_io.read())
                img = Image.open(io.BytesIO(output))
            except ImportError:
                return jsonify({"error": "Background removal not available (rembg not installed)"}), 501
            except Exception as e:
                return jsonify({"error": f"Background removal failed: {str(e)}"}), 500

        # Save edited image
        upload_dir = Path('data/draft_photos') / 'edited'
        upload_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"edited_{timestamp}_{uuid.uuid4().hex[:8]}.png"
        filepath = upload_dir / filename

        img.save(str(filepath), 'PNG')

        # Convert to base64 for preview
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()

        return jsonify({
            "success": True,
            "image": f"data:image/png;base64,{img_base64}",
            "filepath": f"data/draft_photos/edited/{filename}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# GET DRAFT
# -------------------------------------------------------------------------

@main_bp.route('/api/get-draft/<int:draft_id>', methods=['GET'])
@login_required
def api_get_draft(draft_id):
    """Get draft details for editing"""
    try:
        listing = db.get_listing(draft_id)

        if not listing:
            return jsonify({"error": "Draft not found"}), 404

        if listing['user_id'] != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        return jsonify({
            "success": True,
            "listing": listing
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# SAVE DRAFT / CREATE LISTING
# -------------------------------------------------------------------------


@main_bp.route('/api/save-draft', methods=['POST'])
@login_required
def api_save_draft():
    """Save a listing as draft or post it (status). Expects JSON with form fields and `photos` array."""
    try:
        import uuid
        data = request.get_json() or {}

        # Required fields
        title = data.get('title') or 'Untitled'
        price = float(data.get('price') or 0)
        condition = data.get('condition') or 'good'
        status = data.get('status', 'draft')
        photos = data.get('photos') or []

        # Optional fields
        description = data.get('description')
        cost = float(data.get('cost')) if data.get('cost') else None
        item_type = data.get('item_type')
        attributes = {
            'brand': data.get('brand'),
            'size': data.get('size'),
            'color': data.get('color')
        }
        quantity = int(data.get('quantity') or 1)
        storage_location = data.get('storage_location')
        sku = data.get('sku')
        upc = data.get('upc')

        # If editing an existing draft, remove it first (simple replace semantics)
        draft_id = data.get('draft_id')
        if draft_id:
            try:
                db.delete_listing(int(draft_id))
            except Exception:
                pass

        listing_uuid = data.get('listing_uuid') or str(uuid.uuid4())

        # Create listing in DB
        listing_id = db.create_listing(
            listing_uuid=listing_uuid,
            title=title,
            description=description,
            price=price,
            condition=condition,
            photos=photos,
            user_id=current_user.id,
            cost=cost,
            category=item_type,
            attributes=attributes,
            quantity=quantity,
            storage_location=storage_location,
            sku=sku,
            upc=upc,
            status=status,
        )

        return jsonify({"success": True, "listing_id": listing_id})

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


# -------------------------------------------------------------------------
# STORAGE API ENDPOINTS
# -------------------------------------------------------------------------

@main_bp.route('/api/storage/bins', methods=['GET'])
@login_required
def api_get_storage_bins():
    """Get all storage bins for the current user"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        bin_type = request.args.get('type')  # 'clothing' or 'cards'
        bins = db.get_storage_bins(current_user.id, bin_type)

        # Get section counts for each bin
        for bin in bins:
            sections = db.get_storage_sections(bin['id'])
            bin['section_count'] = len(sections)
            bin['sections'] = sections

        return jsonify({
            "success": True,
            "bins": bins
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/storage/create-bin', methods=['POST'])
@login_required
def api_create_storage_bin():
    """Create a new storage bin"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        data = request.get_json()
        bin_name = data.get('bin_name')
        bin_type = data.get('bin_type')  # 'clothing' or 'cards'
        description = data.get('description', '')

        if not bin_name or not bin_type:
            return jsonify({"error": "bin_name and bin_type are required"}), 400

        bin_id = db.create_storage_bin(
            user_id=current_user.id,
            bin_name=bin_name,
            bin_type=bin_type,
            description=description
        )

        return jsonify({
            "success": True,
            "bin_id": bin_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/storage/create-section', methods=['POST'])
@login_required
def api_create_storage_section():
    """Create a new section within a bin"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        data = request.get_json()
        bin_id = data.get('bin_id')
        section_name = data.get('section_name')
        capacity = data.get('capacity')

        if not bin_id or not section_name:
            return jsonify({"error": "bin_id and section_name are required"}), 400

        # Verify the bin belongs to the current user
        bins = db.get_storage_bins(current_user.id)
        if not any(b['id'] == bin_id for b in bins):
            return jsonify({"error": "Bin not found or unauthorized"}), 403

        section_id = db.create_storage_section(
            bin_id=bin_id,
            section_name=section_name,
            capacity=capacity
        )

        return jsonify({
            "success": True,
            "section_id": section_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/storage/items', methods=['GET'])
@login_required
def api_get_storage_items():
    """Get storage items, optionally filtered by bin"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        bin_id = request.args.get('bin_id', type=int)

        if bin_id:
            # Verify the bin belongs to the current user
            bins = db.get_storage_bins(current_user.id)
            if not any(b['id'] == bin_id for b in bins):
                return jsonify({"error": "Bin not found or unauthorized"}), 403

            items = db.get_storage_items(current_user.id, bin_id=bin_id)
        else:
            items = db.get_storage_items(current_user.id)

        return jsonify({
            "success": True,
            "items": items
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/storage/add-item', methods=['POST'])
@login_required
def api_add_storage_item():
    """Add a new item to storage"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        data = request.get_json()
        bin_id = data.get('bin_id')
        section_id = data.get('section_id')
        item_type = data.get('item_type')
        category = data.get('category')
        title = data.get('title')
        description = data.get('description')
        notes = data.get('notes')

        if not bin_id:
            return jsonify({"error": "bin_id is required"}), 400

        # Verify the bin belongs to the current user
        bins = db.get_storage_bins(current_user.id)
        bin_obj = next((b for b in bins if b['id'] == bin_id), None)
        if not bin_obj:
            return jsonify({"error": "Bin not found or unauthorized"}), 403

        # Get section name if section_id provided
        section_name = None
        if section_id:
            sections = db.get_storage_sections(bin_id)
            section_obj = next((s for s in sections if s['id'] == section_id), None)
            if section_obj:
                section_name = section_obj['section_name']

        # Generate storage ID
        storage_id = db.generate_storage_id(
            user_id=current_user.id,
            bin_name=bin_obj['bin_name'],
            section_name=section_name,
            category=category
        )

        # Add the item
        item_id = db.add_storage_item(
            user_id=current_user.id,
            storage_id=storage_id,
            bin_id=bin_id,
            section_id=section_id,
            item_type=item_type,
            category=category,
            title=title,
            description=description,
            notes=notes
        )

        return jsonify({
            "success": True,
            "item_id": item_id,
            "storage_id": storage_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/storage/find', methods=['GET'])
@login_required
def api_find_storage_item():
    """Find an item by storage ID"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        storage_id = request.args.get('storage_id')

        if not storage_id:
            return jsonify({"error": "storage_id is required"}), 400

        item = db.find_storage_item(current_user.id, storage_id)

        if item:
            return jsonify({
                "success": True,
                "item": item
            })
        else:
            return jsonify({
                "success": False,
                "error": "Item not found"
            }), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------------
# SETTINGS API ENDPOINTS
# -------------------------------------------------------------------------

@main_bp.route('/api/settings/notification-email', methods=['POST'])
@login_required
def api_update_notification_email():
    """Update notification email"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        data = request.get_json()
        email = data.get('notification_email')

        if not email:
            return jsonify({"error": "notification_email is required"}), 400

        cursor = db._get_cursor()
        cursor.execute("""
            UPDATE users
            SET notification_email = %s
            WHERE id = %s
        """, (email, current_user.id))
        db.conn.commit()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/settings/marketplace-credentials', methods=['POST'])
@login_required
def api_save_marketplace_credentials():
    """Save marketplace credentials"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        data = request.get_json()
        platform = data.get('platform')
        username = data.get('username')
        password = data.get('password')

        if not platform or not username or not password:
            return jsonify({"error": "platform, username, and password are required"}), 400

        cursor = db._get_cursor()
        cursor.execute("""
            INSERT INTO marketplace_credentials (user_id, platform, username, password)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, platform)
            DO UPDATE SET username = %s, password = %s, updated_at = CURRENT_TIMESTAMP
        """, (current_user.id, platform, username, password, username, password))
        db.conn.commit()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/settings/marketplace-credentials/<platform>', methods=['DELETE'])
@login_required
def api_delete_marketplace_credentials(platform):
    """Delete marketplace credentials"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        cursor = db._get_cursor()
        cursor.execute("""
            DELETE FROM marketplace_credentials
            WHERE user_id = %s AND platform = %s
        """, (current_user.id, platform))
        db.conn.commit()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/settings/api-credentials', methods=['POST'])
@login_required
def api_save_api_credentials():
    """Save API credentials for automated platforms"""
    try:
        from src.database.db import get_db_instance
        import json
        db = get_db_instance()

        data = request.get_json()
        platform = data.get('platform')
        credentials = data.get('credentials')

        if not platform or not credentials:
            return jsonify({"error": "platform and credentials are required"}), 400

        cursor = db._get_cursor()
        cursor.execute("""
            INSERT INTO api_credentials (user_id, platform, credentials)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, platform)
            DO UPDATE SET credentials = %s, updated_at = CURRENT_TIMESTAMP
        """, (current_user.id, platform, json.dumps(credentials), json.dumps(credentials)))
        db.conn.commit()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
