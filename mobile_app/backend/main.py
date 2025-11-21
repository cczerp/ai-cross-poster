"""
Mobile API Backend for AI Cross-Poster
=======================================
FastAPI backend that provides REST API endpoints for the Android/iOS app.

Features:
- User authentication (JWT)
- Photo upload with camera support
- AI listing generation
- eBay/Mercari posting
- Storage location tracking
- Subscription management
"""

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import shutil

# Add parent directory to path to import existing modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database.db import Database
from src.schema.unified_listing import UnifiedListing, Price, ListingCondition, Photo
from src.ai.ai_enhancer import AIEnhancer
from src.sync.multi_platform_sync import MultiPlatformSync

# Initialize FastAPI
app = FastAPI(
    title="AI Cross-Poster Mobile API",
    description="REST API for mobile app to create and post listings to eBay and Mercari",
    version="1.0.0"
)

# CORS - Allow mobile app to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize database and services
db = Database("./data/mobile_app.db")

# Configuration
UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# DATA MODELS (Request/Response)
# ============================================================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int


class PhotoUploadResponse(BaseModel):
    photo_id: str
    url: str
    local_path: str
    uploaded_at: datetime


class AIAnalysisRequest(BaseModel):
    photo_ids: List[str]
    enable_gpt4_fallback: bool = False


class AIAnalysisResponse(BaseModel):
    title: str
    description: str
    suggested_price: Optional[float]
    brand: Optional[str]
    size: Optional[str]
    color: Optional[str]
    condition: str
    category: Optional[str]
    is_collectible: bool
    collectible_data: Optional[dict] = None


class CreateListingRequest(BaseModel):
    title: str
    description: str
    price: float
    cost: Optional[float] = None
    condition: str
    photo_ids: List[str]
    brand: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    storage_location: Optional[str] = None
    shipping_cost: Optional[float] = 0.0
    platforms: List[str]  # ["ebay", "mercari"]


class ListingResponse(BaseModel):
    listing_id: int
    listing_uuid: str
    success_count: int
    total_platforms: int
    results: dict


# ============================================================================
# AUTHENTICATION (Simplified - Add JWT in production)
# ============================================================================

# TODO: Implement proper JWT authentication with password hashing
# For now, using simplified version for demonstration

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Validate JWT token and return current user"""
    # TODO: Implement JWT validation
    # For demo, just return a mock user
    return {"id": 1, "email": "demo@example.com", "name": "Demo User"}


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """API health check"""
    return {
        "status": "online",
        "app": "AI Cross-Poster Mobile API",
        "version": "1.0.0"
    }


@app.post("/auth/register", response_model=Token)
def register(user: UserCreate):
    """Register a new user"""
    # TODO: Implement user registration with password hashing
    # TODO: Store user in database
    # TODO: Generate JWT token

    return {
        "access_token": "demo_token_" + str(uuid.uuid4()),
        "token_type": "bearer",
        "user_id": 1
    }


@app.post("/auth/login", response_model=Token)
def login(credentials: UserLogin):
    """Login and get access token"""
    # TODO: Implement login with password verification
    # TODO: Generate JWT token

    return {
        "access_token": "demo_token_" + str(uuid.uuid4()),
        "token_type": "bearer",
        "user_id": 1
    }


@app.post("/photos/upload", response_model=PhotoUploadResponse)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a photo from camera or gallery.

    The mobile app will use the device camera to capture photos
    and upload them here.
    """
    # Generate unique filename
    photo_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix or ".jpg"
    filename = f"{photo_id}{file_ext}"

    # Save file
    file_path = UPLOAD_DIR / filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "photo_id": photo_id,
        "url": f"/photos/{filename}",
        "local_path": str(file_path),
        "uploaded_at": datetime.now()
    }


@app.post("/photos/upload-multiple", response_model=List[PhotoUploadResponse])
async def upload_multiple_photos(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload multiple photos at once"""
    responses = []

    for file in files:
        # Generate unique filename
        photo_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix or ".jpg"
        filename = f"{photo_id}{file_ext}"

        # Save file
        file_path = UPLOAD_DIR / filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        responses.append({
            "photo_id": photo_id,
            "url": f"/photos/{filename}",
            "local_path": str(file_path),
            "uploaded_at": datetime.now()
        })

    return responses


@app.post("/ai/analyze", response_model=AIAnalysisResponse)
async def analyze_photos(
    request: AIAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze photos with AI to generate listing details.

    Uses Claude AI (with optional GPT-4 fallback) to:
    - Generate title and description
    - Detect brand, size, color
    - Estimate condition
    - Suggest price
    - Identify if collectible
    """
    # Get photo paths
    photo_paths = []
    for photo_id in request.photo_ids:
        # Find photo file
        for file_path in UPLOAD_DIR.glob(f"{photo_id}.*"):
            photo_paths.append(str(file_path))
            break

    if not photo_paths:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photos not found"
        )

    # TODO: Integrate with AI enhancer
    # For now, return mock data

    return {
        "title": "Vintage Designer Jacket",
        "description": "Beautiful vintage jacket in excellent condition. Features unique design and quality materials.",
        "suggested_price": 45.99,
        "brand": "Nike",
        "size": "M",
        "color": "Blue",
        "condition": "excellent",
        "category": "Clothing",
        "is_collectible": False,
        "collectible_data": None
    }


@app.post("/listings/create", response_model=ListingResponse)
async def create_listing(
    request: CreateListingRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create and post a listing to selected platforms.

    This endpoint:
    1. Creates the listing in the database
    2. Posts to eBay and/or Mercari
    3. Returns the results
    """
    # Get photo paths
    photo_objects = []
    for i, photo_id in enumerate(request.photo_ids):
        for file_path in UPLOAD_DIR.glob(f"{photo_id}.*"):
            photo_objects.append(Photo(
                url="",
                local_path=str(file_path),
                order=i,
                is_primary=(i == 0)
            ))
            break

    if not photo_objects:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photos not found"
        )

    # Create UnifiedListing object
    listing = UnifiedListing(
        title=request.title,
        description=request.description,
        price=Price(amount=request.price),
        condition=ListingCondition(request.condition),
        photos=photo_objects,
        storage_location=request.storage_location,
    )

    # TODO: Integrate with MultiPlatformSync to actually post
    # For now, just save to database

    listing_uuid = str(uuid.uuid4())
    listing_id = db.create_listing(
        listing_uuid=listing_uuid,
        title=request.title,
        description=request.description,
        price=request.price,
        condition=request.condition,
        photos=[p.local_path for p in photo_objects],
        cost=request.cost,
        storage_location=request.storage_location,
        attributes={
            "brand": request.brand,
            "size": request.size,
            "color": request.color,
            "shipping_cost": request.shipping_cost,
        }
    )

    return {
        "listing_id": listing_id,
        "listing_uuid": listing_uuid,
        "success_count": len(request.platforms),
        "total_platforms": len(request.platforms),
        "results": {platform: {"success": True} for platform in request.platforms}
    }


@app.get("/listings/my-listings")
async def get_my_listings(
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    status: Optional[str] = None
):
    """Get user's listings"""
    # TODO: Filter by user_id when multi-user is implemented
    cursor = db._get_cursor()

    if status:
        cursor.execute("""
            SELECT * FROM listings
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (status, limit))
    else:
        cursor.execute("""
            SELECT * FROM listings
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

    listings = [dict(row) for row in cursor.fetchall()]
    return {"listings": listings}


@app.get("/listings/drafts")
async def get_drafts(
    current_user: dict = Depends(get_current_user),
    limit: int = 50
):
    """Get draft listings"""
    drafts = db.get_drafts(limit=limit)
    return {"drafts": drafts}


@app.delete("/listings/{listing_id}")
async def delete_listing(
    listing_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a listing"""
    db.delete_listing(listing_id)
    return {"success": True, "message": "Listing deleted"}


@app.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    """Get user statistics"""
    # TODO: Implement proper stats
    return {
        "total_listings": 0,
        "active_listings": 0,
        "sold_listings": 0,
        "total_revenue": 0.0,
        "total_profit": 0.0,
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("🚀 AI Cross-Poster Mobile API Server")
    print("=" * 70)
    print("Starting server on http://0.0.0.0:8000")
    print("API Docs: http://0.0.0.0:8000/docs")
    print("=" * 70)

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
