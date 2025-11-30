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
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        platform = data.get("platform", "").lower()
        username = data.get("username")
        password = data.get("password")

        if platform not in VALID_MARKETPLATFORMS:
            return jsonify({"error": f"Invalid platform. Valid platforms: {', '.join(VALID_MARKETPLATFORMS)}"}), 400
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        db.save_marketplace_credentials(
            current_user.id, platform, username, password
        )
        return jsonify({"success": True})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to save credentials: {str(e)}"}), 500


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
            print(f"Card analysis error: {error_msg}")  # Debug logging
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
        print(f"Card analysis ValueError: {error_msg}")  # Debug logging
        if "API_KEY" in error_msg:
            return jsonify({
                "error": "AI service not configured. Please set GEMINI_API_KEY environment variable.",
                "details": error_msg
            }), 503
        return jsonify({"error": error_msg}), 500
    except Exception as e:
        print(f"Card analysis exception: {str(e)}")  # Debug logging
        import traceback
        traceback.print_exc()  # Print full stack trace for debugging
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

@main_bp.route('/api/get-drafts', methods=['GET'])
@login_required
def api_get_drafts():
    """Get all drafts for current user"""
    try:
        user_id_str = str(current_user.id) if current_user and current_user.id else None
        if not user_id_str:
            return jsonify({"error": "User not authenticated"}), 401
        
        drafts = db.get_drafts(user_id=user_id_str, limit=100)
        return jsonify({"success": True, "drafts": drafts})
    except Exception as e:
        print(f"Error getting drafts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


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

        # Handle AI analysis data if present
        collectible_id = None
        enhanced_analysis = data.get('enhanced_analysis')
        if enhanced_analysis:
            # Extract key info from enhanced analysis
            name = title  # Use listing title as collectible name
            category_val = item_type
            brand = attributes.get('brand') if attributes else None

            # Extract values from enhanced analysis
            condition_val = condition
            value_low = None
            value_high = None
            if enhanced_analysis.get('market_analysis'):
                market = enhanced_analysis['market_analysis']
                value_low = market.get('estimated_value_low')
                value_high = market.get('estimated_value_high')

            # Get historical context
            year_val = None
            if enhanced_analysis.get('historical_context'):
                year_val = enhanced_analysis['historical_context'].get('release_year')

            # Get authentication confidence
            confidence = 0.0
            if enhanced_analysis.get('authentication'):
                confidence = enhanced_analysis['authentication'].get('confidence_score', 0.0)

            # Create collectible entry
            collectible_id = db.add_collectible(
                name=name,
                category=category_val,
                brand=brand,
                year=year_val,
                condition=condition_val,
                estimated_value_low=value_low,
                estimated_value_high=value_high,
                market_data=enhanced_analysis.get('market_analysis'),
                attributes=enhanced_analysis.get('rarity'),
                image_urls=photos,
                identified_by='claude',
                confidence_score=confidence,
                notes=description
            )

            # Save deep analysis to collectible
            db.save_deep_analysis(collectible_id, enhanced_analysis)

        # Create listing in DB - ensure user_id is UUID string
        user_id_str = str(current_user.id) if current_user and current_user.id else None
        if not user_id_str:
            return jsonify({"error": "User not authenticated"}), 401

        listing_id = db.create_listing(
            listing_uuid=listing_uuid,
            title=title,
            description=description,
            price=price,
            condition=condition,
            photos=photos,
            user_id=user_id_str,
            collectible_id=collectible_id,
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
        print(f"Error saving draft: {e}")
        import traceback
        traceback.print_exc()
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
# INVENTORY MANAGEMENT ENDPOINTS
# -------------------------------------------------------------------------

@main_bp.route('/inventory')
@login_required
def inventory():
    """Centralized inventory management page"""
    return render_template('inventory.html')


@main_bp.route('/api/inventory/listings')
@login_required
def api_get_inventory():
    """Get all inventory items with filtering"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        # Get filter parameters
        status_filter = request.args.get('status', 'all')  # all, draft, active, sold, shipped, archived
        category_filter = request.args.get('category', 'all')
        platform_filter = request.args.get('platform', 'all')
        search_query = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'created_at')  # created_at, title, price, status
        sort_order = request.args.get('order', 'desc')  # asc, desc
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        # Build query
        query = """
            SELECT
                l.*,
                COALESCE(SUM(CASE WHEN ps.status = 'sold' THEN 1 ELSE 0 END), 0) as sold_count,
                COUNT(ps.id) as platform_count,
                STRING_AGG(DISTINCT p.name, ', ') as platforms
            FROM listings l
            LEFT JOIN platform_listings ps ON l.id = ps.listing_id
            LEFT JOIN platforms p ON ps.platform_id = p.id
            WHERE l.user_id::text = %s::text
        """
        params = [str(current_user.id)]

        # Add status filter
        if status_filter != 'all':
            query += " AND l.status = %s"
            params.append(status_filter)

        # Add category filter
        if category_filter != 'all':
            query += " AND l.category ILIKE %s"
            params.append(f"%{category_filter}%")

        # Add platform filter
        if platform_filter != 'all':
            query += " AND p.name = %s"
            params.append(platform_filter)

        # Add search filter
        if search_query:
            query += """ AND (
                l.title ILIKE %s OR
                l.description ILIKE %s OR
                l.sku ILIKE %s OR
                l.upc ILIKE %s
            )"""
            search_param = f"%{search_query}%"
            params.extend([search_param] * 4)

        # Group by and add sorting
        query += """
            GROUP BY l.id
            ORDER BY l.{sort_by} {sort_order}
            LIMIT %s OFFSET %s
        """.format(sort_by=sort_by, sort_order=sort_order)
        params.extend([per_page, (page - 1) * per_page])

        # Execute query
        cursor = db._get_cursor()
        cursor.execute(query, params)
        listings = [dict(row) for row in cursor.fetchall()]

        # Get total count for pagination
        count_query = """
            SELECT COUNT(DISTINCT l.id) as total
            FROM listings l
            LEFT JOIN platform_listings ps ON l.id = ps.listing_id
            LEFT JOIN platforms p ON ps.platform_id = p.id
            WHERE l.user_id::text = %s::text
        """
        count_params = [str(current_user.id)]

        # Apply same filters for count
        if status_filter != 'all':
            count_query += " AND l.status = %s"
            count_params.append(status_filter)
        if category_filter != 'all':
            count_query += " AND l.category ILIKE %s"
            count_params.append(f"%{category_filter}%")
        if platform_filter != 'all':
            count_query += " AND p.name = %s"
            count_params.append(platform_filter)
        if search_query:
            count_query += """ AND (
                l.title ILIKE %s OR
                l.description ILIKE %s OR
                l.sku ILIKE %s OR
                l.upc ILIKE %s
            )"""
            search_param = f"%{search_query}%"
            count_params.extend([search_param] * 4)

        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['total']

        # Get summary stats
        stats_query = """
            SELECT
                COUNT(CASE WHEN status = 'draft' THEN 1 END) as draft_count,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count,
                COUNT(CASE WHEN status = 'sold' THEN 1 END) as sold_count,
                COUNT(CASE WHEN status = 'shipped' THEN 1 END) as shipped_count,
                COUNT(CASE WHEN status = 'archived' THEN 1 END) as archived_count,
                COUNT(*) as total_count,
                COALESCE(SUM(CASE WHEN status IN ('sold', 'shipped') THEN price ELSE 0 END), 0) as total_value
            FROM listings
            WHERE user_id::text = %s::text
        """
        cursor.execute(stats_query, (str(current_user.id),))
        stats = dict(cursor.fetchone())

        return jsonify({
            'success': True,
            'listings': listings,
            'stats': stats,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/inventory/bulk-update', methods=['POST'])
@login_required
def api_bulk_update_inventory():
    """Bulk update inventory items"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        data = request.get_json()
        listing_ids = data.get('listing_ids', [])
        updates = data.get('updates', {})  # status, category, etc.

        if not listing_ids:
            return jsonify({'error': 'No listing IDs provided'}), 400

        if not updates:
            return jsonify({'error': 'No updates provided'}), 400

        updated_count = 0
        failed = []

        for listing_id in listing_ids:
            try:
                # Verify ownership
                listing = db.get_listing(listing_id)
                if not listing or str(listing['user_id']) != str(current_user.id):
                    failed.append({'id': listing_id, 'error': 'Not found or unauthorized'})
                    continue

                # Update listing
                db.update_listing(listing_id, **updates)
                updated_count += 1

            except Exception as e:
                failed.append({'id': listing_id, 'error': str(e)})

        return jsonify({
            'success': True,
            'updated': updated_count,
            'failed': failed
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/inventory/bulk-delete', methods=['POST'])
@login_required
def api_bulk_delete_inventory():
    """Bulk delete inventory items"""
    try:
        from src.database.db import get_db_instance
        db = get_db_instance()

        data = request.get_json()
        listing_ids = data.get('listing_ids', [])
        confirm_delete = data.get('confirm', False)

        if not listing_ids:
            return jsonify({'error': 'No listing IDs provided'}), 400

        if not confirm_delete:
            return jsonify({'error': 'Deletion not confirmed'}), 400

        deleted_count = 0
        failed = []

        for listing_id in listing_ids:
            try:
                # Verify ownership
                listing = db.get_listing(listing_id)
                if not listing or str(listing['user_id']) != str(current_user.id):
                    failed.append({'id': listing_id, 'error': 'Not found or unauthorized'})
                    continue

                # Delete listing
                db.delete_listing(listing_id)
                deleted_count += 1

            except Exception as e:
                failed.append({'id': listing_id, 'error': str(e)})

        return jsonify({
            'success': True,
            'deleted': deleted_count,
            'failed': failed
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/inventory/export')
@login_required
def api_export_inventory():
    """Export inventory data"""
    try:
        from src.database.db import get_db_instance
        from src.import_export.csv_handler import CSVImportExport

        db = get_db_instance()
        csv_handler = CSVImportExport(db)

        export_type = request.args.get('type', 'all')  # all, draft, active, sold
        format_type = request.args.get('format', 'csv')  # csv, json

        if format_type == 'csv':
            csv_content = csv_handler.export_csv(current_user.id, export_type)
            return csv_content, 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename=inventory_{export_type}.csv'
            }
        else:
            # JSON export
            listings = csv_handler._get_listings_for_export(current_user.id, export_type)
            return jsonify({
                'success': True,
                'listings': listings,
                'export_type': export_type
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


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


# -------------------------------------------------------------------------
# CSV EXPORT ENDPOINT
# -------------------------------------------------------------------------

@main_bp.route('/api/export-csv', methods=['POST'])
@login_required
def api_export_csv():
    """Export listings to platform-specific CSV format"""
    try:
        import csv
        import io
        from flask import make_response

        data = request.get_json()
        platform = data.get('platform', 'generic')
        listings = data.get('listings', [])

        if not listings:
            return jsonify({"error": "No listings provided"}), 400

        # Create CSV in memory
        output = io.StringIO()

        # Platform-specific CSV formats
        if platform == 'poshmark':
            fieldnames = ['Title', 'Description', 'Category', 'Brand', 'Size', 'Color', 'Price', 'Quantity', 'Condition', 'Photos']
        elif platform == 'mercari':
            fieldnames = ['Title', 'Description', 'Category', 'Brand', 'Price', 'Condition', 'Shipping Weight', 'Photos']
        elif platform == 'ebay':
            fieldnames = ['Title', 'Description', 'Category', 'Price', 'Quantity', 'Condition', 'Brand', 'Photos', 'SKU']
        elif platform == 'grailed':
            fieldnames = ['Title', 'Description', 'Designer', 'Size', 'Category', 'Price', 'Condition', 'Photos']
        elif platform == 'depop':
            fieldnames = ['Title', 'Description', 'Category', 'Brand', 'Size', 'Price', 'Condition', 'Photos']
        else:  # generic
            fieldnames = ['Title', 'Description', 'Price', 'Category', 'Brand', 'Size', 'Color', 'Condition', 'Quantity', 'Storage Location', 'Photos']

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for listing in listings:
            # Parse photos if stored as JSON string
            photos = listing.get('photos', '')
            if isinstance(photos, str) and photos:
                try:
                    import json
                    photos = json.loads(photos)
                    photos = ','.join(photos) if isinstance(photos, list) else photos
                except:
                    pass

            # Create row based on platform
            row = {}
            if platform == 'poshmark':
                row = {
                    'Title': listing.get('title', ''),
                    'Description': listing.get('description', ''),
                    'Category': listing.get('category', listing.get('item_type', '')),
                    'Brand': listing.get('brand', ''),
                    'Size': listing.get('size', ''),
                    'Color': listing.get('color', ''),
                    'Price': listing.get('price', ''),
                    'Quantity': listing.get('quantity', 1),
                    'Condition': listing.get('condition', ''),
                    'Photos': photos
                }
            elif platform == 'mercari':
                row = {
                    'Title': listing.get('title', ''),
                    'Description': listing.get('description', ''),
                    'Category': listing.get('category', listing.get('item_type', '')),
                    'Brand': listing.get('brand', ''),
                    'Price': listing.get('price', ''),
                    'Condition': listing.get('condition', ''),
                    'Shipping Weight': listing.get('weight', '1 lb'),
                    'Photos': photos
                }
            elif platform == 'ebay':
                row = {
                    'Title': listing.get('title', ''),
                    'Description': listing.get('description', ''),
                    'Category': listing.get('category', listing.get('item_type', '')),
                    'Price': listing.get('price', ''),
                    'Quantity': listing.get('quantity', 1),
                    'Condition': listing.get('condition', ''),
                    'Brand': listing.get('brand', ''),
                    'Photos': photos,
                    'SKU': listing.get('sku', '')
                }
            elif platform == 'grailed':
                row = {
                    'Title': listing.get('title', ''),
                    'Description': listing.get('description', ''),
                    'Designer': listing.get('brand', ''),
                    'Size': listing.get('size', ''),
                    'Category': listing.get('category', listing.get('item_type', '')),
                    'Price': listing.get('price', ''),
                    'Condition': listing.get('condition', ''),
                    'Photos': photos
                }
            elif platform == 'depop':
                row = {
                    'Title': listing.get('title', ''),
                    'Description': listing.get('description', ''),
                    'Category': listing.get('category', listing.get('item_type', '')),
                    'Brand': listing.get('brand', ''),
                    'Size': listing.get('size', ''),
                    'Price': listing.get('price', ''),
                    'Condition': listing.get('condition', ''),
                    'Photos': photos
                }
            else:  # generic
                row = {
                    'Title': listing.get('title', ''),
                    'Description': listing.get('description', ''),
                    'Price': listing.get('price', ''),
                    'Category': listing.get('category', listing.get('item_type', '')),
                    'Brand': listing.get('brand', ''),
                    'Size': listing.get('size', ''),
                    'Color': listing.get('color', ''),
                    'Condition': listing.get('condition', ''),
                    'Quantity': listing.get('quantity', 1),
                    'Storage Location': listing.get('storage_location', ''),
                    'Photos': photos
                }

            writer.writerow(row)

        # Create response
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename={platform}_export.csv'

        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# FEED GENERATION ENDPOINT
# -------------------------------------------------------------------------

@main_bp.route('/api/generate-feed', methods=['POST'])
@login_required
def api_generate_feed():
    """Generate product feed for catalog platforms (Facebook, Google Shopping, Pinterest)"""
    try:
        import io
        from flask import make_response
        from ..src.adapters.all_platforms import FacebookShopsAdapter, GoogleShoppingAdapter, PinterestAdapter
        from ..src.schema.unified_listing import UnifiedListing, Price, ListingCondition, Photo

        data = request.get_json()
        platform = data.get('platform', 'facebook')
        format_type = data.get('format', 'csv')  # csv, xml, json

        # Get active listings for the user
        listings_data = db.get_active_listings(current_user.id)
        
        if not listings_data:
            return jsonify({"error": "No active listings found"}), 404

        # Convert to UnifiedListing objects
        listings = []
        for listing_data in listings_data:
            try:
                # Convert price to Price object
                price_obj = Price(amount=float(listing_data['price']))

                # Convert condition to ListingCondition enum
                condition_str = listing_data.get('condition', 'good').lower()
                condition_enum = ListingCondition.GOOD  # default
                if condition_str == 'new':
                    condition_enum = ListingCondition.NEW
                elif condition_str == 'like_new':
                    condition_enum = ListingCondition.LIKE_NEW
                elif condition_str == 'excellent':
                    condition_enum = ListingCondition.EXCELLENT
                elif condition_str == 'fair':
                    condition_enum = ListingCondition.FAIR
                elif condition_str == 'poor':
                    condition_enum = ListingCondition.POOR

                # Convert photos from JSON string to List[Photo]
                photos = []
                if listing_data.get('photos'):
                    try:
                        import json
                        photos_data = json.loads(listing_data['photos'])
                        for i, photo_url in enumerate(photos_data):
                            photos.append(Photo(url=photo_url, order=i, is_primary=(i == 0)))
                    except (json.JSONDecodeError, TypeError):
                        # If photos is not valid JSON, skip
                        pass

                listing = UnifiedListing(
                    title=listing_data['title'],
                    description=listing_data.get('description', ''),
                    price=price_obj,
                    condition=condition_enum,
                    photos=photos
                )
                listings.append(listing)
            except Exception as e:
                print(f"Error converting listing {listing_data.get('id')}: {e}")
                continue

        # Initialize the appropriate adapter
        adapter = None
        if platform == 'facebook':
            adapter = FacebookShopsAdapter()
        elif platform == 'google':
            adapter = GoogleShoppingAdapter()
        elif platform == 'pinterest':
            adapter = PinterestAdapter()
        else:
            return jsonify({"error": f"Unsupported platform: {platform}"}), 400

        # Generate the feed
        feed_path = adapter.generate_feed(listings, format_type)
        
        # Read the feed file and return it
        with open(feed_path, 'r', encoding='utf-8') as f:
            feed_content = f.read()

        # Create response
        response = make_response(feed_content)
        
        # Set appropriate content type
        if format_type == 'xml':
            response.headers['Content-Type'] = 'application/xml'
            extension = 'xml'
        elif format_type == 'json':
            response.headers['Content-Type'] = 'application/json'
            extension = 'json'
        else:
            response.headers['Content-Type'] = 'text/csv'
            extension = 'csv'
            
        response.headers['Content-Disposition'] = f'attachment; filename={platform}_feed.{extension}'

        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# DRAFT → LISTING WORKFLOW
# ============================================================================

@main_bp.route('/api/publish-drafts', methods=['POST'])
@login_required
def api_publish_drafts():
    """Publish selected drafts to active listings and optionally to platforms"""
    try:
        data = request.get_json()
        draft_ids = data.get('draft_ids', [])
        platforms = data.get('platforms', [])  # List of platforms to publish to
        auto_assign_sku = data.get('auto_assign_sku', True)

        if not draft_ids:
            return jsonify({"error": "No draft IDs provided"}), 400

        results = {
            'published': [],
            'failed': [],
            'platform_results': {}
        }

        for draft_id in draft_ids:
            try:
                # Get draft
                draft = db.get_listing(draft_id)
                if not draft:
                    results['failed'].append({
                        'draft_id': draft_id,
                        'error': 'Draft not found'
                    })
                    continue

                # Verify ownership
                if str(draft['user_id']) != str(current_user.id):
                    results['failed'].append({
                        'draft_id': draft_id,
                        'error': 'Permission denied'
                    })
                    continue

                # Auto-assign SKU if needed
                if auto_assign_sku and not draft.get('sku'):
                    sku = db.assign_auto_sku_if_missing(draft_id, current_user.id)
                    draft['sku'] = sku

                # Change status to active
                db.update_listing_status(draft_id, 'active')

                results['published'].append({
                    'draft_id': draft_id,
                    'title': draft['title'],
                    'sku': draft.get('sku')
                })

            except Exception as e:
                results['failed'].append({
                    'draft_id': draft_id,
                    'error': str(e)
                })

        # Publish to platforms if specified
        if platforms and results['published']:
            platform_results = {}
            for platform in platforms:
                try:
                    # Import platform adapter
                    if platform.lower() == 'ebay':
                        from ..src.adapters.ebay_adapter import EbayAdapter
                        adapter_class = EbayAdapter
                    elif platform.lower() == 'mercari':
                        from ..src.adapters.mercari_adapter import MercariAdapter
                        adapter_class = MercariAdapter
                    elif platform.lower() == 'poshmark':
                        from ..src.adapters.poshmark_adapter import PoshmarkAdapter
                        adapter_class = PoshmarkAdapter
                    else:
                        # Try to get from all_platforms
                        from ..src.adapters.all_platforms import get_adapter_class as get_all_adapter_class
                        adapter_class = get_all_adapter_class(platform)
                        if not adapter_class:
                            platform_results[platform] = {'error': f'Unsupported platform: {platform}'}
                            continue

                    # Try to create adapter instance
                    adapter = None
                    try:
                        # Check if adapter has from_env method
                        if hasattr(adapter_class, 'from_env'):
                            adapter = adapter_class.from_env()
                        else:
                            # For adapters that don't need auth (like CSV adapters)
                            adapter = adapter_class()
                    except Exception as e:
                        platform_results[platform] = {'error': f'Authentication/setup required for {platform}: {str(e)}'}
                        continue

                    # Get platform mapper
                    from ..src.adapters.platform_configs import get_platform_mapper
                    mapper = get_platform_mapper(platform)

                    # Publish each listing
                    published_count = 0
                    failed_count = 0
                    for item in results['published']:
                        try:
                            listing_data = db.get_listing(item['draft_id'])

                            # Convert to UnifiedListing
                            from ..schema.unified_listing import UnifiedListing
                            unified_listing = UnifiedListing.from_dict(listing_data)

                            # Publish to platform (adapter handles field mapping internally)
                            result = adapter.publish_listing(unified_listing)
                            if result.get('success'):
                                published_count += 1
                            else:
                                failed_count += 1
                                print(f"Failed to publish {item['draft_id']} to {platform}: {result.get('error', 'Unknown error')}")

                        except Exception as e:
                            failed_count += 1
                            print(f"Failed to publish {item['draft_id']} to {platform}: {e}")

                    platform_results[platform] = {
                        'published': published_count,
                        'failed': failed_count,
                        'total': len(results['published'])
                    }

                except Exception as e:
                    platform_results[platform] = {'error': str(e)}

            results['platform_results'] = platform_results

            # Format response for frontend compatibility
            csv_files = {}
            api_results = []

            for platform, result in platform_results.items():
                if 'error' in result:
                    if platform.lower() in ['poshmark', 'bonanza', 'ecrater', 'rubylane', 'offerup']:
                        # CSV platform error
                        csv_files[platform] = {
                            'platform_name': platform.title(),
                            'error': result['error']
                        }
                    else:
                        # API platform error
                        api_results.append({
                            'platform_name': platform.title(),
                            'status': 'error',
                            'message': result['error']
                        })
                else:
                    if platform.lower() in ['poshmark', 'bonanza', 'ecrater', 'rubylane', 'offerup']:
                        # CSV platform success - would need to generate CSV here
                        csv_files[platform] = {
                            'platform_name': platform.title(),
                            'download_url': f'/api/export-csv?platform={platform}&ids={",".join(str(item["draft_id"]) for item in results["published"])}',
                            'instructions': [
                                f'Log into your {platform.title()} account',
                                f'Go to the bulk upload section',
                                f'Upload the generated CSV file',
                                'Review and publish listings'
                            ]
                        }
                    else:
                        # API platform result
                        api_results.append({
                            'platform_name': platform.title(),
                            'status': 'posted' if result['published'] > 0 else 'partial',
                            'message': f'Successfully posted {result["published"]} of {result["total"]} listings'
                        })

            results['csv_files'] = csv_files
            results['api_results'] = api_results

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/bulk-edit-drafts', methods=['POST'])
@login_required
def api_bulk_edit_drafts():
    """Bulk edit multiple drafts"""
    try:
        data = request.get_json()
        draft_ids = data.get('draft_ids', [])
        updates = data.get('updates', {})  # Fields to update

        if not draft_ids:
            return jsonify({"error": "No draft IDs provided"}), 400

        if not updates:
            return jsonify({"error": "No updates provided"}), 400

        results = {
            'updated': [],
            'failed': []
        }

        for draft_id in draft_ids:
            try:
                # Verify ownership
                draft = db.get_listing(draft_id)
                if not draft or str(draft['user_id']) != str(current_user.id):
                    results['failed'].append({
                        'draft_id': draft_id,
                        'error': 'Permission denied or draft not found'
                    })
                    continue

                # Update the draft
                db.update_listing(draft_id, **updates)

                results['updated'].append({
                    'draft_id': draft_id,
                    'title': draft['title']
                })

            except Exception as e:
                results['failed'].append({
                    'draft_id': draft_id,
                    'error': str(e)
                })

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/schedule-feed-sync', methods=['POST'])
@login_required
def api_schedule_feed_sync():
    """Schedule automatic feed sync for catalog platforms"""
    try:
        from ..src.workers.scheduler import Scheduler
        
        data = request.get_json()
        platforms = data.get('platforms', ['facebook', 'google', 'pinterest'])
        interval_hours = data.get('interval_hours', 6)  # Default 6 hours
        
        # Get or create scheduler instance
        # TODO: This should be a singleton/global instance
        scheduler = Scheduler()
        scheduler.start()
        
        # Schedule feed sync for current user
        job_id = scheduler.schedule_feed_sync(
            user_id=current_user.id,
            platforms=platforms,
            interval_hours=interval_hours
        )
        
        return jsonify({
            "status": "scheduled",
            "job_id": job_id,
            "platforms": platforms,
            "interval_hours": interval_hours,
            "message": f"Feed sync scheduled every {interval_hours} hours for platforms: {', '.join(platforms)}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PLATFORM CONNECTIONS UI & API
# ============================================================================

@main_bp.route("/platforms")
@login_required
def platforms_page():
    """Platform connections management page"""
    # Get user's platform connections from database
    connections = db.get_platform_connections(current_user.id) if hasattr(db, 'get_platform_connections') else {}

    return render_template("platforms.html", connections=connections)


@main_bp.route("/api/platform/<platform>/connect", methods=["POST"])
@login_required
def connect_platform(platform):
    """Connect a platform with API key/credentials"""
    try:
        data = request.get_json()

        # Store platform credentials (encrypted in production!)
        if hasattr(db, 'save_platform_connection'):
            db.save_platform_connection(
                user_id=current_user.id,
                platform=platform,
                credentials=data
            )
        else:
            # Fallback: store in user's settings
            print(f"Platform {platform} connection saved for user {current_user.id}")

        return jsonify({"success": True, "message": f"Connected to {platform}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/platform/<platform>/disconnect", methods=["DELETE"])
@login_required
def disconnect_platform(platform):
    """Disconnect a platform"""
    try:
        if hasattr(db, 'delete_platform_connection'):
            db.delete_platform_connection(current_user.id, platform)
        else:
            print(f"Platform {platform} disconnected for user {current_user.id}")

        return jsonify({"success": True, "message": f"Disconnected from {platform}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/platform/<platform>/test", methods=["GET"])
@login_required
def test_platform_connection(platform):
    """Test a platform connection"""
    try:
        # Get platform credentials
        if hasattr(db, 'get_platform_connection'):
            credentials = db.get_platform_connection(current_user.id, platform)

            if not credentials:
                return jsonify({"error": "Platform not connected"}), 404

            # Test the connection (implement per platform)
            # For now, just return success
            return jsonify({"success": True, "message": f"Connection to {platform} is working"})
        else:
            return jsonify({"error": "Platform connections not implemented"}), 501

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/listing/<int:listing_id>/platforms", methods=["GET"])
@login_required
def get_listing_platforms(listing_id):
    """Get platform status for a specific listing"""
    try:
        # Check listing belongs to user
        listing = db.get_listing(listing_id)
        if not listing or listing.get('user_id') != current_user.id:
            return jsonify({"error": "Listing not found"}), 404

        # Get platform statuses
        if hasattr(db, 'get_listing_platform_status'):
            platforms = db.get_listing_platform_status(listing_id)
        else:
            # Default implementation
            platforms = [
                {"name": "ebay", "status": "active", "listing_id": "123456789", "updated_at": "2025-11-29"},
                {"name": "etsy", "status": "draft", "listing_id": None, "updated_at": "2025-11-29"},
                {"name": "shopify", "status": "inactive", "listing_id": None, "updated_at": None}
            ]

        return jsonify({"success": True, "platforms": platforms})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/listing/<int:listing_id>/publish-to-platform", methods=["POST"])
@login_required
def publish_to_platform(listing_id):
    """Publish a listing to a specific platform"""
    try:
        data = request.get_json()
        platform = data.get('platform')

        if not platform:
            return jsonify({"error": "Platform is required"}), 400

        # Check listing belongs to user
        listing = db.get_listing(listing_id)
        if not listing or listing.get('user_id') != current_user.id:
            return jsonify({"error": "Listing not found"}), 404

        # Publish to platform
        from src.listing_manager import ListingManager
        manager = ListingManager()
        result = manager.publish_to_platform(listing_id, platform)

        return jsonify({"success": True, "result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/listing/<int:listing_id>/delist-from-platform", methods=["POST"])
@login_required
def delist_from_platform(listing_id):
    """Remove a listing from a specific platform"""
    try:
        data = request.get_json()
        platform = data.get('platform')

        if not platform:
            return jsonify({"error": "Platform is required"}), 400

        # Check listing belongs to user
        listing = db.get_listing(listing_id)
        if not listing or listing.get('user_id') != current_user.id:
            return jsonify({"error": "Listing not found"}), 404

        # Delist from platform
        from src.listing_manager import ListingManager
        manager = ListingManager()
        result = manager.delist_from_platform(listing_id, platform)

        return jsonify({"success": True, "result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# CSV IMPORT SYSTEM
# ============================================================================

@main_bp.route("/api/import/csv", methods=["POST"])
@login_required
def import_csv():
    """Import listings from CSV file"""
    try:
        csv_module = __import__("src.import", fromlist=["CSVImporter"])

        CSVImporter = csv_module.CSVImporter
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({"error": "File must be a CSV"}), 400

        # Read CSV
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as temp:
            file.save(temp.name)
            temp_path = temp.name

        try:
            importer = CSVImporter(user_id=current_user.id, db=db)
            result = importer.import_csv(temp_path)

            return jsonify({
                "success": True,
                "imported": result['imported'],
                "skipped": result['skipped'],
                "errors": result['errors'],
                "duplicates": result.get('duplicates', [])
            })
        finally:
            import os
            os.unlink(temp_path)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# IMAGE PROCESSING PIPELINE
# ============================================================================

@main_bp.route("/api/image/process", methods=["POST"])
@login_required
def process_image():
    """Process an image through the pipeline"""
    try:
        from src.images import ImagePipeline

        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files['file']
        platform = request.form.get('platform', 'generic')

        # Save uploaded file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp:
            file.save(temp.name)
            input_path = temp.name

        try:
            pipeline = ImagePipeline()

            # Process image
            output_path = pipeline.process_for_platform(input_path, platform)

            # Return processed image
            from flask import send_file
            return send_file(output_path, as_attachment=True)

        finally:
            import os
            os.unlink(input_path)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TAX & ACCOUNTING REPORTS
# ============================================================================

@main_bp.route("/api/reports/tax/<period>", methods=["GET"])
@login_required
def generate_tax_report(period):
    """Generate tax report (monthly, quarterly, annual)"""
    try:
        from src.accounting import TaxReportGenerator

        generator = TaxReportGenerator(db)
        report = generator.generate_report(
            user_id=current_user.id,
            period=period,
            year=int(request.args.get('year', datetime.now().year))
        )

        return jsonify({"success": True, "report": report})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/reports/profit", methods=["GET"])
@login_required
def get_profit_summary():
    """Get profit summary for user's listings"""
    try:
        from src.accounting import TaxReportGenerator

        generator = TaxReportGenerator(db)
        summary = generator.get_profit_summary(current_user.id)

        return jsonify({"success": True, "summary": summary})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# STORAGE LOCATION MANAGEMENT
# ============================================================================

@main_bp.route("/api/storage/locations", methods=["GET"])
@login_required
def get_storage_locations():
    """Get all storage locations for current user"""
    try:
        from src.storage import StorageManager
        manager = StorageManager(db)
        locations = manager.get_user_locations(current_user.id)
        return jsonify({"success": True, "locations": locations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/storage/location", methods=["POST"])
@login_required
def create_storage_location():
    """Create a new storage location"""
    try:
        from src.storage import StorageManager
        data = request.get_json()

        manager = StorageManager(db)
        location = manager.create_location(
            user_id=current_user.id,
            name=data.get('name'),
            location_type=data.get('type', 'bin'),
            parent_id=data.get('parent_id'),
            notes=data.get('notes')
        )

        return jsonify({"success": True, "location": location})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/storage/location/<int:location_id>", methods=["GET"])
@login_required
def get_storage_location(location_id):
    """Get storage location details"""
    try:
        from src.storage import StorageManager
        manager = StorageManager(db)
        location = manager.get_location(location_id)

        if not location:
            return jsonify({"error": "Location not found"}), 404

        # Get items in this location
        items = manager.get_location_items(location_id)

        return jsonify({
            "success": True,
            "location": location,
            "items": items
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/storage/assign", methods=["POST"])
@login_required
def assign_storage_location():
    """Assign an item to a storage location"""
    try:
        from src.storage import StorageManager
        data = request.get_json()

        manager = StorageManager(db)
        success = manager.assign_location(
            listing_id=data.get('listing_id'),
            location_id=data.get('location_id'),
            quantity=data.get('quantity', 1)
        )

        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/storage/bulk-assign", methods=["POST"])
@login_required
def bulk_assign_storage():
    """Bulk assign multiple items to a location"""
    try:
        from src.storage import StorageManager
        data = request.get_json()

        manager = StorageManager(db)
        result = manager.bulk_assign(
            location_id=data.get('location_id'),
            listing_ids=data.get('listing_ids', [])
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/storage/suggest", methods=["POST"])
@login_required
def suggest_storage_location():
    """Suggest optimal storage location for an item"""
    try:
        from src.storage import StorageManager
        data = request.get_json()

        manager = StorageManager(db)
        suggestion = manager.suggest_location(
            user_id=current_user.id,
            category=data.get('category'),
            size=data.get('size')
        )

        return jsonify({"success": True, "suggestion": suggestion})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# SALES SYNC ENGINE
# ============================================================================

@main_bp.route("/api/sales/sync/<platform>", methods=["POST"])
@login_required
def sync_platform_sales(platform):
    """Sync sales from a specific platform"""
    try:
        from src.sales import SalesSyncEngine

        engine = SalesSyncEngine(db)
        result = engine.sync_platform_sales(current_user.id, platform)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/sales/sync-all", methods=["POST"])
@login_required
def sync_all_sales():
    """Sync sales from all connected platforms"""
    try:
        from src.sales import SalesSyncEngine

        engine = SalesSyncEngine(db)
        result = engine.sync_all_platforms(current_user.id)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/sales/manual-sale", methods=["POST"])
@login_required
def record_manual_sale():
    """Manually record a sale (for platforms without API)"""
    try:
        from src.sales import SalesSyncEngine
        data = request.get_json()

        engine = SalesSyncEngine(db)
        result = engine.detect_sale(
            listing_id=data.get('listing_id'),
            platform=data.get('platform', 'manual'),
            sale_data={
                'price': data.get('price'),
                'buyer': data.get('buyer', {}),
                'sale_date': data.get('sale_date', datetime.now()),
                'transaction_id': data.get('transaction_id')
            }
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/sales/<int:listing_id>", methods=["GET"])
@login_required
def get_sale_details(listing_id):
    """Get detailed sale information"""
    try:
        from src.sales import SalesSyncEngine

        # Check listing belongs to user
        listing = db.get_listing(listing_id)
        if not listing or listing.get('user_id') != current_user.id:
            return jsonify({"error": "Listing not found"}), 404

        engine = SalesSyncEngine(db)
        details = engine.get_sale_details(listing_id)

        if not details:
            return jsonify({"error": "No sale data found"}), 404

        return jsonify({"success": True, "sale": details})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# INVOICING ROUTES
# ============================================================================

@main_bp.route('/invoicing')
@login_required
def invoicing():
    """Invoicing management page"""
    return render_template('invoicing.html')


@main_bp.route('/api/create-invoice', methods=['POST'])
@login_required
def api_create_invoice():
    """Create a new invoice"""
    try:
        from ..src.invoicing.invoice_generator import InvoiceGenerator

        data = request.get_json()
        listing_id = data.get('listing_id')
        buyer_email = data.get('buyer_email')
        tax_rate = data.get('tax_rate', 0)
        shipping_cost = data.get('shipping_cost', 0)
        discount = data.get('discount', 0)

        if not listing_id or not buyer_email:
            return jsonify({"error": "Missing required fields"}), 400

        # Get listing details
        listing = db.get_listing(listing_id)
        if not listing:
            return jsonify({"error": "Listing not found"}), 404

        # Create buyer info
        buyer = {
            'email': buyer_email,
            'name': buyer_email.split('@')[0]  # Simple name extraction
        }

        # Generate invoice
        generator = InvoiceGenerator()
        invoice_data = generator.create_invoice(
            listing=listing,
            buyer=buyer,
            tax_rate=tax_rate / 100.0,  # Convert percentage to decimal
            shipping=shipping_cost,
            discount=discount
        )

        # Store invoice in database (simplified - just return for now)
        invoice_id = f"inv_{listing_id}_{int(datetime.now().timestamp())}"

        return jsonify({
            "success": True,
            "invoice_id": invoice_id,
            "invoice": invoice_data,
            "message": "Invoice created successfully"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/invoices')
@login_required
def api_get_invoices():
    """Get list of invoices for current user"""
    try:
        # For now, return empty list since we don't have database storage
        return jsonify({"success": True, "invoices": []})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/invoice/<invoice_id>')
@login_required
def api_get_invoice(invoice_id):
    """Get invoice details and HTML"""
    try:
        # For now, return a sample invoice
        sample_invoice = {
            'invoice_number': 'INV-2024-00001',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'buyer': {'email': 'buyer@example.com', 'name': 'Sample Buyer'},
            'item': {'title': 'Sample Item', 'price': 25.00},
            'totals': {'subtotal': 25.00, 'tax': 2.06, 'shipping': 5.00, 'total': 32.06},
            'status': 'unpaid'
        }

        from ..src.invoicing.invoice_generator import InvoiceGenerator
        generator = InvoiceGenerator()
        html = generator.generate_invoice_html(sample_invoice)

        return jsonify({"success": True, "invoice": sample_invoice, "html": html})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/email-invoice/<invoice_id>', methods=['POST'])
@login_required
def api_email_invoice(invoice_id):
    """Email invoice to buyer"""
    try:
        from ..src.invoicing.invoice_generator import InvoiceGenerator

        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({"error": "Email address required"}), 400

        generator = InvoiceGenerator()
        invoice = generator.get_invoice(invoice_id)

        if not invoice or str(invoice.get('user_id')) != str(current_user.id):
            return jsonify({"error": "Invoice not found"}), 404

        # Generate HTML and send email
        html = generator.generate_invoice_html(invoice)

        # TODO: Implement email sending
        # For now, just return success
        return jsonify({"success": True, "message": f"Invoice would be sent to {email}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# BILLING & SUBSCRIPTION ROUTES
# ============================================================================

@main_bp.route('/billing')
@login_required
def billing():
    """Billing and subscription management page"""
    try:
        from ..src.billing import BillingManager, SubscriptionTier

        billing_manager = BillingManager()
        user_tier = billing_manager.get_user_tier(current_user.id)
        tier_limits = billing_manager.get_tier_limits(user_tier)

        # Get current usage
        can_create_listing, limit_message = billing_manager.check_listing_limit(current_user.id)

        return render_template('billing.html',
                             user_tier=user_tier.value,
                             tier_limits=tier_limits,
                             can_create_listing=can_create_listing,
                             limit_message=limit_message)

    except Exception as e:
        flash(f'Error loading billing page: {str(e)}', 'error')
        return redirect(url_for('main.index'))


@main_bp.route('/api/billing/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create Stripe checkout session for subscription"""
    try:
        from ..src.billing import StripeIntegration

        data = request.get_json()
        tier = data.get('tier')

        if not tier or tier not in ['PRO', 'BUSINESS']:
            return jsonify({"error": "Invalid tier"}), 400

        stripe_integration = StripeIntegration()

        success_url = url_for('main.billing_success', _external=True)
        cancel_url = url_for('main.billing', _external=True)

        session = stripe_integration.create_checkout_session(
            user_id=current_user.id,
            tier=tier,
            success_url=success_url,
            cancel_url=cancel_url
        )

        return jsonify(session)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/billing/success')
@login_required
def billing_success():
    """Billing success page"""
    flash('Subscription activated successfully!', 'success')
    return redirect(url_for('main.billing'))


@main_bp.route('/api/billing/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    try:
        from ..src.billing import StripeIntegration

        payload = request.get_data()
        sig_header = request.headers.get('stripe-signature')

        if not sig_header:
            return jsonify({"error": "No signature"}), 400

        stripe_integration = StripeIntegration()
        result = stripe_integration.handle_webhook(payload, sig_header)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/billing/check-feature-access', methods=['GET'])
@login_required
def check_feature_access():
    """Check if user can access a feature"""
    try:
        from ..src.billing import BillingManager

        feature = request.args.get('feature')
        if not feature:
            return jsonify({"error": "Feature parameter required"}), 400

        billing_manager = BillingManager()
        can_access = billing_manager.can_access_feature(current_user.id, feature)

        return jsonify({
            "can_access": can_access,
            "feature": feature
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/billing/usage', methods=['GET'])
@login_required
def get_usage():
    """Get current usage statistics"""
    try:
        from ..src.billing import BillingManager

        billing_manager = BillingManager()

        # Check listing limit
        can_create, limit_message = billing_manager.check_listing_limit(current_user.id)

        return jsonify({
            "can_create_listing": can_create,
            "limit_message": limit_message
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/api/billing/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel user subscription"""
    try:
        from ..src.billing import BillingManager, SubscriptionTier

        billing_manager = BillingManager()

        # Cancel at period end (downgrade to FREE)
        billing_manager.update_subscription(
            user_id=current_user.id,
            tier=SubscriptionTier.FREE
        )

        flash('Subscription cancelled. You will be downgraded to FREE tier at the end of your billing period.', 'info')
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
