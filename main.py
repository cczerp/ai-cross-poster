#!/usr/bin/env python3
"""
AI Cross-Poster - Main CLI Application
======================================
Unified menu-driven interface for creating, enhancing, and publishing listings.
"""
###   TO ADD 
# --------------------------------------------------------------
# CROSS-LISTER SCAFFOLD (COMMENTED OUT FOR SAFE INSERTION)
# --------------------------------------------------------------

# from utils.playwright_setup import get_browser
# from listing_data import ListingData
# from platforms.mercari import Mercari
# from platforms.poshmark import Poshmark
# from platforms.facebook import Facebook
# from platforms.ebay import Ebay

# def run_cross_lister_example():
#     """
#     This is an example scaffold showing how the cross-lister works.
#     All lines are commented out so you can paste this block anywhere
#     without affecting your current code.
#     Claude can safely uncomment and integrate when you're ready.
#     """

#     # Launch browser
#     # pw, browser, context, page = get_browser(headless=False)

#     # Example listing data object
#     # data = ListingData(
#     #     title="Vintage Levi's Denim Jacket",
#     #     description="Classic 90s denim jacket in excellent shape.",
#     #     price=45.00,
#     #     condition="Good",
#     #     images=[
#     #         "images/jacket1.jpg",
#     #         "images/jacket2.jpg"
#     #     ]
#     # )

#     # Platform modules (all optional to enable later)
#     # mercari = Mercari(page)
#     # posh = Poshmark(page)
#     # fb = Facebook(page)
#     # ebay = Ebay(page)

#     # ---- LOGIN STEPS (enable as needed) ----
#     # await mercari.login()
#     # await posh.login()
#     # await fb.login()
#     # await ebay.login()

#     # ---- LISTING CREATION STEPS ----
#     # await mercari.create_listing(data)
#     # await posh.create_listing(data)
#     # await fb.create_listing(data)
#     # await ebay.create_listing(data)

# --------------------------------------------------------------
# END OF CROSS-LISTER SCAFFOLD
# --------------------------------------------------------------

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from src.schema import (
    UnifiedListing,
    Photo,
    Price,
    Shipping,
    ItemSpecifics,
    Category,
    SEOData,
    ListingCondition,
    ShippingService,
)
from src.enhancer import AIEnhancer
from src.publisher import (
    CrossPlatformPublisher,
    ListingPreviewer,
    confirm_publish,
)

# Load environment variables
load_dotenv()

# Global state
current_listing = None
publisher = None
ai_enhancer = None
previewer = ListingPreviewer()


def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print the application header"""
    print("="*70)
    print("🚀 AI CROSS-POSTER - Cross-Platform Listing Tool")
    print("="*70)
    print()


def print_menu():
    """Print the main menu"""
    print("\n📋 MAIN MENU")
    print("-"*70)
    print("1️⃣  Create New Listing (Manual)")
    print("2️⃣  Create Listing from Photos (AI Analysis)")
    print("3️⃣  Enhance Current Listing with AI")
    print("4️⃣  Preview Current Listing")
    print("5️⃣  Publish to eBay")
    print("6️⃣  Publish to Mercari")
    print("7️⃣  Publish to All Platforms")
    print("8️⃣  View Publishing History")
    print("9️⃣  Load Example Listing")
    print("0️⃣  Exit")
    print("-"*70)


def initialize_services():
    """Initialize publisher and AI enhancer"""
    global publisher, ai_enhancer

    print("🔧 Initializing services...")

    try:
        publisher = CrossPlatformPublisher.from_env(auto_enhance=False)
        print("✅ Publisher initialized")
    except Exception as e:
        print(f"⚠️  Publisher initialization warning: {e}")
        publisher = None

    try:
        ai_enhancer = AIEnhancer.from_env()
        print("✅ AI enhancer initialized")
    except Exception as e:
        print(f"⚠️  AI enhancer initialization warning: {e}")
        ai_enhancer = None

    print()


def get_input(prompt, default=None):
    """Get user input with optional default"""
    if default:
        value = input(f"{prompt} [{default}]: ").strip()
        return value if value else default
    return input(f"{prompt}: ").strip()


def get_photos():
    """Get photo information from user"""
    photos = []
    print("\n📸 Photo Setup")
    print("Enter photo paths or URLs (leave blank when done)")

    while True:
        path = get_input(f"  Photo #{len(photos)+1} (local path or URL, or blank to finish)")

        if not path:
            break

        is_primary = len(photos) == 0  # First photo is primary
        if len(photos) > 0:
            primary = get_input(f"  Make this the primary photo? (y/n)", "n")
            is_primary = primary.lower() in ['y', 'yes']

        # Determine if it's a local path or URL
        if path.startswith('http://') or path.startswith('https://'):
            photo = Photo(url=path, order=len(photos), is_primary=is_primary)
        else:
            photo = Photo(
                local_path=path,
                url=f"https://example.com/photo{len(photos)}.jpg",  # Placeholder
                order=len(photos),
                is_primary=is_primary
            )

        photos.append(photo)

    return photos


def create_listing_manual():
    """Create a listing manually"""
    global current_listing

    print("\n" + "="*70)
    print("📝 CREATE NEW LISTING (MANUAL)")
    print("="*70)

    # Basic info
    title = get_input("\nTitle (80 chars max)")
    if len(title) > 80:
        print(f"⚠️  Title is {len(title)} characters (max 80)")

    description = get_input("\nDescription")

    # Price
    price_amount = float(get_input("Price ($)"))
    compare_at = get_input("Compare at price ($ - optional, leave blank to skip)")
    compare_at_price = float(compare_at) if compare_at else None

    # Condition
    print("\nCondition:")
    conditions = list(ListingCondition)
    for i, cond in enumerate(conditions, 1):
        print(f"  {i}. {cond.value.replace('_', ' ').title()}")

    cond_choice = int(get_input("Choose condition (1-9)", "5"))
    condition = conditions[cond_choice - 1]

    # Photos
    photos = get_photos()

    # Item specifics
    print("\n🏷️  Item Specifics (optional, press Enter to skip)")
    brand = get_input("  Brand")
    size = get_input("  Size")
    color = get_input("  Color")
    model = get_input("  Model")

    item_specifics = ItemSpecifics(
        brand=brand if brand else None,
        size=size if size else None,
        color=color if color else None,
        model=model if model else None,
    )

    # Shipping
    shipping_cost_input = get_input("\n📦 Shipping cost ($, or 0 for free)", "5.00")
    shipping_cost = float(shipping_cost_input) if shipping_cost_input else 5.00

    # Create listing
    current_listing = UnifiedListing(
        title=title,
        description=description,
        price=Price(
            amount=price_amount,
            compare_at_price=compare_at_price,
        ),
        condition=condition,
        photos=photos,
        item_specifics=item_specifics,
        shipping=Shipping(cost=shipping_cost),
    )

    print("\n✅ Listing created successfully!")
    input("\nPress Enter to continue...")


def create_listing_from_photos():
    """Create listing using AI photo analysis"""
    global current_listing

    if not ai_enhancer:
        print("\n❌ AI enhancer not available. Check your API keys in .env")
        input("\nPress Enter to continue...")
        return

    print("\n" + "="*70)
    print("📸 CREATE LISTING FROM PHOTOS (AI)")
    print("="*70)

    # Get photos
    photos = get_photos()

    if not photos:
        print("\n❌ No photos provided")
        input("\nPress Enter to continue...")
        return

    # Get basic info that AI can't determine
    price_amount = float(get_input("\nPrice ($)"))

    print("\nCondition:")
    conditions = list(ListingCondition)
    for i, cond in enumerate(conditions, 1):
        print(f"  {i}. {cond.value.replace('_', ' ').title()}")
    cond_choice = int(get_input("Choose condition (1-9)", "5"))
    condition = conditions[cond_choice - 1]

    shipping_cost = float(get_input("Shipping cost ($)", "5.00"))

    # Create minimal listing
    current_listing = UnifiedListing(
        title="AI Generated",
        description="AI Generated",
        price=Price(amount=price_amount),
        condition=condition,
        photos=photos,
        shipping=Shipping(cost=shipping_cost),
    )

    # Enhance with AI
    print("\n🤖 Analyzing photos with AI...")
    current_listing = ai_enhancer.enhance_listing(
        current_listing,
        target_platform="general",
        force=True
    )

    print("\n✅ Listing created from AI analysis!")
    print(f"\nGenerated Title: {current_listing.title}")
    print(f"AI Provider: {current_listing.ai_provider}")

    input("\nPress Enter to continue...")


def enhance_current_listing():
    """Enhance the current listing with AI"""
    global current_listing

    if not current_listing:
        print("\n❌ No current listing. Create one first.")
        input("\nPress Enter to continue...")
        return

    if not ai_enhancer:
        print("\n❌ AI enhancer not available. Check your API keys in .env")
        input("\nPress Enter to continue...")
        return

    print("\n" + "="*70)
    print("✨ ENHANCE WITH AI")
    print("="*70)

    print("\nTarget platform:")
    print("  1. General")
    print("  2. eBay")
    print("  3. Mercari")

    platform_choice = int(get_input("Choose platform (1-3)", "1"))
    platforms = ["general", "ebay", "mercari"]
    target_platform = platforms[platform_choice - 1]

    print(f"\n🤖 Enhancing listing for {target_platform}...")
    current_listing = ai_enhancer.enhance_listing(
        current_listing,
        target_platform=target_platform,
        force=True
    )

    print("\n✅ Listing enhanced successfully!")
    print(f"AI Provider: {current_listing.ai_provider}")

    input("\nPress Enter to continue...")


def preview_current_listing():
    """Preview the current listing"""
    if not current_listing:
        print("\n❌ No current listing. Create one first.")
        input("\nPress Enter to continue...")
        return

    print()
    previewer.print_preview(current_listing)
    input("\nPress Enter to continue...")


def publish_to_platform(platform_name):
    """Publish to a specific platform"""
    global current_listing

    if not current_listing:
        print("\n❌ No current listing. Create one first.")
        input("\nPress Enter to continue...")
        return

    if not publisher:
        print("\n❌ Publisher not available. Check your credentials in .env")
        input("\nPress Enter to continue...")
        return

    print("\n" + "="*70)
    print(f"📤 PUBLISH TO {platform_name.upper()}")
    print("="*70)

    # Show preview first
    if platform_name.lower() == "ebay":
        preview = previewer.preview_for_ebay(current_listing)
    elif platform_name.lower() == "mercari":
        preview = previewer.preview_for_mercari(current_listing)
    else:
        preview = None

    if preview:
        print(f"\n📊 {platform_name} Preview:")
        print(f"  Title: {preview['title']}")
        print(f"  Price: {preview['price']}")
        print(f"  Photos: {preview['photos']}")

        if preview.get('issues'):
            print(f"\n  ⚠️  Issues:")
            for issue in preview['issues']:
                print(f"    {issue}")

    # Confirm
    confirm = get_input(f"\n✅ Publish to {platform_name}? (yes/no)", "yes")

    if confirm.lower() not in ['yes', 'y']:
        print("\n❌ Cancelled")
        input("\nPress Enter to continue...")
        return

    # Publish
    print(f"\n📤 Publishing to {platform_name}...")

    try:
        if platform_name.lower() == "ebay":
            result = publisher.publish_to_ebay(current_listing)
        elif platform_name.lower() == "mercari":
            result = publisher.publish_to_mercari(current_listing)
        else:
            print(f"\n❌ Unknown platform: {platform_name}")
            input("\nPress Enter to continue...")
            return

        if result.success:
            print(f"\n✅ Published successfully!")
            print(f"   Listing ID: {result.listing_id}")
            if result.listing_url:
                print(f"   URL: {result.listing_url}")
        else:
            print(f"\n❌ Publishing failed:")
            print(f"   Error: {result.error}")

    except Exception as e:
        print(f"\n❌ Error: {e}")

    input("\nPress Enter to continue...")


def publish_to_all_platforms():
    """Publish to all platforms"""
    global current_listing

    if not current_listing:
        print("\n❌ No current listing. Create one first.")
        input("\nPress Enter to continue...")
        return

    if not publisher:
        print("\n❌ Publisher not available. Check your credentials in .env")
        input("\nPress Enter to continue...")
        return

    print("\n" + "="*70)
    print("📤 PUBLISH TO ALL PLATFORMS")
    print("="*70)

    # Show full preview
    previewer.print_preview(current_listing)

    # Confirm
    if not confirm_publish(current_listing):
        print("\n❌ Cancelled")
        input("\nPress Enter to continue...")
        return

    # Publish
    print("\n📤 Publishing to all platforms...")
    results = publisher.publish_to_all(current_listing)

    print("\n" + "="*70)
    print("📊 RESULTS")
    print("="*70)

    for platform, result in results.items():
        if result.success:
            print(f"\n✅ {platform}: Published successfully!")
            print(f"   Listing ID: {result.listing_id}")
            if result.listing_url:
                print(f"   URL: {result.listing_url}")
        else:
            print(f"\n❌ {platform}: Failed")
            print(f"   Error: {result.error}")

    input("\nPress Enter to continue...")


def view_history():
    """View publishing history"""
    if not publisher:
        print("\n❌ Publisher not available.")
        input("\nPress Enter to continue...")
        return

    print("\n" + "="*70)
    print("📊 PUBLISHING HISTORY")
    print("="*70)

    history = publisher.get_publish_history()

    if not history:
        print("\nNo publishing history yet.")
    else:
        for entry in history:
            status = "✅" if entry["success"] else "❌"
            print(f"\n{status} {entry['platform']}: {entry['listing_title']}")
            print(f"   Time: {entry['timestamp']}")
            if entry.get('listing_id'):
                print(f"   ID: {entry['listing_id']}")
            if entry.get('error'):
                print(f"   Error: {entry['error']}")

        print(f"\n📈 Overall Success Rate: {publisher.get_success_rate():.1f}%")

    input("\nPress Enter to continue...")


def load_example_listing():
    """Load an example listing"""
    global current_listing

    print("\n" + "="*70)
    print("📦 LOAD EXAMPLE LISTING")
    print("="*70)

    current_listing = UnifiedListing(
        title="Nike Air Jordan 1 Retro High OG Black Red Size 10",
        description="""Classic Nike Air Jordan 1 in the iconic Black/Red "Bred" colorway.

These sneakers are in excellent condition with minimal wear. The leather is
supple with no creasing or cracking. All original branding intact.

Includes:
- Original box
- Extra laces
- Authentication card

Perfect for collectors or anyone wanting to add a piece of sneaker history
to their collection.""",
        price=Price(amount=150.00, compare_at_price=200.00),
        condition=ListingCondition.EXCELLENT,
        photos=[
            Photo(
                url="https://example.com/photo1.jpg",
                order=0,
                is_primary=True,
            ),
            Photo(
                url="https://example.com/photo2.jpg",
                order=1,
            ),
        ],
        item_specifics=ItemSpecifics(
            brand="Nike",
            size="10",
            color="Black/Red",
            model="Air Jordan 1",
        ),
        shipping=Shipping(cost=10.00),
        sku="NIKE-AJ1-BLK-RED-10",
    )

    print("\n✅ Example listing loaded!")
    input("\nPress Enter to continue...")


def main():
    """Main application loop"""
    clear_screen()
    print_header()

    # Initialize services
    initialize_services()

    while True:
        print_menu()

        choice = get_input("\nSelect an option", "0")

        if choice == "1":
            create_listing_manual()
        elif choice == "2":
            create_listing_from_photos()
        elif choice == "3":
            enhance_current_listing()
        elif choice == "4":
            preview_current_listing()
        elif choice == "5":
            publish_to_platform("eBay")
        elif choice == "6":
            publish_to_platform("Mercari")
        elif choice == "7":
            publish_to_all_platforms()
        elif choice == "8":
            view_history()
        elif choice == "9":
            load_example_listing()
        elif choice == "0":
            print("\n👋 Thanks for using AI Cross-Poster!")
            sys.exit(0)
        else:
            print("\n❌ Invalid option. Please try again.")
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
