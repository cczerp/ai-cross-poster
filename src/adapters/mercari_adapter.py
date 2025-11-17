"""
Mercari Adapter
===============
Converts UnifiedListing schema to Mercari format.

Supports both:
1. Mercari Shops API (official API for Mercari Shops sellers)
2. Automation layer (Puppeteer/Playwright for regular Mercari - headless browser)

Note: Regular Mercari does not have a public API, so automation is required.
"""

import os
import json
import time
import random
from typing import Dict, Any, Optional, List
import requests
from datetime import datetime

from ..schema.unified_listing import (
    UnifiedListing,
    ListingCondition,
)


class MercariShopsAdapter:
    """
    Adapter for Mercari Shops API (official API for shop sellers).

    API documentation: https://developer.mercari.com/en (if available)
    """

    # Mercari condition mappings
    CONDITION_MAP = {
        ListingCondition.NEW: "new",
        ListingCondition.NEW_WITH_TAGS: "new",
        ListingCondition.NEW_WITHOUT_TAGS: "new",
        ListingCondition.LIKE_NEW: "like_new",
        ListingCondition.EXCELLENT: "excellent",
        ListingCondition.GOOD: "good",
        ListingCondition.FAIR: "fair",
        ListingCondition.POOR: "poor",
        ListingCondition.FOR_PARTS: "poor",
    }

    def __init__(self, api_key: str, shop_id: str, sandbox: bool = False):
        """
        Initialize Mercari Shops adapter.

        Args:
            api_key: Mercari Shops API key
            shop_id: Your shop ID
            sandbox: Use sandbox environment
        """
        self.api_key = api_key
        self.shop_id = shop_id
        self.sandbox = sandbox

        # Note: Replace with actual Mercari Shops API endpoint when available
        self.base_url = (
            "https://api-sandbox.mercari.com"
            if sandbox
            else "https://api.mercari.com"
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def convert_to_mercari_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        """
        Convert UnifiedListing to Mercari Shops API format.

        Args:
            listing: UnifiedListing object

        Returns:
            Mercari API payload
        """
        # Validate first
        is_valid, errors = listing.validate()
        if not is_valid:
            raise ValueError(f"Invalid listing: {', '.join(errors)}")

        # Mercari has a 40-character title limit
        title = listing.get_platform_title("mercari")

        # Get photos (Mercari allows up to 10 photos)
        photos = listing.get_platform_photos("mercari")
        photo_urls = [p.url for p in photos]

        # Map condition
        condition = self.CONDITION_MAP.get(
            listing.condition, self.CONDITION_MAP[ListingCondition.GOOD]
        )

        # Build the payload (structure based on typical e-commerce APIs)
        payload = {
            "title": title,
            "description": listing.description,
            "price": int(listing.price.amount),  # Mercari uses cents/integer pricing
            "condition": condition,
            "photos": photo_urls,
            "quantity": listing.quantity,
            "shop_id": self.shop_id,
        }

        # Add category if available
        if listing.category and listing.category.mercari_category_id:
            payload["category_id"] = listing.category.mercari_category_id

        # Add brand if available
        if listing.item_specifics.brand:
            payload["brand"] = listing.item_specifics.brand

        # Add size if available
        if listing.item_specifics.size:
            payload["size"] = listing.item_specifics.size

        # Add color if available
        if listing.item_specifics.color:
            payload["color"] = listing.item_specifics.color

        # Shipping information
        if listing.shipping.cost is not None:
            payload["shipping_price"] = int(listing.shipping.cost)
        else:
            payload["shipping_price"] = 0  # Free shipping

        # Apply Mercari-specific overrides
        if listing.mercari_overrides:
            payload.update(listing.mercari_overrides)

        return payload

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, str]:
        """
        Publish listing to Mercari Shops.

        Args:
            listing: UnifiedListing object

        Returns:
            Dictionary with listing_id
        """
        payload = self.convert_to_mercari_format(listing)

        response = requests.post(
            f"{self.base_url}/v1/listings",
            headers=self._get_headers(),
            json=payload,
        )

        if response.status_code in [200, 201]:
            listing_data = response.json()
            return {
                "listing_id": listing_data.get("id"),
                "listing_url": listing_data.get("url"),
            }
        else:
            raise Exception(f"Failed to publish to Mercari Shops: {response.text}")

    @classmethod
    def from_env(cls, sandbox: bool = False) -> "MercariShopsAdapter":
        """
        Create adapter from environment variables.

        Expected variables:
            - MERCARI_API_KEY
            - MERCARI_SHOP_ID
        """
        api_key = os.getenv("MERCARI_API_KEY")
        shop_id = os.getenv("MERCARI_SHOP_ID")

        if not all([api_key, shop_id]):
            raise ValueError(
                "Missing Mercari credentials in environment variables. "
                "Required: MERCARI_API_KEY, MERCARI_SHOP_ID"
            )

        return cls(api_key, shop_id, sandbox)


class MercariAutomationAdapter:
    """
    Adapter for regular Mercari using browser automation.

    Uses Playwright/Puppeteer to automate listing creation when API is not available.
    This is a fallback for regular Mercari sellers without Shops API access.
    """

    # Mercari condition mappings (same as Shops adapter)
    CONDITION_MAP = {
        ListingCondition.NEW: "new",
        ListingCondition.NEW_WITH_TAGS: "new",
        ListingCondition.NEW_WITHOUT_TAGS: "new",
        ListingCondition.LIKE_NEW: "like_new",
        ListingCondition.EXCELLENT: "excellent",
        ListingCondition.GOOD: "good",
        ListingCondition.FAIR: "fair",
        ListingCondition.POOR: "poor",
        ListingCondition.FOR_PARTS: "poor",
    }

    def __init__(
        self,
        email: str,
        password: str,
        headless: bool = True,
        cookies_file: Optional[str] = None,
    ):
        """
        Initialize Mercari automation adapter.

        Args:
            email: Mercari account email
            password: Mercari account password
            headless: Run browser in headless mode
            cookies_file: Path to saved cookies file (bypasses login)
        """
        self.email = email
        self.password = password
        self.headless = headless
        self.cookies_file = cookies_file
        self.browser = None
        self.page = None

    def _ensure_playwright(self):
        """Ensure Playwright is installed"""
        try:
            from playwright.sync_api import sync_playwright
            return sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for Mercari automation. "
                "Install with: pip install playwright && playwright install"
            )

    def _human_delay(self, min_ms: int = 100, max_ms: int = 500):
        """Add random human-like delay"""
        delay = random.uniform(min_ms, max_ms) / 1000
        time.sleep(delay)

    def _human_type(self, selector: str, text: str):
        """Type text with human-like delays between characters"""
        self.page.click(selector)
        for char in text:
            self.page.type(selector, char, delay=random.uniform(50, 150))
            # Occasionally pause (like humans do)
            if random.random() < 0.1:  # 10% chance
                time.sleep(random.uniform(0.2, 0.5))

    def _login(self):
        """Login to Mercari with human-like behavior"""
        import time

        try:
            print("📍 Navigating to Mercari login page...")
            # Navigate to login page - use domcontentloaded instead of networkidle
            # networkidle is too strict and can timeout on pages with constant activity
            self.page.goto("https://www.mercari.com/login/", wait_until="domcontentloaded", timeout=120000)
            print("📄 Page loaded, waiting for form elements...")
            self._human_delay(2000, 3000)  # Wait for page to fully render

            print("✍️  Entering email...")
            # Wait for email field and type email slowly (human-like)
            email_selector = None
            for selector in ['input[name="email"]', 'input[type="email"]', '#email', 'input[placeholder*="mail" i]']:
                try:
                    self.page.wait_for_selector(selector, timeout=5000, state="visible")
                    email_selector = selector
                    print(f"✅ Found email field using: {selector}")
                    break
                except:
                    continue

            if not email_selector:
                screenshot_path = f"mercari_no_email_field_{int(time.time())}.png"
                self.page.screenshot(path=screenshot_path)
                raise Exception(f"Could not find email input field. Screenshot: {screenshot_path}")

            self._human_type(email_selector, self.email)
            self._human_delay(300, 800)

            print("🔒 Entering password...")
            # Wait for password field
            password_selector = None
            for selector in ['input[name="password"]', 'input[type="password"]', '#password', 'input[placeholder*="password" i]']:
                try:
                    self.page.wait_for_selector(selector, timeout=5000, state="visible")
                    password_selector = selector
                    print(f"✅ Found password field using: {selector}")
                    break
                except:
                    continue

            if not password_selector:
                screenshot_path = f"mercari_no_password_field_{int(time.time())}.png"
                self.page.screenshot(path=screenshot_path)
                raise Exception(f"Could not find password input field. Screenshot: {screenshot_path}")

            self._human_type(password_selector, self.password)
            self._human_delay(500, 1000)

            print("🔘 Clicking submit button...")
            # Click submit - try multiple selectors
            submit_clicked = False
            for selector in ['button[type="submit"]', 'button:has-text("Sign in")', 'button:has-text("Log in")', 'input[type="submit"]']:
                try:
                    self.page.click(selector, timeout=5000)
                    submit_clicked = True
                    break
                except:
                    continue

            if not submit_clicked:
                raise Exception("Could not find submit button")

            print("⏳ Waiting for login to complete (max 2 minutes)...")
            # Wait for redirect to homepage or dashboard
            try:
                # Increased timeout to 2 minutes for slow connections
                self.page.wait_for_url("https://www.mercari.com/", timeout=120000)
                print("✅ Login successful!")
                self._human_delay(1000, 2000)
            except Exception as e:
                # Login failed - take screenshot for debugging
                screenshot_path = f"mercari_login_error_{int(time.time())}.png"
                self.page.screenshot(path=screenshot_path)
                current_url = self.page.url

                print(f"📸 Screenshot saved to: {screenshot_path}")
                print(f"❌ Login timeout. Current URL: {current_url}")

                raise Exception(
                    f"Login failed - timeout waiting for redirect to homepage.\n"
                    f"Current URL: {current_url}\n"
                    f"Screenshot saved to: {screenshot_path}\n\n"
                    f"Possible causes:\n"
                    f"1. Invalid email/password credentials\n"
                    f"2. Mercari requires 2FA/verification (not supported in headless mode)\n"
                    f"3. Mercari detected automation and blocked login\n"
                    f"4. Network is slow or Mercari is down\n\n"
                    f"Solutions:\n"
                    f"- Verify MERCARI_EMAIL and MERCARI_PASSWORD in .env are correct\n"
                    f"- Check the screenshot to see what page appeared\n"
                    f"- Try logging in manually at mercari.com to check for verification prompts"
                )

        except Exception as e:
            # Re-raise with context
            if "Login failed" in str(e):
                raise
            else:
                screenshot_path = f"mercari_login_error_{int(time.time())}.png"
                try:
                    self.page.screenshot(path=screenshot_path)
                    print(f"📸 Screenshot saved to: {screenshot_path}")
                except:
                    pass
                raise Exception(f"Login error: {str(e)}")

    def _save_cookies(self):
        """Save browser cookies to file for future sessions"""
        if not self.cookies_file:
            self.cookies_file = "data/mercari_cookies.json"

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)

        # Get cookies from browser context
        cookies = self.page.context.cookies()

        # Save to file
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f)

        print(f"💾 Saved cookies to {self.cookies_file}")

    def _load_cookies(self):
        """Load cookies from file"""
        if not os.path.exists(self.cookies_file):
            return

        with open(self.cookies_file, 'r') as f:
            cookies = json.load(f)

        # Add cookies to browser context
        self.page.context.add_cookies(cookies)
        print(f"✅ Loaded {len(cookies)} cookies")

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, str]:
        """
        Publish listing to Mercari using browser automation.

        Args:
            listing: UnifiedListing object

        Returns:
            Dictionary with listing_id and listing_url
        """
        sync_playwright = self._ensure_playwright()

        with sync_playwright() as p:
            # Launch browser with anti-detection settings
            launch_args = [
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]

            # Only add headless-specific flags when in headless mode
            if self.headless:
                launch_args.extend([
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                ])

            self.browser = p.chromium.launch(
                headless=self.headless,
                args=launch_args,
                # Enable downloads and other features to appear more normal
                downloads_path='./downloads',
            )

            # Create page with realistic context
            context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                timezone_id='America/New_York',
                # Add more realistic browser fingerprint
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                }
            )
            self.page = context.new_page()

            # Enhanced script to hide webdriver property and appear more human
            self.page.add_init_script("""
                // Hide webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Add chrome object
                window.navigator.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {},
                };

                // Mock plugins with realistic values
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });

                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)

            # Load cookies if available, otherwise login
            if self.cookies_file and os.path.exists(self.cookies_file):
                print(f"🍪 Loading saved cookies from {self.cookies_file}")
                self._load_cookies()
                # Navigate to homepage to verify cookies work
                print("📍 Navigating to Mercari to verify cookies...")
                self.page.goto("https://www.mercari.com/", wait_until="domcontentloaded", timeout=120000)
                self._human_delay(2000, 3000)

                # Check if we're logged in by looking at URL (if redirected to login, cookies failed)
                current_url = self.page.url
                print(f"📍 Current URL: {current_url}")

                if "login" in current_url.lower():
                    print("⚠️  Cookies expired or invalid (redirected to login), falling back to login...")
                    self._login()
                    self._save_cookies()
                else:
                    print("✅ Logged in successfully using cookies!")
            else:
                print("🔐 No cookies found, performing login...")
                self._login()
                self._save_cookies()

            # Navigate to sell page (with human delay)
            self.page.goto("https://www.mercari.com/sell/")
            self._human_delay(1500, 2500)

            # Upload photos first (more human-like order)
            photos = listing.get_platform_photos("mercari")
            for photo in photos:
                if photo.local_path:
                    self.page.set_input_files('input[type="file"]', photo.local_path)
                    self._human_delay(800, 1500)  # Wait for upload

            # Fill in title (human-like typing)
            title = listing.get_platform_title("mercari")
            self._human_type('input[placeholder*="title"]', title)
            self._human_delay(500, 1000)

            # Fill description (slower for longer text)
            self._human_type('textarea[placeholder*="description"]', listing.description)
            self._human_delay(700, 1200)

            # Select condition
            condition_text = self.CONDITION_MAP.get(
                listing.condition, "good"
            ).replace("_", " ").title()
            self.page.click(f'text="{condition_text}"')
            self._human_delay(400, 800)

            # Set category (if available)
            if listing.category:
                self.page.click(f'text="{listing.category.primary}"')
                self._human_delay(400, 800)

            # Set price (type it like a human)
            self._human_type('input[placeholder*="price"]', str(int(listing.price.amount)))
            self._human_delay(800, 1500)

            # Submit listing (hesitate a bit before clicking)
            self._human_delay(1000, 2000)
            self.page.click('button:has-text("List")')

            # Wait for success and get listing URL (increased timeout to 2 minutes)
            self.page.wait_for_url("**/item/**", timeout=120000)
            listing_url = self.page.url

            # Extract listing ID from URL
            listing_id = listing_url.split("/item/")[-1].split("/")[0]

            self.browser.close()

            return {
                "listing_id": listing_id,
                "listing_url": listing_url,
            }

    @classmethod
    def from_env(cls, headless: bool = True) -> "MercariAutomationAdapter":
        """
        Create adapter from environment variables.

        Expected variables:
            - MERCARI_EMAIL
            - MERCARI_PASSWORD
            - MERCARI_HEADLESS (optional: "false" to see browser, default "true")
            - MERCARI_COOKIES_FILE (optional: path to cookies file)
        """
        email = os.getenv("MERCARI_EMAIL")
        password = os.getenv("MERCARI_PASSWORD")
        cookies_file = os.getenv("MERCARI_COOKIES_FILE", "data/mercari_cookies.json")

        # Check if headless mode should be disabled (for debugging)
        headless_env = os.getenv("MERCARI_HEADLESS", "true").lower()
        if headless_env in ["false", "0", "no"]:
            headless = False
            print("🔍 Running browser in VISIBLE mode (MERCARI_HEADLESS=false)")

        if not all([email, password]):
            raise ValueError(
                "Missing Mercari credentials in environment variables. "
                "Required: MERCARI_EMAIL, MERCARI_PASSWORD"
            )

        return cls(email, password, headless, cookies_file)


class MercariAdapter:
    """
    Unified Mercari adapter that automatically chooses between Shops API and automation.
    """

    def __init__(self, use_shops_api: bool = True, **kwargs):
        """
        Initialize Mercari adapter.

        Args:
            use_shops_api: Use Shops API (True) or automation (False)
            **kwargs: Arguments for the specific adapter
        """
        if use_shops_api:
            self.adapter = MercariShopsAdapter(**kwargs)
        else:
            self.adapter = MercariAutomationAdapter(**kwargs)

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, str]:
        """Publish listing using the configured adapter"""
        return self.adapter.publish_listing(listing)

    @classmethod
    def from_env(cls) -> "MercariAdapter":
        """
        Create adapter from environment variables.

        Checks for MERCARI_API_KEY first (Shops API), falls back to automation.
        """
        api_key = os.getenv("MERCARI_API_KEY")

        if api_key:
            # Use Shops API
            return cls(
                use_shops_api=True,
                api_key=api_key,
                shop_id=os.getenv("MERCARI_SHOP_ID"),
            )
        else:
            # Use automation - create adapter using from_env to read MERCARI_HEADLESS
            automation_adapter = MercariAutomationAdapter.from_env()
            adapter_instance = cls.__new__(cls)
            adapter_instance.adapter = automation_adapter
            return adapter_instance
