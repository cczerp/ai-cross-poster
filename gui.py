#!/usr/bin/env python3
"""
AI Cross-Poster GUI
===================
Simple, beautiful GUI for cross-platform listing with collectible recognition.
"""

import os
import sys
import threading
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

        # Tabview
        self.tabview = ctk.CTkTabview(self, width=1150, height=650)
        self.tabview.pack(pady=10, padx=20)

        # Create tabs
        self.tabview.add("📦 Create Listing")
        self.tabview.add("🔍 Identify Collectible")
        self.tabview.add("🛒 Shopping Mode")
        self.tabview.add("📋 My Listings")
        self.tabview.add("🔔 Notifications")

        # Build each tab
        self.build_create_listing_tab()
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

        # Scrollable frame for form
        scroll_frame = ctk.CTkScrollableFrame(right_frame, width=600, height=450)
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

        # Shipping
        ctk.CTkLabel(scroll_frame, text="Shipping Cost ($):").pack(anchor="w", pady=(10, 0))
        self.shipping_entry = ctk.CTkEntry(scroll_frame, width=100, placeholder_text="0.00 for free")
        self.shipping_entry.pack(anchor="w", pady=5)

        # AI options
        ai_options_frame = ctk.CTkFrame(scroll_frame)
        ai_options_frame.pack(pady=10)

        # GPT-4 fallback checkbox (disabled by default to save quota)
        self.enable_gpt4_fallback = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            ai_options_frame,
            text="Enable GPT-4 fallback (uses OpenAI quota)",
            variable=self.enable_gpt4_fallback,
        ).pack(pady=5)

        # AI Re-analyze button (auto-runs when photos added)
        ctk.CTkButton(
            scroll_frame,
            text="🔄 Re-run AI Analysis",
            command=self.ai_enhance_listing,
            fg_color="purple",
            hover_color="darkviolet",
            height=40,
        ).pack(pady=10)

        # Platform selection
        ctk.CTkLabel(scroll_frame, text="Post to Platforms:").pack(anchor="w", pady=(10, 0))
        platform_frame = ctk.CTkFrame(scroll_frame)
        platform_frame.pack(anchor="w", pady=5)

        self.ebay_var = tk.BooleanVar(value=True)
        self.mercari_var = tk.BooleanVar(value=True)

        ctk.CTkCheckBox(platform_frame, text="eBay", variable=self.ebay_var).pack(side="left", padx=10)
        ctk.CTkCheckBox(platform_frame, text="Mercari", variable=self.mercari_var).pack(side="left", padx=10)

        # Post button
        ctk.CTkButton(
            scroll_frame,
            text="🚀 Post to All Platforms",
            command=self.post_listing,
            fg_color="green",
            hover_color="darkgreen",
            height=50,
            font=("Arial Bold", 16),
        ).pack(pady=20)

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
            self.update_status(f"Added {len(files)} photo(s)")
            # Auto-run AI analysis
            self.ai_enhance_listing()

    def remove_photo(self):
        """Remove selected photo"""
        selection = self.photo_listbox.curselection()
        if selection:
            idx = selection[0]
            del self.photos[idx]
            self.photo_listbox.delete(idx)
            self.update_status("Photo removed")

    def ai_enhance_listing(self):
        """Use AI to enhance listing details"""
        if not self.photos:
            # Silently skip if no photos (called from add_photos)
            return

        self.update_status("🤖 AI analyzing photos...")

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

                # Detect attributes
                from src.collectibles.attribute_detector import AttributeDetector
                detector = AttributeDetector.from_env()

                # Check if GPT-4 fallback is enabled
                use_fallback = self.enable_gpt4_fallback.get()

                # Try Claude first
                self.after(0, lambda: self.update_status("🤖 Using Claude AI..."))
                attributes = detector.detect_attributes_claude(photo_objects)

                # Check for errors in Claude response
                if "error" in attributes:
                    claude_error = attributes.get("error", "Unknown error")
                    raw_response = attributes.get("raw_response", "")

                    # Show detailed error with raw response if available
                    error_details = f"{claude_error}"
                    if raw_response:
                        error_details += f"\n\n{raw_response}"

                    # Try GPT-4 fallback if enabled
                    if use_fallback:
                        self.after(0, lambda: self.update_status("🔄 Claude failed, trying GPT-4..."))
                        attributes = detector.detect_attributes_openai(photo_objects)

                        # Check if GPT-4 also failed
                        if "error" in attributes:
                            gpt4_error = attributes.get("error", "Unknown error")
                            self.after(0, lambda: messagebox.showerror(
                                "AI Analysis Error",
                                f"Both AIs failed:\n\nClaude: {claude_error}\nGPT-4: {gpt4_error}\n\nPlease check your API keys in .env"
                            ))
                            self.after(0, lambda: self.update_status(f"❌ Both AIs failed"))
                            return
                    else:
                        # No fallback - show Claude error with details
                        self.after(0, lambda ed=error_details: messagebox.showerror(
                            "Claude AI Error",
                            f"Claude could not analyze the photos:\n\n{ed}\n\nPlease check:\n- ANTHROPIC_API_KEY is set in .env\n- Photos are valid images\n- Internet connection\n\nTip: Enable 'GPT-4 fallback' checkbox if you want to try GPT-4 when Claude fails."
                        ))
                        self.after(0, lambda: self.update_status(f"❌ Claude failed: {claude_error}"))
                        return

                # Update UI on main thread
                self.after(0, lambda: self.apply_ai_attributes(attributes))

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

    def apply_ai_attributes(self, attributes):
        """Apply AI-detected attributes to form"""
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

                self.after(0, lambda: self.update_status(f"✅ Posted to {success_count}/{total} platforms"))
                self.after(0, lambda: messagebox.showinfo(
                    "Success!",
                    f"Posted to {success_count}/{total} platforms!\n\nListing ID: {result['listing_id']}"
                ))

                # Clear form
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
        self.shipping_entry.delete(0, tk.END)
        self.collectible_data = None

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

        if not is_collectible:
            self.collectible_results.insert("1.0", "❌ NOT A COLLECTIBLE\n\n")
            self.collectible_results.insert(tk.END, f"Reasoning: {analysis.get('reasoning', 'Standard item')}")
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

        # Additional info
        if analysis.get('why_valuable'):
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
                cursor = self.db.conn.cursor()
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

            text += f"\nStatus: {listing_dict['status']}\n"

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
                cursor = self.db.conn.cursor()
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
