#!/usr/bin/env python3
"""
Mercari Cookie Saver
====================
This script opens a browser, lets you log in to Mercari manually,
then saves your cookies for automated posting.

This bypasses bot detection since you're logging in like a real person.

Usage:
    python save_mercari_cookies.py
"""

import os
import json
from playwright.sync_api import sync_playwright
import time

def save_mercari_cookies():
    """Open browser, let user login, save cookies"""

    print("=" * 70)
    print("🍪 MERCARI COOKIE SAVER")
    print("=" * 70)
    print("\nThis will open a browser window for you to log in to Mercari.")
    print("After you log in successfully, the cookies will be saved.")
    print("\nPress ENTER when ready...")
    input()

    with sync_playwright() as p:
        # Launch visible Firefox browser (better for avoiding detection)
        print("🦊 Launching Firefox browser...")
        browser = p.firefox.launch(
            headless=False,  # Always visible
        )

        # Create context with realistic settings
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
        )

        page = context.new_page()

        # Navigate to Mercari login
        print("\n📍 Opening Mercari login page...")
        print("⏳ This may take a moment...")
        page.goto("https://www.mercari.com/login/", wait_until="domcontentloaded", timeout=120000)
        print("✅ Page loaded!")

        # Wait a bit for the page to fully render
        time.sleep(3)

        print("\n" + "=" * 70)
        print("👉 Please log in to Mercari in the browser window")
        print("=" * 70)
        print("\nTips:")
        print("1. Log in normally (email/password)")
        print("2. Complete any 2FA if required")
        print("3. Wait until you see the Mercari homepage")
        print("4. Come back here and press ENTER")
        print("\n⏳ Waiting for you to log in...")

        input("\nPress ENTER after you've logged in successfully: ")

        # Get current URL to verify login
        current_url = page.url
        print(f"\n📍 Current URL: {current_url}")

        if "login" in current_url.lower():
            print("\n⚠️  Warning: Still on login page. Make sure you're logged in!")
            print("Press ENTER to continue anyway, or CTRL+C to cancel: ")
            input()

        # Save cookies
        cookies = context.cookies()

        # Create data directory
        os.makedirs("data", exist_ok=True)
        cookies_file = "data/mercari_cookies.json"

        with open(cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)

        print(f"\n✅ Saved {len(cookies)} cookies to {cookies_file}")
        print("\n" + "=" * 70)
        print("🎉 SUCCESS!")
        print("=" * 70)
        print("\nYour Mercari session has been saved!")
        print("From now on, automated posting will use these cookies")
        print("and won't need to log in (bypassing bot detection).")
        print("\n💡 If posting fails in the future, just run this script again")
        print("   to refresh your cookies.")

        browser.close()

        print("\n✅ Done! You can now use the GUI to post to Mercari.")
        print("\n💡 Tip: Firefox cookies work great and avoid bot detection!")

if __name__ == "__main__":
    try:
        save_mercari_cookies()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("\nMake sure you have Playwright and Firefox installed:")
        print("  pip install playwright")
        print("  playwright install firefox")
