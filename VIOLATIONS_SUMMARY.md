# TOS Violations Summary - Specific Code Examples

## Overview

The Mercari Regular Account automation contains **4 major categories of violations**:

```
VIOLATION #1: Automated Access
├─ Browser automation (Playwright)
├─ Form submission automation
└─ Circumventing manual login requirement

VIOLATION #2: Security Evasion
├─ Hiding webdriver property
├─ Spoofing browser fingerprint
├─ Faking plugins/languages
└─ Disabling automation detection

VIOLATION #3: Credential Management
├─ Storing passwords in plaintext (.env)
├─ Storing cookies as session tokens
└─ Avoiding 2FA/verification

VIOLATION #4: Deceptive Behavior
├─ Simulating human typing
├─ Adding random delays
├─ Using visible browser to appear human
└─ Intent to circumvent detection
```

---

## VIOLATION #1: Automated Access

### What Mercari ToS Says
```
"You may not... use any form of automated access (e.g., bots, scrapers, 
or other tools) to access, use, or download data from Mercari unless 
expressly authorized by Mercari"
```

### How Code Violates It

#### File: `src/adapters/mercari_adapter.py` (Lines 189-210)

```python
class MercariAutomationAdapter:
    """
    Adapter for regular Mercari using browser automation.
    
    Uses Playwright/Puppeteer to automate listing creation when API is not available.
    This is a fallback for regular Mercari sellers without Shops API access.
    """
    
    def __init__(
        self,
        email: str,
        password: str,
        headless: bool = True,
        cookies_file: Optional[str] = None,
    ):
        """Initialize Mercari automation adapter."""
        # Stores credentials for automated login
        self.email = email
        self.password = password
        self.headless = headless
        self.cookies_file = cookies_file
        self.browser = None
        self.page = None
```

**Violation:** Lines 232-244 - Ensures Playwright is installed for browser automation
```python
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
```

#### File: `src/adapters/mercari_adapter.py` (Lines 397-409)

**Violation:** Lines 407-430 - Launches automated browser

```python
def publish_listing(self, listing: UnifiedListing) -> Dict[str, str]:
    """Publish listing to Mercari using browser automation."""
    sync_playwright = self._ensure_playwright()
    
    with sync_playwright() as p:
        # Launch browser with anti-detection settings
        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
        ]
        
        self.browser = p.chromium.launch(
            headless=self.headless,
            args=launch_args,
            downloads_path='./downloads',
        )
```

**Violation:** Lines 480-502 - Automated login and form filling

```python
# Load cookies if available, otherwise login
if self.cookies_file and os.path.exists(self.cookies_file):
    print(f"🍪 Loading saved cookies from {self.cookies_file}")
    self._load_cookies()
    # Navigate to homepage to verify cookies work
    print("📍 Navigating to Mercari to verify cookies...")
    self.page.goto("https://www.mercari.com/", wait_until="domcontentloaded", timeout=120000)
    self._human_delay(2000, 3000)
else:
    print("🔐 No cookies found, performing login...")
    self._login()
    self._save_cookies()

# Automated form filling
self.page.goto("https://www.mercari.com/sell/")
self._human_delay(1500, 2500)

# Upload photos automatically
photos = listing.get_platform_photos("mercari")
for photo in photos:
    if photo.local_path:
        self.page.set_input_files('input[type="file"]', photo.local_path)
        self._human_delay(800, 1500)

# Fill title, description, condition, price - all automatically
title = listing.get_platform_title("mercari")
self._human_type('input[placeholder*="title"]', title)
```

**Verdict:** CRITICAL VIOLATION - Entire workflow is automated without authorization

---

## VIOLATION #2: Security Evasion

### What Mercari ToS Says
```
"You may not... use tools or methods designed to circumvent or evade 
Mercari's security measures"
```

### How Code Violates It

#### File: `src/adapters/mercari_adapter.py` (Lines 410-478)

**Violation #2A: Hiding Automation Signals**

```python
# Line 410-414
self.browser = p.chromium.launch(
    headless=self.headless,
    args=launch_args,  # <-- EVASION FLAG
)

# The launch_args contain:
launch_args = [
    '--disable-blink-features=AutomationControlled',  # HIDE AUTOMATION
    '--no-sandbox',
    '--disable-dev-shm-usage',
]
```

**Analysis:**
- `--disable-blink-features=AutomationControlled` explicitly hides that this is automated
- This flag tells Chromium to remove the `navigator.webdriver` property
- Known evasion technique that Mercari specifically monitors for
- **Clear intent to deceive Mercari's detection systems**

---

**Violation #2B: Browser Fingerprinting Spoofing**

```python
# Lines 446-478
self.page.add_init_script("""
    // Hide webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined  // LIE to Mercari
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
        get: () => [1, 2, 3, 4, 5],  // FAKE DATA
    });
    
    // Mock languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],  // FAKE DATA
    });
    
    // Override permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
""")
```

**Analysis:**
- JavaScript injection to spoof browser properties
- Deliberately presents false information to Mercari
- Modifying navigator object is deception
- Each property change is designed to hide automation
- **This is technologically identical to fraud** (presenting false information)

---

**Violation #2C: Context Spoofing**

```python
# Lines 432-443
context = self.browser.new_context(
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',  # FAKE
    viewport={'width': 1920, 'height': 1080},
    locale='en-US',
    timezone_id='America/New_York',  # FAKE
    extra_http_headers={
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,...',
    }
)
```

**Analysis:**
- Faking user-agent, timezone, locale, headers
- All designed to appear as normal human browser
- Deceptive to Mercari's bot detection

---

## VIOLATION #3: Credential Management

### What Mercari ToS Says
```
"You may not... share your login credentials with third parties or 
allow others to access your account on your behalf"
```

### How Code Violates It

#### File: `.env.example` (Lines 12-15)

```
# Mercari Automation Credentials (if NOT using Shops API)
# Use your regular Mercari account
MERCARI_EMAIL=your_mercari_email@example.com
MERCARI_PASSWORD=your_mercari_password  # <-- VIOLATION
```

**Violations:**
1. **Plaintext Storage:** Password stored in unencrypted `.env` file
2. **No Encryption:** Anyone with file access gets account access
3. **Code Sharing Risk:** If repo pushed to GitHub, credentials exposed
4. **Security Anti-Pattern:** Violates all credential storage best practices

#### File: `src/adapters/mercari_adapter.py` (Lines 565-585)

**Violation: Password Handling**

```python
@classmethod
def from_env(cls, headless: bool = True) -> "MercariAutomationAdapter":
    """Create adapter from environment variables."""
    email = os.getenv("MERCARI_EMAIL")
    password = os.getenv("MERCARI_PASSWORD")  # <-- LOADED FROM .env
    cookies_file = os.getenv("MERCARI_COOKIES_FILE", "data/mercari_cookies.json")
    
    # ...
    
    return cls(email, password, headless, cookies_file)
```

**Violation: Cookie Persistence**

```python
# Lines 368-384
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
        json.dump(cookies, f)  # <-- PLAINTEXT SESSION TOKENS
```

**Analysis:**
- Session cookies saved to `data/mercari_cookies.json`
- Cookies stored in plaintext JSON
- Anyone with file access can use saved session
- Bypasses need for password (cookies are session tokens)
- **This is credential theft prevention failure**

#### File: `save_mercari_cookies.py` (Lines 8, 92, 99)

```python
# Line 8
"""
This bypasses bot detection since you're logging in like a real person.
"""

# Line 92
print("and won't need to log in (bypassing bot detection).")

# Line 99
print("\n💡 Tip: Firefox cookies work great and avoid bot detection!")
```

**Analysis:**
- Explicitly states goal is to "bypass bot detection"
- Acknowledges that cookies are being used to avoid verification
- **Conscious intent to circumvent security measures**

---

## VIOLATION #4: Deceptive Behavior

### What Mercari ToS Says
```
"You agree to use the Platform in good faith and not to engage in 
deceptive, misleading, or fraudulent practices"
```

### How Code Violates It

#### File: `src/adapters/mercari_adapter.py` (Lines 244-257)

**Violation #4A: Simulated Human Behavior**

```python
def _human_delay(self, min_ms: int = 100, max_ms: int = 500):
    """Add random human-like delay"""
    delay = random.uniform(min_ms, max_ms) / 1000
    time.sleep(delay)  # <-- SIMULATE HUMAN

def _human_type(self, selector: str, text: str):
    """Type text with human-like delays between characters"""
    self.page.click(selector)
    for char in text:
        self.page.type(selector, char, delay=random.uniform(50, 150))
        # Occasionally pause (like humans do)
        if random.random() < 0.1:  # 10% chance
            time.sleep(random.uniform(0.2, 0.5))  # <-- SIMULATE HUMAN
```

**Analysis:**
- Deliberately designed to fool detection systems
- Adding random delays explicitly to appear human
- Human-like typing speeds and pauses
- **Intent: Deceive Mercari into thinking this is human behavior**

#### File: `src/adapters/mercari_adapter.py` (Lines 258-366)

**Violation #4B: Login Impersonation**

```python
def _login(self):
    """Login to Mercari with human-like behavior"""
    # ... lots of code adding delays and trying to appear human
    
    print("📍 Navigating to Mercari login page...")
    self.page.goto("https://www.mercari.com/login/", wait_until="domcontentloaded", timeout=120000)
    
    self._human_delay(2000, 3000)  # Wait like a human would
    
    # Find email field with multiple selector attempts
    for selector in ['input[name="email"]', 'input[type="email"]', '#email', ...]:
        try:
            self.page.wait_for_selector(selector, timeout=5000, state="visible")
            email_selector = selector
            break
        except:
            continue
    
    # Type email slowly like a human
    self._human_type(email_selector, self.email)
    self._human_delay(300, 800)
    
    # Type password slowly like a human
    self._human_type(password_selector, self.password)
    self._human_delay(500, 1000)
    
    # Click submit button
    self.page.click(selector)
    
    # Wait for homepage redirect (up to 5 minutes for 2FA)
    self.page.wait_for_url("https://www.mercari.com/", timeout=300000)
```

**Analysis:**
- **Every single step is designed to appear human**
- Delays are random to avoid pattern detection
- Typing is character-by-character with human timing
- Even acknowledges 2FA support ("up to 5 minutes for 2FA verification code entry")
- **Entire workflow is deceptive**

#### File: `save_mercari_cookies.py` (Lines 30-44)

**Violation #4C: Visible Browser Deception**

```python
with sync_playwright() as p:
    # Launch visible Firefox browser (better for avoiding detection)
    print("🦊 Launching Firefox browser...")
    browser = p.firefox.launch(
        headless=False,  # Always visible - TO APPEAR HUMAN
    )
    
    # Create context with realistic settings
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='en-US',
        timezone_id='America/New_York',  # FAKE
    )
```

**Analysis:**
- Comment explicitly states: "better for avoiding detection"
- Uses Firefox specifically because it's harder to detect as Playwright
- Deliberately runs in visible mode (even though script waits for manual input)
- **Conscious choice to avoid bot detection systems**

---

## Summary: The Violations

| Violation | Type | Location | Severity |
|-----------|------|----------|----------|
| Browser automation | Automated Access | `mercari_adapter.py` 189-632 | 🔴 CRITICAL |
| Hiding webdriver | Security Evasion | `mercari_adapter.py` 447-451 | 🔴 CRITICAL |
| Spoofing browser | Security Evasion | `mercari_adapter.py` 462-478 | 🔴 CRITICAL |
| Plaintext passwords | Credential Mgmt | `.env.example` 14-15 | 🔴 CRITICAL |
| Plaintext cookies | Credential Mgmt | `save_mercari_cookies.py` 81 | 🟠 HIGH |
| Human simulation | Deceptive Behavior | `mercari_adapter.py` 244-257 | 🟠 HIGH |
| Login impersonation | Deceptive Behavior | `mercari_adapter.py` 258-366 | 🟠 HIGH |
| Detection bypass | Deceptive Behavior | `save_mercari_cookies.py` 8, 92 | 🟠 HIGH |

---

## Bottom Line

The Mercari Regular Account automation is **deliberately and comprehensively designed to circumvent Mercari's security and detection systems**.

This is not accidental or incidental - it's the core purpose of the code:

1. ✅ **It works** (at least temporarily)
2. ❌ **It violates ToS** (explicitly and repeatedly)
3. ❌ **It will be detected** (Mercari has sophisticated detection)
4. ❌ **It's deceptive** (admittedly designed to fool detection)
5. ❌ **It's not sustainable** (accounts get banned regularly)

---

**Recommendation:** Remove this code entirely or clearly mark as UNSUPPORTED/DEPRECATED.

