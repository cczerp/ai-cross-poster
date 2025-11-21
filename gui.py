#!/usr/bin/env python3
"""
AI Cross-Poster GUI
===================
Simple, beautiful GUI for cross-platform listing with collectible recognition.
"""

import os
import sys
import threading
import json
import requests
from pathlib import Path
from typing import List, Optional
import tkinter as tk
from tkinter import filedialog, messagebox
from dotenv import load_dotenv

try:
    import customtkinter as ctk
except ImportError:
    print("Installing CustomTkinter...")
    os.system(f"{sys.executable} -m pip install customtkinter")
    import customtkinter as ctk

from src.schema import (
    UnifiedListing,
    Photo,
    Price,
    ListingCondition,
    Shipping,
    ItemSpecifics,
)
from src.collectibles import identify_collectible, detect_attributes
from src.sync import MultiPlatformSyncManager
from src.shopping import quick_lookup, profit_calculator, compare_prices
from src.database import get_db
from src.notifications import NotificationManager

# Load environment
load_dotenv()

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AIListerGUI(ctk.CTk):
    """Main GUI Application"""

    def __init__(self):
        super().__init__()

        # Configure window
        self.title("AI Cross-Poster - Collectible Listing Tool")
        self.geometry("1200x800")

        # Initialize services
        self.db = get_db()
        self.sync_manager = None
        self.notification_manager = None
        self.photos = []
        self.current_listing = None
        self.collectible_data = None
        self.is_collectible = False  # Track if Gemini detected collectible
        self.gemini_analysis = None  # Store Gemini's analysis

        # Create UI
        self.create_widgets()
        self.initialize_services()

    def initialize_services(self):
        """Initialize background services"""
        def init():
            try:
                self.sync_manager = MultiPlatformSyncManager.from_env()
                self.notification_manager = NotificationManager.from_env()
                self.update_status("✅ Services initialized")
            except Exception as e:
                self.update_status(f"⚠️ Service init warning: {e}")

        threading.Thread(target=init, daemon=True).start()

    def create_widgets(self):
        """Create all GUI widgets"""
        # Header
        header = ctk.CTkLabel(
            self,
            text="🚀 AI Cross-Poster",
            font=("Arial Bold", 28),
        )
        header.pack(pady=20)

        # Tabview (expands to fill window)
        self.tabview = ctk.CTkTabview(self, width=1150)
        self.tabview.pack(pady=10, padx=20, fill="both", expand=True)

        # Create tabs
        self.tabview.add("📦 Create Listing")
        self.tabview.add("💾 Drafts")
        self.tabview.add("🔍 Identify Collectible")
        self.tabview.add("🛒 Shopping Mode")
        self.tabview.add("📋 My Listings")
        self.tabview.add("🔔 Notifications")

        # Build each tab
        self.build_create_listing_tab()
        self.build_drafts_tab()
        self.build_identify_collectible_tab()
        self.build_shopping_mode_tab()
        self.build_my_listings_tab()
        self.build_notifications_tab()

        # Status bar
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            font=("Arial", 12),
        )
        self.status_label.pack(pady=10)

    # ========================================================================
    # CREATE LISTING TAB
    # ========================================================================

    def build_create_listing_tab(self):
        """Build the create listing tab"""
        tab = self.tabview.tab("📦 Create Listing")

        # Left side - Photo upload
        left_frame = ctk.CTkFrame(tab, width=400)
        left_frame.pack(side="left", fill="both", expand=False, padx=10, pady=10)

        ctk.CTkLabel(
            left_frame,
            text="Photos",
            font=("Arial Bold", 18),
        ).pack(pady=10)

        # Photo list
        self.photo_listbox = tk.Listbox(left_frame, height=15, bg="#2b2b2b", fg="white")
        self.photo_listbox.pack(fill="both", expand=True, padx=10, pady=5)

        # Photo buttons
        btn_frame = ctk.CTkFrame(left_frame)
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame,
            text="➕ Add Photos",
            command=self.add_photos,
            width=120,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="🗑️ Remove",
            command=self.remove_photo,
            width=120,
        ).pack(side="left", padx=5)

        # Right side - Listing details
        right_frame = ctk.CTkFrame(tab)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            right_frame,
            text="Listing Details",
            font=("Arial Bold", 18),
        ).pack(pady=10)

        # Scrollable frame for form (auto-sizes to window)
        scroll_frame = ctk.CTkScrollableFrame(right_frame, width=600)
        scroll_frame.pack(fill="both", expand=True, padx=10)

        # Title
        ctk.CTkLabel(scroll_frame, text="Title:").pack(anchor="w", pady=(10, 0))
        self.title_entry = ctk.CTkEntry(scroll_frame, width=500, placeholder_text="Item title (80 chars max)")
        self.title_entry.pack(pady=5)

        # Description (AI-generated)
        ctk.CTkLabel(scroll_frame, text="Description (AI-Generated):").pack(anchor="w", pady=(10, 0))
        self.description_text = ctk.CTkTextbox(scroll_frame, width=500, height=150)
        self.description_text.pack(pady=5)
        self.description_text.insert("1.0", "Add photos to auto-generate description...")

        # Price
        price_frame = ctk.CTkFrame(scroll_frame)
        price_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(price_frame, text="Price ($):").pack(side="left", padx=5)
        self.price_entry = ctk.CTkEntry(price_frame, width=100, placeholder_text="0.00")
        self.price_entry.pack(side="left", padx=5)

        ctk.CTkLabel(price_frame, text="Cost ($):").pack(side="left", padx=5)
        self.cost_entry = ctk.CTkEntry(price_frame, width=100, placeholder_text="0.00")
        self.cost_entry.pack(side="left", padx=5)

        # Condition
        ctk.CTkLabel(scroll_frame, text="Condition:").pack(anchor="w", pady=(10, 0))
        self.condition_var = tk.StringVar(value="excellent")
        conditions = ["new", "like_new", "excellent", "good", "fair", "poor"]
        self.condition_menu = ctk.CTkOptionMenu(
            scroll_frame,
            variable=self.condition_var,
            values=conditions,
            width=200,
        )
        self.condition_menu.pack(anchor="w", pady=5)

        # Brand, Size, Color
        details_frame = ctk.CTkFrame(scroll_frame)
        details_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(details_frame, text="Brand:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.brand_entry = ctk.CTkEntry(details_frame, width=150, placeholder_text="Brand")
        self.brand_entry.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(details_frame, text="Size:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.size_entry = ctk.CTkEntry(details_frame, width=150, placeholder_text="Size")
        self.size_entry.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(details_frame, text="Color:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.color_entry = ctk.CTkEntry(details_frame, width=150, placeholder_text="Color")
        self.color_entry.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkLabel(details_frame, text="Storage Location:").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.storage_location_entry = ctk.CTkEntry(details_frame, width=150, placeholder_text="e.g., A1, B2")
        self.storage_location_entry.grid(row=1, column=3, padx=5, pady=5)

        # Shipping
        ctk.CTkLabel(scroll_frame, text="Shipping Cost ($):").pack(anchor="w", pady=(10, 0))
        self.shipping_entry = ctk.CTkEntry(scroll_frame, width=100, placeholder_text="0.00 for free")
        self.shipping_entry.pack(anchor="w", pady=5)

        # Inventory Management Section
        inventory_section = ctk.CTkFrame(scroll_frame)
        inventory_section.pack(pady=15, fill="x")

        ctk.CTkLabel(
            inventory_section,
            text="📦 Inventory Management",
            font=("Arial Bold", 14),
        ).pack(pady=(5, 10))

        inventory_frame = ctk.CTkFrame(inventory_section)
        inventory_frame.pack(fill="x", pady=5)

        # Storage Location (primary for 1-to-1 sellers)
        ctk.CTkLabel(inventory_frame, text="Storage Location:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.location_entry = ctk.CTkEntry(inventory_frame, width=150, placeholder_text="B1, C2, etc.")
        self.location_entry.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(
            inventory_frame,
            text="(Where you put this item - e.g., Bin B1, Shelf C2)",
            font=("Arial", 10),
            text_color="gray60"
        ).grid(row=0, column=2, sticky="w", padx=5, pady=5)

        # Quantity
        ctk.CTkLabel(inventory_frame, text="Quantity:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.quantity_entry = ctk.CTkEntry(inventory_frame, width=150, placeholder_text="1")
        self.quantity_entry.insert(0, "1")  # Default to 1
        self.quantity_entry.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(
            inventory_frame,
            text="(1 for single items, >1 for multiples of same item)",
            font=("Arial", 10),
            text_color="gray60"
        ).grid(row=1, column=2, sticky="w", padx=5, pady=5)

        # AI Analysis section
        ai_section = ctk.CTkFrame(scroll_frame)
        ai_section.pack(pady=15, fill="x")

        ctk.CTkLabel(
            ai_section,
            text="AI Analysis",
            font=("Arial Bold", 14),
        ).pack(pady=(5, 10))

        # Collectible Indicator Light
        indicator_frame = ctk.CTkFrame(ai_section)
        indicator_frame.pack(pady=5)

        ctk.CTkLabel(indicator_frame, text="Collectible Status:").pack(side="left", padx=5)
        self.collectible_indicator = ctk.CTkLabel(
            indicator_frame,
            text="⚪ Not Analyzed",
            font=("Arial Bold", 12),
            text_color="gray",
        )
        self.collectible_indicator.pack(side="left", padx=5)

        # GPT-4 fallback checkbox (disabled by default to save quota)
        self.enable_gpt4_fallback = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            ai_section,
            text="Enable GPT-4 fallback for deep analysis (uses OpenAI quota)",
            variable=self.enable_gpt4_fallback,
        ).pack(pady=5)

        # All buttons in one horizontal row
        all_buttons_frame = ctk.CTkFrame(ai_section)
        all_buttons_frame.pack(pady=10)

        # Left side - Action buttons
        ctk.CTkButton(
            all_buttons_frame,
            text="💾 Save as Draft",
            command=self.save_as_draft,
            fg_color="gray",
            hover_color="darkgray",
            height=50,
            width=170,
            font=("Arial Bold", 12),
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            all_buttons_frame,
            text="🚀 Post Now",
            command=self.post_listing,
            fg_color="green",
            hover_color="darkgreen",
            height=50,
            width=170,
            font=("Arial Bold", 12),
        ).pack(side="left", padx=3)

        # Middle - Main AI Analysis (Gemini)
        ctk.CTkButton(
            all_buttons_frame,
            text="🤖 Analyze with AI",
            command=self.ai_enhance_listing,
            fg_color="purple",
            hover_color="darkviolet",
            height=50,
            width=170,
            font=("Arial Bold", 12),
        ).pack(side="left", padx=3)

        # Deep Collectible Analysis (Claude) - initially disabled
        self.deep_analysis_button = ctk.CTkButton(
            all_buttons_frame,
            text="🔍 Identify Collectible",
            command=self.deep_collectible_analysis,
            fg_color="#FF6B00",  # Orange
            hover_color="#CC5500",
            height=50,
            width=170,
            font=("Arial Bold", 12),
            state="disabled",  # Disabled until Gemini detects collectible
        )
        self.deep_analysis_button.pack(side="left", padx=3)

        # Regenerate description
        ctk.CTkButton(
            all_buttons_frame,
            text="🔄 Regenerate Desc",
            command=self.regenerate_description,
            fg_color="orange",
            hover_color="darkorange",
            height=50,
            width=170,
            font=("Arial Bold", 12),
        ).pack(side="left", padx=3)

        # Platform selection
        ctk.CTkLabel(scroll_frame, text="Post to Platforms:").pack(anchor="w", pady=(10, 0))
        platform_frame = ctk.CTkFrame(scroll_frame)
        platform_frame.pack(anchor="w", pady=5)

        self.ebay_var = tk.BooleanVar(value=True)
        self.mercari_var = tk.BooleanVar(value=True)

        ctk.CTkCheckBox(platform_frame, text="eBay", variable=self.ebay_var).pack(side="left", padx=10)
        ctk.CTkCheckBox(platform_frame, text="Mercari", variable=self.mercari_var).pack(side="left", padx=10)

    def add_photos(self):
        """Add photos to listing"""
        files = filedialog.askopenfilenames(
            title="Select Photos",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif"), ("All files", "*.*")]
        )

        for file in files:
            self.photos.append(file)
            self.photo_listbox.insert(tk.END, Path(file).name)

        if files:
            self.update_status(f"Added {len(files)} photo(s) - Click 'Analyze with AI' to continue")

    def remove_photo(self):
        """Remove selected photo"""
        selection = self.photo_listbox.curselection()
        if selection:
            idx = selection[0]
            del self.photos[idx]
            self.photo_listbox.delete(idx)
            self.update_status("Photo removed")

    def ai_enhance_listing(self):
        """Use Gemini AI for fast item classification (PRIMARY ANALYZER)"""
        if not self.photos:
            messagebox.showwarning("No Photos", "Please add photos first!")
            return

        self.update_status("🤖 Analyzing with Gemini AI...")

        def enhance():
            try:
                # Validate photos exist
                for photo_path in self.photos:
                    if not os.path.exists(photo_path):
                        raise FileNotFoundError(f"Photo not found: {photo_path}")

                # Create photo objects
                photo_objects = [
                    Photo(url="", local_path=p, order=i, is_primary=(i == 0))
                    for i, p in enumerate(self.photos)
                ]

                # Use Gemini for fast classification
                from src.ai.gemini_classifier import GeminiClassifier
                classifier = GeminiClassifier.from_env()

                self.after(0, lambda: self.update_status("🤖 Gemini analyzing..."))
                analysis = classifier.analyze_item(photo_objects)

                # Check for errors
                if "error" in analysis:
                    error_msg = analysis.get("error", "Unknown error")
                    self.after(0, lambda: messagebox.showerror(
                        "Gemini AI Error",
                        f"Gemini could not analyze the photos:\n\n{error_msg}\n\nPlease check:\n- GOOGLE_AI_API_KEY or GEMINI_API_KEY is set in .env\n- Photos are valid images\n- Internet connection"
                    ))
                    self.after(0, lambda: self.update_status(f"❌ Gemini failed: {error_msg}"))
                    return

                # Store analysis
                self.gemini_analysis = analysis
                self.is_collectible = analysis.get("collectible", False)

                # Update UI on main thread
                self.after(0, lambda: self.apply_gemini_classification(analysis))

            except FileNotFoundError as e:
                self.after(0, lambda: messagebox.showerror("File Error", str(e)))
                self.after(0, lambda: self.update_status("❌ Photo file not found"))
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                self.after(0, lambda: messagebox.showerror(
                    "AI Error",
                    f"Unexpected error:\n\n{str(e)}\n\nDetails:\n{error_details[:500]}"
                ))
                self.after(0, lambda: self.update_status(f"❌ AI failed: {e}"))

        threading.Thread(target=enhance, daemon=True).start()

    def apply_gemini_classification(self, analysis):
        """Apply Gemini's classification results to form"""
        # Fill in basic fields
        if analysis.get("brand"):
            self.brand_entry.delete(0, tk.END)
            self.brand_entry.insert(0, analysis["brand"])

        if analysis.get("size"):
            self.size_entry.delete(0, tk.END)
            self.size_entry.insert(0, analysis["size"])

        if analysis.get("color"):
            self.color_entry.delete(0, tk.END)
            self.color_entry.insert(0, analysis["color"])

        # Use suggested title
        if analysis.get("suggested_title"):
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, analysis["suggested_title"][:80])

        # Use Gemini's description
        if analysis.get("description"):
            self.description_text.delete("1.0", tk.END)
            self.description_text.insert("1.0", analysis["description"])

        # Set condition
        if analysis.get("condition"):
            condition = analysis["condition"].replace(" ", "_").lower()
            if condition in ["new", "like_new", "excellent", "good", "fair", "poor"]:
                self.condition_var.set(condition)

        # Set suggested price
        if analysis.get("suggested_price") and analysis["suggested_price"] > 0:
            self.price_entry.delete(0, tk.END)
            self.price_entry.insert(0, str(analysis["suggested_price"]))

        # Update collectible indicator
        is_collectible = analysis.get("collectible", False)
        confidence = analysis.get("collectible_confidence", 0.0)

        if is_collectible:
            # Turn on collectible light
            self.collectible_indicator.configure(
                text=f"🟢 COLLECTIBLE DETECTED ({confidence:.0%} confidence)",
                text_color="green"
            )
            # Enable deep analysis button
            self.deep_analysis_button.configure(state="normal")

            # Show notification
            indicators = analysis.get("collectible_indicators", [])
            indicator_text = "\n".join([f"• {ind}" for ind in indicators[:5]])

            messagebox.showinfo(
                "Collectible Detected!",
                f"Gemini detected this may be a COLLECTIBLE item!\n\nConfidence: {confidence:.0%}\n\nIndicators:\n{indicator_text}\n\nClick '🔍 Identify Collectible' for deep authentication analysis."
            )
        else:
            # Turn off collectible light
            self.collectible_indicator.configure(
                text="⚪ Standard Item (not collectible)",
                text_color="gray"
            )
            # Keep deep analysis button disabled
            self.deep_analysis_button.configure(state="disabled")

        self.update_status(f"✅ Gemini classification complete! ({analysis.get('category', 'unknown')})")

    def apply_ai_attributes(self, attributes):
        """LEGACY: Apply Claude AttributeDetector results (kept for regenerate_description)"""
        if "error" in attributes:
            messagebox.showwarning("AI Warning", f"Partial results: {attributes['error']}")

        # Fill in the form
        if "brand" in attributes and attributes["brand"].get("name"):
            self.brand_entry.delete(0, tk.END)
            self.brand_entry.insert(0, attributes["brand"]["name"])

        if "size" in attributes and attributes["size"].get("size"):
            self.size_entry.delete(0, tk.END)
            self.size_entry.insert(0, attributes["size"]["size"])

        if "color" in attributes and attributes["color"].get("primary"):
            self.color_entry.delete(0, tk.END)
            self.color_entry.insert(0, attributes["color"]["primary"])

        # Generate title if we have item type
        if "item_type" in attributes:
            item_type = attributes["item_type"].get("specific_type", "")
            brand = attributes.get("brand", {}).get("name", "")
            color = attributes.get("color", {}).get("primary", "")
            size = attributes.get("size", {}).get("size", "")

            title_parts = [brand, color, item_type, size]
            title = " ".join([p for p in title_parts if p])

            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, title[:80])

        # Generate comprehensive description
        desc_parts = []

        # Item overview
        if "item_type" in attributes:
            item_type = attributes["item_type"].get("specific_type", "item")
            brand = attributes.get("brand", {}).get("name", "")
            if brand:
                desc_parts.append(f"This {brand} {item_type} is ")
            else:
                desc_parts.append(f"This {item_type} is ")

        # Condition
        if "condition" in attributes:
            condition = attributes['condition'].get('overall', 'good')
            if attributes['condition'].get('has_tags'):
                desc_parts.append(f"in {condition} condition with original tags attached.")
            else:
                desc_parts.append(f"in {condition} condition.")

            if attributes['condition'].get('wear_notes'):
                desc_parts.append(f" {attributes['condition']['wear_notes']}")

        desc = " ".join(desc_parts) + "\n\n"

        # Details section
        details = []
        if "size" in attributes and attributes["size"].get("size"):
            details.append(f"Size: {attributes['size']['size']}")
        if "color" in attributes and attributes["color"].get("description"):
            details.append(f"Color: {attributes['color']['description']}")
        elif "color" in attributes and attributes["color"].get("primary"):
            details.append(f"Color: {attributes['color']['primary']}")
        if "material" in attributes and attributes["material"].get("composition"):
            details.append(f"Material: {attributes['material']['composition']}")

        if details:
            desc += "\n".join(details) + "\n\n"

        # Features
        if "features" in attributes and attributes["features"].get("special"):
            desc += "Features:\n"
            for feature in attributes["features"]["special"]:
                desc += f"• {feature}\n"
            desc += "\n"

        # Style info
        if "style" in attributes and attributes["style"].get("style_type"):
            desc += f"Style: {attributes['style']['style_type']}\n"

        # Market info
        if "retail_info" in attributes and attributes["retail_info"].get("market_notes"):
            desc += f"\n{attributes['retail_info']['market_notes']}\n"

        self.description_text.delete("1.0", tk.END)
        self.description_text.insert("1.0", desc.strip())

        # Set condition
        if "condition" in attributes and attributes["condition"].get("overall"):
            condition = attributes["condition"]["overall"].replace(" ", "_").lower()
            if condition in ["new", "like_new", "excellent", "good", "fair", "poor"]:
                self.condition_var.set(condition)

        # Show which AI was used
        ai_used = attributes.get("ai_provider", "unknown").upper()
        self.update_status(f"✅ AI enhancement complete! (Used {ai_used})")
        messagebox.showinfo("Success", f"Listing enhanced with AI-detected attributes!\n\nAI Provider: {ai_used}")

    def regenerate_description(self):
        """Regenerate just the description using current form values"""
        if not self.photos:
            messagebox.showwarning("No Photos", "Please add photos first!")
            return

        self.update_status("🔄 Regenerating description...")

        def regenerate():
            try:
                from src.collectibles.attribute_detector import AttributeDetector
                import anthropic

                # Get current form values
                title = self.title_entry.get() or "Item"
                brand = self.brand_entry.get() or "Unknown brand"
                size = self.size_entry.get() or "N/A"
                color = self.color_entry.get() or "N/A"
                condition = self.condition_var.get()

                # Create a focused prompt for description only
                prompt = f"""Generate a compelling marketplace listing description for this item.

Item Details:
- Title: {title}
- Brand: {brand}
- Size: {size}
- Color: {color}
- Condition: {condition}

Write a 2-3 paragraph description that:
1. Starts with an engaging overview
2. Highlights key features and condition details
3. Mentions any wear or flaws honestly
4. Ends with a selling point

Return ONLY the description text, no JSON, no formatting, just the description."""

                # Use Claude to generate
                detector = AttributeDetector.from_env()

                if not detector.anthropic_api_key:
                    raise ValueError("No Anthropic API key found")

                # Encode first photo
                photo_b64 = detector._encode_image_to_base64(self.photos[0])
                mime_type = detector._get_image_mime_type(self.photos[0])

                headers = {
                    "x-api-key": detector.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }

                model = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")

                payload = {
                    "model": model,
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": mime_type,
                                        "data": photo_b64,
                                    }
                                }
                            ],
                        }
                    ],
                }

                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )

                if response.status_code == 200:
                    result = response.json()
                    new_description = result["content"][0]["text"]

                    # Update description
                    self.after(0, lambda: self.description_text.delete("1.0", tk.END))
                    self.after(0, lambda: self.description_text.insert("1.0", new_description.strip()))
                    self.after(0, lambda: self.update_status("✅ Description regenerated!"))
                    self.after(0, lambda: messagebox.showinfo("Success", "New description generated!"))
                else:
                    error_msg = f"API error ({response.status_code}): {response.text[:200]}"
                    self.after(0, lambda: messagebox.showerror("Error", f"Failed to regenerate:\n\n{error_msg}"))
                    self.after(0, lambda: self.update_status("❌ Regeneration failed"))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to regenerate description:\n\n{str(e)}"))
                self.after(0, lambda: self.update_status(f"❌ Regeneration failed: {e}"))

        threading.Thread(target=regenerate, daemon=True).start()

    def deep_collectible_analysis(self):
        """
        Deep collectible analysis using Claude (EXPERT MODE).

        This runs AFTER Gemini has detected a collectible.
        Claude performs expert-level:
        - Authenticity checks
        - Variant identification
        - Condition grading
        - Value justification
        - Database-level structuring
        """
        if not self.photos:
            messagebox.showwarning("No Photos", "Please add photos first!")
            return

        if not self.is_collectible:
            messagebox.showinfo(
                "Not a Collectible",
                "Gemini didn't detect this as a collectible.\n\nRun 'Analyze with AI' first, or this item may not be a collectible."
            )
            return

        self.update_status("🔍 Running deep collectible analysis with Claude...")

        def analyze():
            try:
                # Create photo objects
                photo_objects = [
                    Photo(url="", local_path=p, order=i, is_primary=(i == 0))
                    for i, p in enumerate(self.photos)
                ]

                # Use Claude for deep collectible recognition
                from src.collectibles.recognizer import CollectibleRecognizer
                recognizer = CollectibleRecognizer.from_env()

                # Check if GPT-4 fallback is enabled
                use_fallback = self.enable_gpt4_fallback.get()

                self.after(0, lambda: self.update_status("🔍 Claude analyzing collectible..."))
                is_collectible, collectible_id, analysis = recognizer.identify_and_store(
                    photo_objects,
                    force_gpt4=use_fallback
                )

                # Check for errors
                if "error" in analysis:
                    error_msg = analysis.get("error", "Unknown error")
                    raw_response = analysis.get("raw_response", "No raw response available")
                    debug_info = analysis.get("debug_info", "")

                    # Build detailed error message
                    full_error = f"Claude could not complete deep analysis:\n\n{error_msg}"
                    if debug_info:
                        full_error += f"\n\nDebug: {debug_info}"
                    if raw_response and raw_response != "No raw response available":
                        full_error += f"\n\nRaw Response:\n{raw_response[:500]}"
                    full_error += "\n\nPlease check:\n- ANTHROPIC_API_KEY is set in .env\n- Photos are clear and show item details\n- Internet connection"

                    self.after(0, lambda msg=full_error: messagebox.showerror(
                        "Deep Analysis Error",
                        msg
                    ))
                    self.after(0, lambda: self.update_status(f"❌ Deep analysis failed: {error_msg}"))
                    return

                # Store collectible data
                self.collectible_data = analysis

                # Update UI on main thread
                self.after(0, lambda: self.apply_deep_collectible_analysis(
                    is_collectible, collectible_id, analysis
                ))

            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                self.after(0, lambda: messagebox.showerror(
                    "Deep Analysis Error",
                    f"Unexpected error:\n\n{str(e)}\n\nDetails:\n{error_details[:500]}"
                ))
                self.after(0, lambda: self.update_status(f"❌ Deep analysis failed: {e}"))

        threading.Thread(target=analyze, daemon=True).start()

    def apply_deep_collectible_analysis(self, is_collectible, collectible_id, analysis):
        """Apply deep collectible analysis results to form"""
        if not is_collectible:
            messagebox.showinfo(
                "Not a Collectible",
                "After deep analysis, Claude determined this is NOT a collectible item.\n\n" +
                f"Reasoning: {analysis.get('reasoning', 'No specific reason provided')}"
            )
            # Turn off collectible indicator
            self.collectible_indicator.configure(
                text="⚪ Not a Collectible (verified)",
                text_color="gray"
            )
            return

        # Collectible confirmed!
        # Update indicator with higher confidence
        confidence = analysis.get("confidence_score", 0.0)
        self.collectible_indicator.configure(
            text=f"🟢 COLLECTIBLE VERIFIED ({confidence:.0%} confidence)",
            text_color="green"
        )

        # Update title with collector-grade details
        if analysis.get("name"):
            suggested_title = analysis["name"]
            if analysis.get("brand"):
                suggested_title = f"{analysis['brand']} {suggested_title}"
            if analysis.get("year"):
                suggested_title += f" ({analysis['year']})"

            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, suggested_title[:80])

        # Update description with detailed collectible info
        desc_parts = []

        # Opening
        desc_parts.append(f"{analysis.get('name', 'Collectible item')} - {analysis.get('why_valuable', 'Highly sought after collectible')}")
        desc_parts.append("")

        # Authentication
        if analysis.get("authentication"):
            auth = analysis["authentication"]
            desc_parts.append("🔍 AUTHENTICATION:")
            if auth.get("key_identifiers"):
                for identifier in auth["key_identifiers"][:3]:
                    desc_parts.append(f"• {identifier}")

            # Signature Analysis (CRITICAL for autographed items)
            if auth.get("has_signature") and auth.get("signature_analysis"):
                sig = auth["signature_analysis"]
                desc_parts.append("")
                desc_parts.append("✍️ SIGNATURE AUTHENTICATION:")

                # Authenticity verdict
                if sig.get("is_authentic"):
                    confidence_pct = int(sig.get("confidence", 0) * 100)
                    desc_parts.append(f"✅ LIKELY AUTHENTIC ({confidence_pct}% confidence)")
                else:
                    confidence_pct = int(sig.get("confidence", 0) * 100)
                    desc_parts.append(f"❌ LIKELY FAKE/STAMPED ({confidence_pct}% confidence)")

                # Key findings
                if sig.get("authenticity_reasoning"):
                    desc_parts.append(f"Analysis: {sig['authenticity_reasoning']}")

                # Ink characteristics
                if sig.get("ink_characteristics"):
                    ink = sig["ink_characteristics"]
                    desc_parts.append("Ink Analysis:")
                    if ink.get("bleeding"):
                        desc_parts.append(f"  • Bleeding: {ink['bleeding']}")
                    if ink.get("pressure_variation"):
                        desc_parts.append(f"  • Pressure: {ink['pressure_variation']}")

                # Placement analysis
                if sig.get("placement_style"):
                    place = sig["placement_style"]
                    if place.get("location"):
                        typical = "✓" if place.get("typical_for_player") else "⚠"
                        desc_parts.append(f"Placement: {place['location']} {typical}")

                # Red flags
                if sig.get("red_flags_found") and len(sig["red_flags_found"]) > 0:
                    desc_parts.append("⚠️ RED FLAGS:")
                    for flag in sig["red_flags_found"][:3]:
                        desc_parts.append(f"  • {flag}")

                # Recommendation
                if sig.get("recommendation"):
                    desc_parts.append(f"Recommendation: {sig['recommendation']}")

            desc_parts.append("")

        # Condition & Grading
        if analysis.get("condition"):
            desc_parts.append(f"📊 CONDITION: {analysis['condition']}")
            desc_parts.append("")

        # Rarity
        if analysis.get("rarity"):
            desc_parts.append(f"💎 RARITY: {analysis['rarity'].upper()}")
            desc_parts.append("")

        # Value
        if analysis.get("estimated_value_low") and analysis.get("estimated_value_high"):
            desc_parts.append(
                f"💰 ESTIMATED VALUE: ${analysis['estimated_value_low']} - ${analysis['estimated_value_high']}"
            )

            # Price Reasons (3 reasons explaining the price)
            if analysis.get("price_reasons"):
                desc_parts.append("")
                desc_parts.append("WHY THIS PRICE:")
                for i, reason in enumerate(analysis["price_reasons"][:3], 1):
                    desc_parts.append(f"{i}. {reason}")

            if analysis.get("market_trend"):
                desc_parts.append(f"📈 Market Trend: {analysis['market_trend']}")
            desc_parts.append("")

        # Fake Indicators (if item has fake/counterfeit markers)
        if analysis.get("fake_indicators"):
            desc_parts.append("⚠️ FAKE/COUNTERFEIT INDICATORS:")
            for i, indicator in enumerate(analysis["fake_indicators"][:3], 1):
                desc_parts.append(f"{i}. {indicator}")
            desc_parts.append("")

        # What collectors want
        if analysis.get("what_collectors_want"):
            desc_parts.append(f"What collectors look for: {analysis['what_collectors_want']}")
            desc_parts.append("")

        # Best platforms
        if analysis.get("best_platforms"):
            desc_parts.append(f"Best platforms to sell: {', '.join(analysis['best_platforms'][:3])}")

        self.description_text.delete("1.0", tk.END)
        self.description_text.insert("1.0", "\n".join(desc_parts))

        # Update price with estimated value
        if analysis.get("estimated_value_low") and analysis.get("estimated_value_high"):
            # Use midpoint as suggested price
            suggested_price = (analysis["estimated_value_low"] + analysis["estimated_value_high"]) / 2
            self.price_entry.delete(0, tk.END)
            self.price_entry.insert(0, f"{suggested_price:.2f}")

        # Update condition
        if analysis.get("condition"):
            condition = analysis["condition"].replace(" ", "_").lower()
            if condition in ["new", "like_new", "excellent", "good", "fair", "poor"]:
                self.condition_var.set(condition)

        # Show summary
        summary_parts = [
            f"Item: {analysis.get('name', 'Unknown')}",
            f"Category: {analysis.get('category', 'Unknown')}",
            f"Rarity: {analysis.get('rarity', 'Unknown')}",
            f"Condition: {analysis.get('condition', 'Unknown')}",
            f"Estimated Value: ${analysis.get('estimated_value_low', 0)} - ${analysis.get('estimated_value_high', 0)}",
        ]

        # Add signature analysis to summary if present
        if analysis.get("authentication", {}).get("has_signature"):
            sig = analysis["authentication"].get("signature_analysis", {})
            if sig:
                if sig.get("is_authentic"):
                    conf = int(sig.get("confidence", 0) * 100)
                    summary_parts.append(f"\n✍️ Signature: LIKELY AUTHENTIC ({conf}% confidence)")
                else:
                    conf = int(sig.get("confidence", 0) * 100)
                    summary_parts.append(f"\n✍️ Signature: LIKELY FAKE/STAMPED ({conf}% confidence)")
                if sig.get("recommendation"):
                    summary_parts.append(f"   {sig['recommendation']}")

        if collectible_id:
            summary_parts.append(f"\n✅ Saved to database (ID: {collectible_id})")

        messagebox.showinfo(
            "Deep Analysis Complete!",
            "Claude has verified this is a COLLECTIBLE!\n\n" + "\n".join(summary_parts)
        )

        self.update_status(f"✅ Deep collectible analysis complete! ({analysis.get('category', 'collectible')})")

    def post_listing(self):
        """Post listing to selected platforms"""
        if not self.photos:
            messagebox.showwarning("No Photos", "Please add photos first!")
            return

        if not self.title_entry.get():
            messagebox.showwarning("No Title", "Please enter a title!")
            return

        if not self.price_entry.get():
            messagebox.showwarning("No Price", "Please enter a price!")
            return

        self.update_status("📤 Posting to platforms...")

        def post():
            try:
                # Create listing object
                photo_objects = [
                    Photo(url="", local_path=p, order=i, is_primary=(i == 0))
                    for i, p in enumerate(self.photos)
                ]

                listing = UnifiedListing(
                    title=self.title_entry.get(),
                    description=self.description_text.get("1.0", tk.END).strip(),
                    price=Price(amount=float(self.price_entry.get())),
                    condition=ListingCondition(self.condition_var.get()),
                    photos=photo_objects,
                    item_specifics=ItemSpecifics(
                        brand=self.brand_entry.get() or None,
                        size=self.size_entry.get() or None,
                        color=self.color_entry.get() or None,
                    ),
                    shipping=Shipping(
                        cost=float(self.shipping_entry.get()) if self.shipping_entry.get() else 0.0
                    ),
                    quantity=int(self.quantity_entry.get()) if self.quantity_entry.get() else 1,
                    storage_location=self.location_entry.get() if self.location_entry.get() else None,
                )

                # Selected platforms
                platforms = []
                if self.ebay_var.get():
                    platforms.append("ebay")
                if self.mercari_var.get():
                    platforms.append("mercari")

                if not platforms:
                    self.after(0, lambda: messagebox.showwarning("No Platforms", "Select at least one platform!"))
                    return

                # Post to platforms
                cost = float(self.cost_entry.get()) if self.cost_entry.get() else None

                result = self.sync_manager.post_to_all_platforms(
                    listing,
                    platforms=platforms,
                    collectible_id=self.collectible_data.get("id") if self.collectible_data else None,
                    cost=cost,
                )

                # Show results
                success_count = result["success_count"]
                total = result["total_platforms"]

                # Build detailed result message
                result_msg = f"Posted to {success_count}/{total} platforms\n\n"

                # Show success/failure for each platform
                for platform, platform_result in result.get("results", {}).items():
                    if platform_result.success:
                        result_msg += f"✅ {platform.upper()}: Success\n"
                        if platform_result.listing_url:
                            result_msg += f"   URL: {platform_result.listing_url}\n"
                    else:
                        result_msg += f"❌ {platform.upper()}: Failed\n"
                        result_msg += f"   Error: {platform_result.error}\n"

                result_msg += f"\nListing ID: {result['listing_id']}"

                self.after(0, lambda: self.update_status(f"Posted to {success_count}/{total} platforms"))

                # Show appropriate dialog based on success
                if success_count > 0:
                    self.after(0, lambda msg=result_msg: messagebox.showinfo("Posting Results", msg))
                else:
                    self.after(0, lambda msg=result_msg: messagebox.showerror("Posting Failed", msg))

                # Clear form if at least one succeeded
                if success_count > 0:
                    self.after(0, self.clear_listing_form)

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to post: {e}"))
                self.after(0, lambda: self.update_status(f"❌ Post failed: {e}"))

        threading.Thread(target=post, daemon=True).start()

    def clear_listing_form(self):
        """Clear the listing form"""
        self.photos = []
        self.photo_listbox.delete(0, tk.END)
        self.title_entry.delete(0, tk.END)
        self.description_text.delete("1.0", tk.END)
        self.price_entry.delete(0, tk.END)
        self.cost_entry.delete(0, tk.END)
        self.brand_entry.delete(0, tk.END)
        self.size_entry.delete(0, tk.END)
        self.color_entry.delete(0, tk.END)
        self.storage_location_entry.delete(0, tk.END)
        self.shipping_entry.delete(0, tk.END)
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, "1")  # Reset to default
        self.location_entry.delete(0, tk.END)
        self.collectible_data = None

    def save_as_draft(self):
        """Save listing as draft for later posting"""
        if not self.photos:
            messagebox.showwarning("No Photos", "Please add photos first!")
            return

        if not self.title_entry.get():
            messagebox.showwarning("No Title", "Please enter a title!")
            return

        self.update_status("💾 Saving draft...")

        def save():
            try:
                import uuid
                import shutil
                from pathlib import Path

                # Create UUID for listing
                listing_uuid = str(uuid.uuid4())

                # Create permanent storage directory for draft photos
                draft_photos_dir = Path("data/draft_photos") / listing_uuid
                draft_photos_dir.mkdir(parents=True, exist_ok=True)

                # Copy photos to permanent storage
                permanent_photo_paths = []
                for i, photo_path in enumerate(self.photos):
                    # Get file extension
                    ext = Path(photo_path).suffix
                    # Create new filename with index
                    new_filename = f"photo_{i:02d}{ext}"
                    # Copy to permanent storage
                    permanent_path = draft_photos_dir / new_filename
                    shutil.copy2(photo_path, permanent_path)
                    # Store the permanent path
                    permanent_photo_paths.append(str(permanent_path))

                # Save to database with permanent photo paths
                listing_id = self.db.create_listing(
                    listing_uuid=listing_uuid,
                    title=self.title_entry.get(),
                    description=self.description_text.get("1.0", tk.END).strip(),
                    price=float(self.price_entry.get()) if self.price_entry.get() else 0.0,
                    condition=self.condition_var.get(),
                    photos=permanent_photo_paths,
                    collectible_id=self.collectible_data.get("id") if self.collectible_data else None,
                    cost=float(self.cost_entry.get()) if self.cost_entry.get() else None,
                    quantity=int(self.quantity_entry.get()) if self.quantity_entry.get() else 1,
                    storage_location=self.location_entry.get() if self.location_entry.get() else None,
                    attributes={
                        "brand": self.brand_entry.get(),
                        "size": self.size_entry.get(),
                        "color": self.color_entry.get(),
                        "shipping_cost": float(self.shipping_entry.get()) if self.shipping_entry.get() else 0.0,
                    }
                )

                self.after(0, lambda: self.update_status(f"✅ Draft saved with {len(permanent_photo_paths)} photos (ID: {listing_id})"))
                self.after(0, lambda: messagebox.showinfo(
                    "Draft Saved!",
                    f"Listing saved as draft!\n\nDraft ID: {listing_id}\nPhotos: {len(permanent_photo_paths)} saved\n\nYou can find it in the 'Drafts' tab."
                ))

                # Clear form
                self.after(0, self.clear_listing_form)

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to save draft: {e}"))
                self.after(0, lambda: self.update_status(f"❌ Save failed: {e}"))

        threading.Thread(target=save, daemon=True).start()

    # ========================================================================
    # DRAFTS TAB
    # ========================================================================

    def build_drafts_tab(self):
        """Build the drafts tab"""
        tab = self.tabview.tab("💾 Drafts")

        # Header with refresh and export buttons
        header_frame = ctk.CTkFrame(tab)
        header_frame.pack(pady=10, fill="x", padx=20)

        ctk.CTkLabel(
            header_frame,
            text="Saved Drafts",
            font=("Arial Bold", 18),
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            header_frame,
            text="🔄 Refresh",
            command=self.refresh_drafts,
            width=100,
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            header_frame,
            text="📤 Export to CSV",
            command=self.export_drafts_to_csv,
            width=120,
        ).pack(side="right", padx=5)

        # Scrollable frame for draft cards
        self.drafts_scroll = ctk.CTkScrollableFrame(tab, width=1000, height=600)
        self.drafts_scroll.pack(pady=10, padx=20, fill="both", expand=True)

    def refresh_drafts(self):
        """Refresh drafts from database"""
        self.update_status("Loading drafts...")

        def refresh():
            try:
                drafts = self.db.get_drafts(limit=100)
                self.after(0, lambda: self.display_drafts(drafts))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to load drafts: {e}"))

        threading.Thread(target=refresh, daemon=True).start()

    def display_drafts(self, drafts):
        """Display drafts as interactive cards"""
        # Clear existing draft cards
        for widget in self.drafts_scroll.winfo_children():
            widget.destroy()

        if not drafts:
            ctk.CTkLabel(
                self.drafts_scroll,
                text="No drafts found.\n\nCreate a listing and click '💾 Save as Draft' to save it for later.",
                font=("Arial", 14)
            ).pack(pady=20)
            return

        # Create a card for each draft
        for draft in drafts:
            # Draft card frame
            card = ctk.CTkFrame(self.drafts_scroll, fg_color="gray20", corner_radius=10)
            card.pack(pady=10, padx=10, fill="x")

            # Left side: Draft info
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=15, pady=15)

            # Title
            ctk.CTkLabel(
                info_frame,
                text=f"📦 {draft['title']}",
                font=("Arial Bold", 16),
                anchor="w"
            ).pack(fill="x")

            # Price and ID
            price_text = f"💰 ${draft['price']:.2f}"
            if draft.get('cost'):
                profit = draft['price'] - draft['cost']
                price_text += f" (Cost: ${draft['cost']:.2f}, Profit: ${profit:.2f})"

            ctk.CTkLabel(
                info_frame,
                text=price_text,
                font=("Arial", 12),
                anchor="w",
                text_color="lightgreen"
            ).pack(fill="x")

            # Details
            details = []

            # Parse attributes
            if draft.get('attributes'):
                try:
                    attrs = json.loads(draft['attributes'])
                    if attrs.get('brand'):
                        details.append(f"Brand: {attrs['brand']}")
                    if attrs.get('size'):
                        details.append(f"Size: {attrs['size']}")
                    if attrs.get('color'):
                        details.append(f"Color: {attrs['color']}")
                except:
                    pass

            details.append(f"Condition: {draft['condition']}")

            # Add storage location if available
            if draft.get('storage_location'):
                details.append(f"📍 Storage: {draft['storage_location']}")

            # Photo count
            if draft.get('photos'):
                try:
                    photos = json.loads(draft['photos'])
                    details.append(f"📷 {len(photos)} photos")
                except:
                    pass

            ctk.CTkLabel(
                info_frame,
                text=" | ".join(details),
                font=("Arial", 11),
                anchor="w",
                text_color="gray70"
            ).pack(fill="x", pady=(5, 0))

            # Description preview
            desc_preview = draft['description'][:150]
            if len(draft['description']) > 150:
                desc_preview += "..."

            ctk.CTkLabel(
                info_frame,
                text=desc_preview,
                font=("Arial", 10),
                anchor="w",
                text_color="gray60",
                wraplength=600
            ).pack(fill="x", pady=(5, 0))

            # Created date
            ctk.CTkLabel(
                info_frame,
                text=f"Created: {draft['created_at']}",
                font=("Arial", 9),
                anchor="w",
                text_color="gray50"
            ).pack(fill="x", pady=(5, 0))

            # Right side: Action buttons
            button_frame = ctk.CTkFrame(card, fg_color="transparent")
            button_frame.pack(side="right", padx=15, pady=15)

            # Load Draft button
            ctk.CTkButton(
                button_frame,
                text="📝 Load Draft",
                command=lambda d=draft: self.load_draft_to_form(d),
                width=140,
                height=35,
                fg_color="gray30",
                hover_color="gray40"
            ).pack(pady=5)

            # Post Draft button
            ctk.CTkButton(
                button_frame,
                text="🚀 Post Now",
                command=lambda d=draft: self.post_draft_directly(d),
                width=140,
                height=35,
                fg_color="green",
                hover_color="darkgreen"
            ).pack(pady=5)

            # Delete Draft button
            ctk.CTkButton(
                button_frame,
                text="🗑️ Delete",
                command=lambda d=draft: self.delete_draft(d),
                width=140,
                height=35,
                fg_color="red",
                hover_color="darkred"
            ).pack(pady=5)

        self.update_status(f"Loaded {len(drafts)} draft(s)")

    def load_draft_to_form(self, draft):
        """Load a draft into the Create Listing form"""
        try:
            # Switch to Create Listing tab
            self.tabview.set("📦 Create Listing")

            # Clear existing form data
            self.title_entry.delete(0, tk.END)
            self.description_text.delete("1.0", tk.END)
            self.price_entry.delete(0, tk.END)
            self.cost_entry.delete(0, tk.END)
            self.shipping_entry.delete(0, tk.END)

            # Fill in draft data
            self.title_entry.insert(0, draft['title'])
            self.description_text.insert("1.0", draft['description'])
            self.price_entry.insert(0, str(draft['price']))

            if draft.get('cost'):
                self.cost_entry.insert(0, str(draft['cost']))

            if draft.get('shipping_cost'):
                self.shipping_entry.insert(0, str(draft['shipping_cost']))

            # Set condition
            self.condition_menu.set(draft.get('condition', 'Used - Good'))

            # Parse and set attributes
            if draft.get('attributes'):
                try:
                    attrs = json.loads(draft['attributes'])
                    if attrs.get('brand'):
                        self.brand_entry.delete(0, tk.END)
                        self.brand_entry.insert(0, attrs['brand'])
                    if attrs.get('size'):
                        self.size_entry.delete(0, tk.END)
                        self.size_entry.insert(0, attrs['size'])
                    if attrs.get('color'):
                        self.color_entry.delete(0, tk.END)
                        self.color_entry.insert(0, attrs['color'])
                except:
                    pass

            # Load photos
            if draft.get('photos'):
                try:
                    photo_paths = json.loads(draft['photos'])
                    self.photos = []
                    self.photo_listbox.delete(0, tk.END)

                    for path in photo_paths:
                        # Store just the path string (not Photo objects) in the GUI
                        self.photos.append(path)
                        self.photo_listbox.insert(tk.END, os.path.basename(path))

                except Exception as e:
                    print(f"Error loading draft photos: {e}")

            # Store draft ID so we can mark it as posted later
            self.current_draft_id = draft['id']

            self.update_status(f"✅ Loaded draft: {draft['title']}")
            messagebox.showinfo("Draft Loaded", f"Draft loaded into form!\n\nYou can now edit it and click 'Post Listing' to publish it.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load draft: {e}")

    def post_draft_directly(self, draft):
        """Post a draft directly to selected platforms"""
        # Confirm with user
        if not messagebox.askyesno("Post Draft?", f"Post this listing now?\n\n{draft['title']}\n\nPrice: ${draft['price']:.2f}"):
            return

        # Parse photos
        photo_paths = []
        if draft.get('photos'):
            try:
                photo_paths = json.loads(draft['photos'])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to parse draft photos: {e}")
                return

        if not photo_paths:
            messagebox.showerror("Error", "Draft has no photos!")
            return

        # Parse attributes
        attributes = {}
        if draft.get('attributes'):
            try:
                attributes = json.loads(draft['attributes'])
            except:
                pass

        # Get selected platforms from checkboxes
        selected_platforms = []
        if self.ebay_var.get():
            selected_platforms.append('ebay')
        if self.mercari_var.get():
            selected_platforms.append('mercari')

        if not selected_platforms:
            messagebox.showwarning("No Platforms", "Please select at least one platform to post to!")
            return

        # Post listing
        self.update_status(f"📤 Posting draft to {', '.join(selected_platforms)}...")

        def post():
            try:
                # Create Photo objects
                photo_objects = [
                    Photo(url="", local_path=p, order=i, is_primary=(i == 0))
                    for i, p in enumerate(photo_paths)
                ]

                # Create UnifiedListing object
                listing = UnifiedListing(
                    title=draft['title'],
                    description=draft['description'],
                    price=Price(amount=float(draft['price'])),
                    condition=ListingCondition(draft.get('condition', 'Used - Good')),
                    photos=photo_objects,
                    item_specifics=ItemSpecifics(
                        brand=attributes.get('brand') or None,
                        size=attributes.get('size') or None,
                        color=attributes.get('color') or None,
                    ),
                    shipping=Shipping(
                        cost=float(draft.get('shipping_cost', 0))
                    ),
                )

                # Post to all selected platforms
                result = self.sync_manager.post_to_all_platforms(
                    listing,
                    platforms=selected_platforms,
                    collectible_id=None,
                    cost=draft.get('cost'),
                )

                # Update database - mark draft as posted
                self.db.update_listing_status(draft['id'], 'posted')

                # Clean up draft photos directory (optional - keep photos for posted drafts if needed)
                # Uncomment to delete photos after posting:
                # import shutil
                # from pathlib import Path
                # if draft.get('listing_uuid'):
                #     draft_photos_dir = Path("data/draft_photos") / draft['listing_uuid']
                #     if draft_photos_dir.exists():
                #         shutil.rmtree(draft_photos_dir)

                # Show results
                success_count = result["success_count"]
                total = result["total_platforms"]

                # Build detailed result message
                result_msg = f"Posted to {success_count}/{total} platforms\n\n"

                # Show success/failure for each platform
                for platform, platform_result in result.get("results", {}).items():
                    if platform_result.success:
                        result_msg += f"✅ {platform.upper()}: Success\n"
                        if platform_result.listing_url:
                            result_msg += f"   URL: {platform_result.listing_url}\n"
                    else:
                        result_msg += f"❌ {platform.upper()}: Failed\n"
                        result_msg += f"   Error: {platform_result.error}\n"

                result_msg += f"\nListing ID: {result['listing_id']}"

                self.after(0, lambda: self.update_status(f"Posted to {success_count}/{total} platforms"))

                # Show appropriate dialog based on success
                if success_count > 0:
                    self.after(0, lambda msg=result_msg: messagebox.showinfo("Posting Results", msg))
                else:
                    self.after(0, lambda msg=result_msg: messagebox.showerror("Posting Failed", msg))

                # Refresh drafts list
                self.after(0, self.refresh_drafts)

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to post draft: {e}"))
                self.after(0, lambda: self.update_status("❌ Failed to post draft"))

        threading.Thread(target=post, daemon=True).start()

    def delete_draft(self, draft):
        """Delete a draft from the database"""
        if not messagebox.askyesno("Delete Draft?", f"Are you sure you want to delete this draft?\n\n{draft['title']}\n\nThis cannot be undone."):
            return

        try:
            import shutil
            from pathlib import Path

            # Delete photos directory if it exists
            if draft.get('listing_uuid'):
                draft_photos_dir = Path("data/draft_photos") / draft['listing_uuid']
                if draft_photos_dir.exists():
                    shutil.rmtree(draft_photos_dir)
                    print(f"Deleted draft photos directory: {draft_photos_dir}")

            # Delete from database
            cursor = self.db._get_cursor()
            cursor.execute("DELETE FROM listings WHERE id = ?", (draft['id'],))
            self.db.conn.commit()

            self.update_status(f"🗑️ Deleted draft: {draft['title']}")
            messagebox.showinfo("Draft Deleted", "Draft has been deleted.")

            # Refresh drafts list
            self.refresh_drafts()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete draft: {e}")

    def export_drafts_to_csv(self):
        """Export drafts to CSV for manual posting"""
        import csv
        from tkinter import filedialog

        # Get drafts
        drafts = self.db.get_drafts(limit=1000)

        if not drafts:
            messagebox.showinfo("No Drafts", "No drafts to export!")
            return

        # Ask where to save
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Drafts to CSV"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['ID', 'Title', 'Description', 'Price', 'Cost', 'Condition', 'Brand', 'Size', 'Color', 'Shipping', 'Photos', 'Created']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for draft in drafts:
                    # Parse attributes
                    attrs = {}
                    if draft.get('attributes'):
                        try:
                            attrs = json.loads(draft['attributes'])
                        except:
                            pass

                    # Get photo paths
                    photo_paths = ""
                    if draft.get('photos'):
                        try:
                            photos = json.loads(draft['photos'])
                            photo_paths = "; ".join(photos)
                        except:
                            pass

                    writer.writerow({
                        'ID': draft['id'],
                        'Title': draft['title'],
                        'Description': draft['description'],
                        'Price': draft['price'],
                        'Cost': draft.get('cost', ''),
                        'Condition': draft['condition'],
                        'Brand': attrs.get('brand', ''),
                        'Size': attrs.get('size', ''),
                        'Color': attrs.get('color', ''),
                        'Shipping': attrs.get('shipping_cost', ''),
                        'Photos': photo_paths,
                        'Created': draft['created_at']
                    })

            messagebox.showinfo("Success", f"Exported {len(drafts)} drafts to:\n{file_path}")
            self.update_status(f"✅ Exported {len(drafts)} drafts")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")

    # ========================================================================
    # IDENTIFY COLLECTIBLE TAB
    # ========================================================================

    def build_identify_collectible_tab(self):
        """Build the identify collectible tab"""
        tab = self.tabview.tab("🔍 Identify Collectible")

        # Instructions
        ctk.CTkLabel(
            tab,
            text="Upload photos to identify if item is a collectible",
            font=("Arial", 14),
        ).pack(pady=20)

        # Photo upload
        ctk.CTkButton(
            tab,
            text="📸 Select Photos to Analyze",
            command=self.select_collectible_photos,
            width=300,
            height=50,
            font=("Arial Bold", 14),
        ).pack(pady=10)

        self.collectible_photos_label = ctk.CTkLabel(tab, text="No photos selected")
        self.collectible_photos_label.pack(pady=5)

        # Analyze button
        ctk.CTkButton(
            tab,
            text="🤖 Identify with AI",
            command=self.identify_collectible,
            fg_color="purple",
            hover_color="darkviolet",
            width=300,
            height=50,
            font=("Arial Bold", 14),
        ).pack(pady=20)

        # Results
        self.collectible_results = ctk.CTkTextbox(tab, width=1000, height=400)
        self.collectible_results.pack(pady=10, padx=20)

    def select_collectible_photos(self):
        """Select photos for collectible identification"""
        files = filedialog.askopenfilenames(
            title="Select Photos",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")]
        )

        if files:
            self.collectible_photos = list(files)
            self.collectible_photos_label.configure(text=f"{len(files)} photo(s) selected")

    def identify_collectible(self):
        """Identify if photos contain a collectible"""
        if not hasattr(self, 'collectible_photos') or not self.collectible_photos:
            messagebox.showwarning("No Photos", "Please select photos first!")
            return

        self.update_status("🔍 Analyzing for collectibles...")
        self.collectible_results.delete("1.0", tk.END)
        self.collectible_results.insert("1.0", "Analyzing with AI...\n\n")

        def identify():
            try:
                photo_objects = [
                    Photo(url="", local_path=p, order=i, is_primary=(i == 0))
                    for i, p in enumerate(self.collectible_photos)
                ]

                is_collectible, collectible_id, analysis = identify_collectible(photo_objects)

                # Update UI
                self.after(0, lambda: self.show_collectible_results(is_collectible, collectible_id, analysis))

            except Exception as e:
                self.after(0, lambda: self.collectible_results.delete("1.0", tk.END))
                self.after(0, lambda: self.collectible_results.insert("1.0", f"❌ Error: {e}"))
                self.after(0, lambda: self.update_status(f"❌ Identification failed: {e}"))

        threading.Thread(target=identify, daemon=True).start()

    def show_collectible_results(self, is_collectible, collectible_id, analysis):
        """Display collectible identification results"""
        self.collectible_results.delete("1.0", tk.END)

        # Check for errors first
        if "error" in analysis:
            self.collectible_results.insert("1.0", "❌ AI ERROR\n\n")
            self.collectible_results.insert(tk.END, f"Error: {analysis.get('error')}\n\n")
            self.collectible_results.insert(tk.END, "This might mean:\n")
            self.collectible_results.insert(tk.END, "- Claude Sonnet model not available on your API tier\n")
            self.collectible_results.insert(tk.END, "- API key issue\n")
            self.collectible_results.insert(tk.END, "- Network problem\n\n")
            self.collectible_results.insert(tk.END, "Try adding to your .env file:\n")
            self.collectible_results.insert(tk.END, "CLAUDE_COLLECTIBLE_MODEL=claude-3-haiku-20240307")
            self.update_status(f"❌ Error: {analysis.get('error')}")
            return

        if not is_collectible:
            self.collectible_results.insert("1.0", "❌ NOT A COLLECTIBLE\n\n")
            self.collectible_results.insert(tk.END, f"Reasoning: {analysis.get('reasoning', 'Standard item')}\n\n")
            self.collectible_results.insert(tk.END, "⚠️ If this seems wrong (e.g., sports cards, team logos), there may be an AI error.\n")
            self.collectible_results.insert(tk.END, "Try using a different Claude model in your .env file.")
            self.update_status("Not a collectible")
            return

        # Store collectible data
        self.collectible_data = {"id": collectible_id, **analysis}

        # Display results
        result_text = "✅ COLLECTIBLE IDENTIFIED!\n\n"
        result_text += f"Name: {analysis.get('name', 'Unknown')}\n"
        result_text += f"Category: {analysis.get('category', 'N/A')}\n"

        if analysis.get('brand'):
            result_text += f"Brand: {analysis['brand']}\n"

        if analysis.get('model'):
            result_text += f"Model: {analysis['model']}\n"

        if analysis.get('year'):
            result_text += f"Year: {analysis['year']}\n"

        result_text += f"\nCondition: {analysis.get('condition', 'N/A')}\n"
        result_text += f"Rarity: {analysis.get('rarity', 'N/A')}\n\n"

        # Pricing
        result_text += "💰 MARKET VALUE:\n"
        if analysis.get('estimated_value_low'):
            result_text += f"  Low: ${analysis['estimated_value_low']:.2f}\n"
        if analysis.get('estimated_value_high'):
            result_text += f"  High: ${analysis['estimated_value_high']:.2f}\n"
        if analysis.get('estimated_value_low') and analysis.get('estimated_value_high'):
            avg = (analysis['estimated_value_low'] + analysis['estimated_value_high']) / 2
            result_text += f"  Average: ${avg:.2f}\n"

        result_text += f"\nMarket Trend: {analysis.get('market_trend', 'N/A')}\n\n"

        # Price Reasons (3 reasons explaining the price)
        if analysis.get('price_reasons'):
            result_text += "💰 WHY THIS PRICE:\n"
            for i, reason in enumerate(analysis['price_reasons'][:3], 1):
                result_text += f"   {i}. {reason}\n"
            result_text += "\n"

        # Signature Analysis (if item has autograph)
        if analysis.get('authentication', {}).get('has_signature'):
            sig = analysis['authentication'].get('signature_analysis', {})
            if sig:
                auth_status = "AUTHENTIC" if sig.get('is_authentic') else "FAKE/STAMPED"
                conf = int(sig.get('confidence', 0) * 100)
                result_text += f"✍️  Signature: {auth_status} ({conf}% confidence)\n"
                if sig.get('authenticity_reasoning'):
                    result_text += f"   {sig['authenticity_reasoning']}\n"
                if sig.get('recommendation'):
                    result_text += f"   💡 {sig['recommendation']}\n"
                result_text += "\n"

        # Fake Indicators (if item has fake/counterfeit markers)
        if analysis.get('fake_indicators'):
            result_text += "⚠️  FAKE/COUNTERFEIT INDICATORS:\n"
            for i, indicator in enumerate(analysis['fake_indicators'][:3], 1):
                result_text += f"   {i}. {indicator}\n"
            result_text += "\n"

        # Fallback: show why_valuable if price_reasons not available
        if not analysis.get('price_reasons') and analysis.get('why_valuable'):
            result_text += f"Why Valuable:\n{analysis['why_valuable']}\n\n"

        if analysis.get('best_platforms'):
            result_text += f"Best Platforms: {', '.join(analysis['best_platforms'])}\n\n"

        result_text += f"Confidence: {analysis.get('confidence_score', 0) * 100:.0f}%\n"
        result_text += f"AI Provider: {analysis.get('ai_provider', 'Unknown')}\n\n"

        result_text += f"💾 Saved to database (ID: {collectible_id})"

        self.collectible_results.insert("1.0", result_text)
        self.update_status("✅ Collectible identified and saved!")

        # Ask if they want to create listing
        if messagebox.askyesno("Create Listing?", "This is a collectible! Create a listing for it?"):
            self.photos = self.collectible_photos.copy()
            self.tabview.set("📦 Create Listing")

            # Pre-fill listing form
            if analysis.get('name'):
                self.title_entry.delete(0, tk.END)
                self.title_entry.insert(0, analysis['name'][:80])

            if analysis.get('estimated_value_low') and analysis.get('estimated_value_high'):
                avg_price = (analysis['estimated_value_low'] + analysis['estimated_value_high']) / 2
                self.price_entry.delete(0, tk.END)
                self.price_entry.insert(0, f"{avg_price:.2f}")

            # Update photo list
            self.photo_listbox.delete(0, tk.END)
            for photo in self.photos:
                self.photo_listbox.insert(tk.END, Path(photo).name)

    # ========================================================================
    # SHOPPING MODE TAB
    # ========================================================================

    def build_shopping_mode_tab(self):
        """Build the shopping mode tab"""
        tab = self.tabview.tab("🛒 Shopping Mode")

        ctk.CTkLabel(
            tab,
            text="Quick lookup collectibles while shopping",
            font=("Arial", 14),
        ).pack(pady=20)

        # Search box
        search_frame = ctk.CTkFrame(tab)
        search_frame.pack(pady=10)

        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(search_frame, width=400, placeholder_text="Enter item name, brand, or keyword")
        self.search_entry.pack(side="left", padx=5)

        ctk.CTkButton(
            search_frame,
            text="🔍 Quick Lookup",
            command=self.quick_lookup_search,
            width=150,
        ).pack(side="left", padx=5)

        # Results
        self.shopping_results = ctk.CTkTextbox(tab, width=1000, height=250)
        self.shopping_results.pack(pady=10, padx=20)

        # Profit calculator
        calc_frame = ctk.CTkFrame(tab)
        calc_frame.pack(pady=20)

        ctk.CTkLabel(
            calc_frame,
            text="💰 Profit Calculator",
            font=("Arial Bold", 16),
        ).pack(pady=10)

        input_frame = ctk.CTkFrame(calc_frame)
        input_frame.pack(pady=5)

        ctk.CTkLabel(input_frame, text="Asking Price ($):").grid(row=0, column=0, padx=5, pady=5)
        self.asking_price_entry = ctk.CTkEntry(input_frame, width=100, placeholder_text="0.00")
        self.asking_price_entry.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(input_frame, text="Fees %:").grid(row=0, column=2, padx=5, pady=5)
        self.fees_entry = ctk.CTkEntry(input_frame, width=80, placeholder_text="15")
        self.fees_entry.insert(0, "15")
        self.fees_entry.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkButton(
            input_frame,
            text="Calculate Profit",
            command=self.calculate_profit,
            width=150,
        ).grid(row=0, column=4, padx=10, pady=5)

        # Profit results
        self.profit_results = ctk.CTkTextbox(tab, width=1000, height=200)
        self.profit_results.pack(pady=10, padx=20)

    def quick_lookup_search(self):
        """Quick lookup in database"""
        query = self.search_entry.get()
        if not query:
            messagebox.showwarning("No Query", "Please enter a search term!")
            return

        self.update_status(f"Searching for '{query}'...")

        def search():
            try:
                results = quick_lookup(query, max_results=10)

                self.after(0, lambda: self.display_search_results(results))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Search failed: {e}"))

        threading.Thread(target=search, daemon=True).start()

    def display_search_results(self, results):
        """Display search results"""
        self.shopping_results.delete("1.0", tk.END)

        if not results:
            self.shopping_results.insert("1.0", "No results found in database.\n\n💡 Tip: Use 'Identify Collectible' to add new items to the database.")
            self.update_status("No results found")
            return

        result_text = f"Found {len(results)} collectible(s):\n\n"

        for i, item in enumerate(results, 1):
            result_text += f"{i}. {item['name']}\n"

            if item.get('brand'):
                result_text += f"   Brand: {item['brand']}\n"

            if item.get('category'):
                result_text += f"   Category: {item['category']}\n"

            if item.get('estimated_value_avg'):
                low = item.get('estimated_value_low', 0)
                high = item.get('estimated_value_high', 0)
                avg = item['estimated_value_avg']
                result_text += f"   💰 Value: ${low:.2f} - ${high:.2f} (Avg: ${avg:.2f})\n"

            if item.get('times_found', 0) > 1:
                result_text += f"   📊 Found {item['times_found']} times\n"

            result_text += f"   Database ID: {item['id']}\n\n"

        self.shopping_results.insert("1.0", result_text)
        self.update_status(f"Found {len(results)} result(s)")

        # Store last result for profit calc
        if results:
            self.last_search_result = results[0]

    def calculate_profit(self):
        """Calculate profit for a collectible"""
        if not hasattr(self, 'last_search_result'):
            messagebox.showwarning("No Item", "Search for an item first!")
            return

        if not self.asking_price_entry.get():
            messagebox.showwarning("No Price", "Enter asking price!")
            return

        asking_price = float(self.asking_price_entry.get())
        fees_pct = float(self.fees_entry.get())

        collectible_id = self.last_search_result['id']

        def calc():
            try:
                result = profit_calculator(collectible_id, asking_price, fees_percentage=fees_pct)

                self.after(0, lambda: self.display_profit_results(result, asking_price))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Calculation failed: {e}"))

        threading.Thread(target=calc, daemon=True).start()

    def display_profit_results(self, result, asking_price):
        """Display profit calculation results"""
        self.profit_results.delete("1.0", tk.END)

        if "error" in result:
            self.profit_results.insert("1.0", f"❌ Error: {result['error']}")
            return

        result_text = f"💰 PROFIT ANALYSIS\n\n"
        result_text += f"Item: {result['collectible_name']}\n\n"
        result_text += f"Asking Price: ${asking_price:.2f}\n"
        result_text += f"Market Average: ${result['estimated_value']:.2f}\n"
        result_text += f"Platform Fees ({result['fees'] / result['estimated_value'] * 100:.0f}%): ${result['fees']:.2f}\n\n"

        result_text += f"Expected Profit: ${result['expected_profit']:.2f}\n"
        result_text += f"Expected ROI: {result['expected_roi']:.0f}%\n\n"

        if result['is_profitable']:
            if result['expected_roi'] > 50:
                result_text += "✅ RECOMMENDATION: EXCELLENT BUY! 🎯\n"
            elif result['expected_roi'] > 30:
                result_text += "✅ RECOMMENDATION: Good buy 👍\n"
            else:
                result_text += "👍 RECOMMENDATION: Worth considering\n"
        else:
            result_text += "⚠️ WARNING: May not be profitable at this price\n"

        self.profit_results.insert("1.0", result_text)
        self.update_status("Profit calculated")

    # ========================================================================
    # MY LISTINGS TAB
    # ========================================================================

    def build_my_listings_tab(self):
        """Build the my listings tab"""
        tab = self.tabview.tab("📋 My Listings")

        # Refresh button
        ctk.CTkButton(
            tab,
            text="🔄 Refresh Listings",
            command=self.refresh_listings,
            width=200,
        ).pack(pady=10)

        # Listings display
        self.listings_text = ctk.CTkTextbox(tab, width=1000, height=600)
        self.listings_text.pack(pady=10, padx=20)

    def refresh_listings(self):
        """Refresh listings from database"""
        self.update_status("Refreshing listings...")

        def refresh():
            try:
                cursor = self.db._get_cursor()
                cursor.execute("""
                    SELECT l.*, GROUP_CONCAT(pl.platform || ':' || pl.status) as platform_statuses
                    FROM listings l
                    LEFT JOIN platform_listings pl ON l.id = pl.listing_id
                    WHERE l.status != 'sold'
                    GROUP BY l.id
                    ORDER BY l.created_at DESC
                    LIMIT 50
                """)

                listings = cursor.fetchall()

                self.after(0, lambda: self.display_listings(listings))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to load listings: {e}"))

        threading.Thread(target=refresh, daemon=True).start()

    def display_listings(self, listings):
        """Display listings"""
        self.listings_text.delete("1.0", tk.END)

        if not listings:
            self.listings_text.insert("1.0", "No active listings found.")
            return

        text = f"Active Listings ({len(listings)}):\n\n"

        for listing in listings:
            listing_dict = dict(listing)

            text += f"{'='*80}\n"
            text += f"📦 {listing_dict['title']}\n"
            text += f"ID: {listing_dict['id']} | UUID: {listing_dict['listing_uuid']}\n"
            text += f"Price: ${listing_dict['price']:.2f}"

            if listing_dict.get('cost'):
                profit = listing_dict['price'] - listing_dict['cost']
                text += f" (Cost: ${listing_dict['cost']:.2f}, Profit: ${profit:.2f})"

            text += f"\nStatus: {listing_dict['status']}"

            # Storage location
            if listing_dict.get('storage_location'):
                text += f" | 📍 Storage: {listing_dict['storage_location']}"

            text += "\n"

            # Platform statuses
            if listing_dict.get('platform_statuses'):
                text += "Platforms:\n"
                for platform_status in listing_dict['platform_statuses'].split(','):
                    if ':' in platform_status:
                        platform, status = platform_status.split(':')
                        icon = "✅" if status == "active" else "❌" if status == "failed" else "⏳"
                        text += f"  {icon} {platform}: {status}\n"

            text += f"Created: {listing_dict['created_at']}\n\n"

        self.listings_text.insert("1.0", text)
        self.update_status(f"Showing {len(listings)} listing(s)")

    # ========================================================================
    # NOTIFICATIONS TAB
    # ========================================================================

    def build_notifications_tab(self):
        """Build the notifications tab"""
        tab = self.tabview.tab("🔔 Notifications")

        # Refresh button
        btn_frame = ctk.CTkFrame(tab)
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame,
            text="🔄 Refresh",
            command=self.refresh_notifications,
            width=150,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="✅ Mark All Read",
            command=self.mark_all_read,
            width=150,
        ).pack(side="left", padx=5)

        # Notifications display
        self.notifications_text = ctk.CTkTextbox(tab, width=1000, height=600)
        self.notifications_text.pack(pady=10, padx=20)

    def refresh_notifications(self):
        """Refresh notifications"""
        self.update_status("Loading notifications...")

        def refresh():
            try:
                notifications = self.notification_manager.get_recent_notifications(limit=50)

                self.after(0, lambda: self.display_notifications(notifications))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to load notifications: {e}"))

        threading.Thread(target=refresh, daemon=True).start()

    def display_notifications(self, notifications):
        """Display notifications"""
        self.notifications_text.delete("1.0", tk.END)

        if not notifications:
            self.notifications_text.insert("1.0", "No notifications")
            return

        unread_count = sum(1 for n in notifications if not n['is_read'])
        text = f"Notifications (Unread: {unread_count}):\n\n"

        for notif in notifications:
            icon = "🔴" if not notif['is_read'] else "✅"
            type_icon = {
                "sale": "💰",
                "offer": "💵",
                "listing_failed": "❌",
                "price_alert": "🔔"
            }.get(notif['type'], "📬")

            text += f"{icon} {type_icon} {notif['title']}\n"
            text += f"   {notif['message']}\n"
            text += f"   {notif['created_at']}\n\n"

        self.notifications_text.insert("1.0", text)
        self.update_status(f"{unread_count} unread notification(s)")

    def mark_all_read(self):
        """Mark all notifications as read"""
        def mark():
            try:
                cursor = self.db._get_cursor()
                cursor.execute("UPDATE notifications SET is_read = 1 WHERE is_read = 0")
                self.db.conn.commit()

                self.after(0, self.refresh_notifications)
                self.after(0, lambda: self.update_status("All notifications marked as read"))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed: {e}"))

        threading.Thread(target=mark, daemon=True).start()

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def update_status(self, message):
        """Update status bar"""
        self.status_label.configure(text=message)


def main():
    """Run the GUI application"""
    app = AIListerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
