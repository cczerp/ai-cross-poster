1. Inventory Management System (Missing Category)
Your plan needs sections for:
Unified inventory table
Draft → Active → Sold → Shipped → Archived states
Storage location system (bins/shelves/boxes)
SKU optional + auto-SKU generator
Bulk editing
Cross-platform inventory linking
Duplicates detection
COGS tracking
Notes, tags, item history logs
This is completely missing.
2. CSV Import System (Missing Entirely)
The Integration Plan includes CSV export for platform —
but not the CSV import + normalization system used to:
Read CSVs from any marketplace
Normalize into your unified inventory schema
Auto-assign SKUs if missing
Detect duplicates
Optional immediate sync vs draft mode
This is a core feature missing from the plan.
3. Draft → Listing Workflow (Missing)
Your platform requires:
All imported items go → Drafts
User edits them
Then publishes to all platforms
Single-item, batch, or full-draft publish
Sync to API platforms
Build CSVs for CSV-only platforms
This workflow is not present anywhere in the Integration Plan.
4. Sales Sync Engine + Notifications (Missing)
Your earlier requirements included a huge system:
Detect sale (API or CSV-based)
Pull buyer info, shipping label, fees
Fetch storage location
Notify user
Mark item sold everywhere
15-minute delay → auto-delist from other platforms
Update profit + tax data
Completely missing.
The Plan only documents platform adapters — not the sync logic.
5. SEO Automation (Missing)
You require:
SEO intelligent title generation
Keyword enrichment
Category prediction
Sync SEO metadata across all platforms
When one listing is updated → update all others
The Integration Plan has zero mention of SEO features.
6. Tax & Accounting System (Missing)
Needed features:
Profit per item
Cost of goods
Platform fee tracking
1099-K reconciliation
Monthly/annual tax reports
Exportable transaction logs
This system does not appear anywhere in the Integration Plan.
7. Invoicing + Local Sales Tools (Missing)
You need:
PDF invoice generator
Link/email delivery
Mark paid/unpaid
Auto-mark sold after payment
Add taxes, shipping, discounts
No mention in the Plan.
8. Image Pipeline (Missing)
Required features:
EXIF wipe
Auto-resize + compress per platform
Background removal (if included)
Auto-rotate correction
Multi-photo uploader
Completely absent from the Integration Plan.
9. Automation Worker Layer (Missing)
Required background jobs like:
Sync queue
Listing creation workers
Delisting workers
Scheduled CSV feed updates
Image optimization jobs
Retry/backoff system
Error logging/reporting
The Integration Plan does not cover the automation engine at all.
10. Unified Cross-Platform Listing Manager (Missing)
You need one “source of truth” system that:
Manages every synced listing
Tracks per-platform status
Tracks errors
Shows which marketplaces each item currently lives on
Offers “List Everywhere”, “Delist Everywhere”, and “Relist Everywhere”
This logic is not in the Integration Plan.
11. User Dashboard & UI Requirements (Missing)
Missing UI work:
Consistent login/signup/logout location
Site-wide dark mode
Unified navbar
Listing manager UI
Inventory table UI
Draft management UI
Platform connection UI
CSV import/export UI
Bulk editing UI
Notifications UI
Sales dashboard
Integration Plan only covers backend adapters.
12. Storage System (Missing)
You need:
Bin assignment
Location lookup on sale
Auto-bin suggestion
Bulk reassignments
Not present in the Integration Plan.
13. Item Lifecycle Automation (Missing)
You specified:
If item sells on one platform → delist everywhere
After 15 minutes
Then archive item
The Plan includes platform adapters, but not this automation.
14. Marketplace Draft Handling (Missing)
You wanted:
Some platforms use drafts
Some use CSV
Some need templates
There is no unified abstraction for “draft mode” in the current Plan.
15. Multi-Platform Sync Logic (Missing)
Your earlier requirements include:
One listing = on truth
→ propagate outwad
→ reconcile back i
→ update all platforms on edit
None of this sync logic is documented.
16. PDF + Document Generation (Missing)
You need:
Invoices
Packing slips
Pick lists
Storage labels
Not included anywhere.
17. Real-Time Sync + Scheduling (Missing)
Your needs:
Scheduled nightly sync
Quick-sync mode
Real-time updates for API platforms
Polling/refresh for CSV platforms
Not documented.
18. Cross-Site SEO Synchronization (Missing)
You require:
Every platform gets identical SEO
Edits are propagated everywhere
Multi-market SEO harmonizer
Also not documented.
19. Multi-Platform Draft Synchronization (Missing)
You need:
User edits one item
All platform drafts update accordingly
SEO updates accordingly
Not present.
20. Billing & Subscription System (You will need later)
Your Monetization section exists
but actual implementation steps are missing:
Subscription tiers
Stripe integration
API limits per tier
Feature gates
Per-plan quotas
21. Mobile App Requirements (Incomplete)
Integration Plan only lists:
CSV download
Template copy/paste
Feed management

Missing:
Inventory
Drafts
Sales notifications
Cross-platform sync controls
Barcode scanning for storage/bin assignment

# Platform Integration Plan
## Compliant Multi-Platform Cross-Posting

This document outlines the **compliant** integration plan for all supported platforms. Every platform listed here uses **officially approved** methods for automation.

---

## ✅ Currently Implemented (Compliant)

### 1. eBay
- **Method:** Official Sell API (REST)
- **Authentication:** OAuth 2.0
- **Documentation:** https://developer.ebay.com/api-docs/sell/inventory/overview.html
- **Status:** ✅ Production-ready
- **File:** `src/adapters/ebay_adapter.py`
- **Compliance:** Fully compliant, no TOS violations

### 2. Mercari Shops
- **Method:** Official Shops API (REST)
- **Authentication:** API Key
- **Documentation:** https://developer.mercari.com
- **Status:** ✅ Production-ready (if API key available)
- **File:** `src/adapters/mercari_adapter.py`
- **Compliance:** Fully compliant, no TOS violations
- **Note:** Requires Mercari Shops (business) account

---

## 🚀 Planned Integrations (Priority Order)

### TIER 1: Official APIs (Highest Priority)

#### 3. Poshmark - CSV Bulk Upload
- **Method:** CSV file upload (officially supported)
- **Authentication:** OAuth 2.0 or username/password for CSV generation
- **Documentation:** https://poshmark.com/sell/bulk
- **Implementation:**
  - Generate CSV from UnifiedListing
  - User downloads CSV
  - User uploads to Poshmark manually OR auto-upload if API available
- **Fields:**
  ```csv
  Title,Description,Category,Brand,Size,Color,Condition,Price,Shipping,Photo1,Photo2,Photo3...
  ```
- **File to create:** `src/adapters/poshmark_adapter.py`
- **Estimated effort:** 2-3 days
- **Compliance:** ✅ CSV upload is officially supported

#### 4. Etsy
- **Method:** Official Etsy API v3
- **Authentication:** OAuth 2.0
- **Documentation:** https://developers.etsy.com/documentation
- **API Endpoint:** `POST /v3/application/shops/{shop_id}/listings`
- **Rate Limits:** 10,000 requests/day
- **File to create:** `src/adapters/etsy_adapter.py`
- **Estimated effort:** 3-4 days
- **Compliance:** ✅ Fully compliant

#### 5. Shopify
- **Method:** Official Admin API
- **Authentication:** API Key + Access Token
- **Documentation:** https://shopify.dev/api/admin-rest/2024-01/resources/product
- **API Endpoint:** `POST /admin/api/2024-01/products.json`
- **File to create:** `src/adapters/shopify_adapter.py`
- **Estimated effort:** 2-3 days
- **Compliance:** ✅ Fully compliant
- **Note:** User needs their own Shopify store

#### 6. Depop
- **Method:** Official API (for approved sellers)
- **Authentication:** API Key
- **Documentation:** Contact Depop for API access
- **Alternative:** CSV export for manual upload
- **File to create:** `src/adapters/depop_adapter.py`
- **Estimated effort:** 3-4 days (pending API access)
- **Compliance:** ✅ Compliant with API; CSV also allowed

#### 7. Bonanza
- **Method:** CSV bulk upload + API (if available)
- **Authentication:** API token
- **Documentation:** https://www.bonanza.com/developer_api
- **Alternative:** Generate CSV for manual upload
- **File to create:** `src/adapters/bonanza_adapter.py`
- **Estimated effort:** 2 days
- **Compliance:** ✅ CSV upload officially supported

---

### TIER 2: Catalog/Feed Systems

#### 8. Facebook Shops / Marketplace (Catalog Mode)
- **Method:** Facebook Catalog/Product Feed
- **Authentication:** Facebook Business Account + Access Token
- **Documentation:** https://developers.facebook.com/docs/marketing-api/catalog
- **Implementation:**
  - Create product feed (CSV or XML)
  - Upload to Facebook Catalog
  - Auto-sync to Marketplace
- **Feed Format:**
  ```csv
  id,title,description,availability,condition,price,link,image_link,brand,google_product_category
  ```
- **File to create:** `src/adapters/facebook_catalog_adapter.py`
- **Estimated effort:** 4-5 days
- **Compliance:** ✅ Catalog mode is officially supported

#### 9. Google Shopping
- **Method:** Google Merchant Center Feed
- **Authentication:** Google Account + Merchant Center
- **Documentation:** https://developers.google.com/shopping-content/guides/quickstart
- **API:** Content API for Shopping
- **Feed Format:** Google Product Feed XML/CSV
- **File to create:** `src/adapters/google_shopping_adapter.py`
- **Estimated effort:** 4-5 days
- **Compliance:** ✅ Fully compliant via Merchant Center

#### 10. Pinterest Product Pins
- **Method:** Pinterest Catalogs + Pins API
- **Authentication:** OAuth 2.0
- **Documentation:** https://developers.pinterest.com/docs/api/v5/
- **API Endpoint:** `POST /v5/pins`
- **File to create:** `src/adapters/pinterest_adapter.py`
- **Estimated effort:** 3-4 days
- **Compliance:** ✅ Fully compliant

---

### TIER 3: Other Platforms (Lower Priority)

#### 11. WooCommerce
- **Method:** WooCommerce REST API
- **Authentication:** Consumer Key + Consumer Secret
- **Documentation:** https://woocommerce.github.io/woocommerce-rest-api-docs/
- **API Endpoint:** `POST /wp-json/wc/v3/products`
- **File to create:** `src/adapters/woocommerce_adapter.py`
- **Estimated effort:** 2-3 days
- **Compliance:** ✅ Fully compliant
- **Note:** User needs their own WooCommerce site

#### 12. Craigslist
- **Method:** Email-to-post OR manual posting assistance
- **Authentication:** Email
- **Documentation:** Craigslist TOS prohibits automation
- **Implementation:** Generate email with listing details, user forwards to Craigslist
- **File to create:** `src/adapters/craigslist_email_adapter.py`
- **Estimated effort:** 1 day
- **Compliance:** ⚠️ NO AUTOMATION - Email template only
- **Note:** Cannot automate; provide email template for manual posting

#### 13. OfferUp
- **Method:** CSV export for manual upload (no public API)
- **Authentication:** N/A
- **Documentation:** None publicly available
- **Implementation:** Generate CSV, user uploads manually
- **File to create:** `src/adapters/offerup_csv_adapter.py`
- **Estimated effort:** 1 day
- **Compliance:** ✅ CSV generation is safe

#### 14. VarageSale
- **Method:** Manual posting assistance (no API)
- **Authentication:** N/A
- **Documentation:** TOS prohibits automation
- **Implementation:** Generate listing text + photo URLs for manual posting
- **File to create:** `src/adapters/varagesale_template_adapter.py`
- **Estimated effort:** 1 day
- **Compliance:** ⚠️ NO AUTOMATION - Template only

#### 15. Nextdoor (Business)
- **Method:** Nextdoor Business API (if available)
- **Authentication:** Business account required
- **Documentation:** https://business.nextdoor.com/
- **Implementation:** Check if API exists; otherwise CSV/template
- **File to create:** `src/adapters/nextdoor_adapter.py`
- **Estimated effort:** 2-3 days (pending API verification)
- **Compliance:** ✅ If using business tools; ⚠️ no automation for personal

#### 16. Ecrater
- **Method:** CSV bulk upload
- **Authentication:** Account login
- **Documentation:** https://www.ecrater.com/help.php
- **Implementation:** Generate CSV for upload
- **File to create:** `src/adapters/ecrater_adapter.py`
- **Estimated effort:** 1-2 days
- **Compliance:** ✅ CSV upload supported

#### 17. Ruby Lane
- **Method:** CSV import
- **Authentication:** Seller account
- **Documentation:** https://www.rubylane.com/
- **Implementation:** Generate CSV for upload
- **File to create:** `src/adapters/rubylane_adapter.py`
- **Estimated effort:** 1-2 days
- **Compliance:** ✅ CSV upload supported

#### 18. Chairish
- **Method:** Manual upload assistance (no API)
- **Authentication:** N/A
- **Documentation:** No public API
- **Implementation:** Generate listing template + photo prep
- **File to create:** `src/adapters/chairish_template_adapter.py`
- **Estimated effort:** 1 day
- **Compliance:** ⚠️ NO AUTOMATION - Template only

---

## 📐 Technical Architecture

### Adapter Interface

All platform adapters will implement a common interface:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..schema.unified_listing import UnifiedListing

class PlatformAdapter(ABC):
    """Base class for all platform adapters"""

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate platform credentials"""
        pass

    @abstractmethod
    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        """Convert UnifiedListing to platform-specific format"""
        pass

    @abstractmethod
    def publish_listing(self, listing: UnifiedListing) -> Dict[str, str]:
        """Publish listing to platform"""
        pass

    @abstractmethod
    def get_compliance_status(self) -> str:
        """Return compliance status: 'api', 'csv', 'template', 'manual'"""
        pass
```

### Integration Types

1. **API Integration** (eBay, Etsy, Shopify, etc.)
   - Direct REST API calls
   - OAuth 2.0 or API Key authentication
   - Real-time posting

2. **CSV Export** (Poshmark, Bonanza, etc.)
   - Generate CSV file
   - User uploads to platform
   - Batch processing

3. **Catalog/Feed** (Facebook, Google Shopping, Pinterest)
   - Generate product feed (CSV/XML)
   - Auto-sync via platform APIs
   - Scheduled updates

4. **Template Generation** (Craigslist, VarageSale, Chairish)
   - Generate formatted listing text
   - Copy/paste by user
   - No automation

---

## 🔐 Compliance Framework

### Rules for All Adapters

1. **NO browser automation** unless explicitly allowed by platform TOS
2. **Only use official APIs** where available
3. **Respect rate limits** on all platforms
4. **Store credentials securely** (environment variables, never in code)
5. **Document compliance status** in each adapter
6. **Provide clear warnings** for manual-only platforms

### Compliance Checklist Template

For each new adapter, verify:

- [ ] Platform TOS allows automation/API use
- [ ] Using official, documented API
- [ ] Authentication follows platform guidelines
- [ ] Rate limits are respected
- [ ] No anti-detection techniques needed
- [ ] No credential storage in code
- [ ] Compliance status documented in code
- [ ] User informed of any manual steps required

---

## 📊 Implementation Roadmap

### Phase 1: CSV Export Framework (Week 1-2) ✅ MOSTLY COMPLETE
- [x] ~~Create `CSVExportAdapter` base class~~ ✅ DONE (base_adapter.py)
- [x] ~~Implement Poshmark CSV~~ ✅ DONE (poshmark_adapter.py)
- [x] ~~Implement Bonanza CSV~~ ✅ DONE (all_platforms.py)
- [x] ~~Implement Ecrater CSV~~ ✅ DONE (all_platforms.py)
- [x] ~~Implement Ruby Lane CSV~~ ✅ DONE (all_platforms.py)
- [x] ~~Add CSV download to GUI~~ ✅ DONE (routes_main.py /api/export-csv)
- [ ] **[PRIORITY 1]** Add CSV download to mobile app

### Phase 2: Feed/Catalog System (Week 3-4) ✅ MOSTLY COMPLETE
- [x] ~~Create `FeedAdapter` base class~~ ✅ DONE (base_adapter.py)
- [x] ~~Implement Facebook Catalog~~ ✅ DONE (all_platforms.py FacebookShopsAdapter)
- [x] ~~Implement Google Shopping~~ ✅ DONE (all_platforms.py GoogleShoppingAdapter)
- [x] ~~Implement Pinterest Catalog~~ ✅ DONE (all_platforms.py PinterestAdapter)
- [ ] **[PRIORITY 2]** Add feed generation to backend API
- [ ] **[PRIORITY 3]** Add scheduling for auto-sync

### Phase 3: API Integrations (Week 5-8) ✅ MOSTLY COMPLETE
- [x] ~~Implement Etsy API~~ ✅ DONE (all_platforms.py EtsyAdapter)
- [x] ~~Implement Shopify API~~ ✅ DONE (all_platforms.py ShopifyAdapter)
- [x] ~~Implement Depop API (if available)~~ ✅ DONE (all_platforms.py DepopAdapter)
- [x] ~~Implement WooCommerce API~~ ✅ DONE (all_platforms.py WooCommerceAdapter)
- [ ] **[PRIORITY 4]** Add OAuth flows to mobile app
- [ ] **[PRIORITY 5]** Add platform connection UI

### Phase 4: Template System (Week 9) ✅ COMPLETE
- [x] ~~Create `TemplateAdapter` base class~~ ✅ DONE (base_adapter.py)
- [x] ~~Implement Craigslist email template~~ ✅ DONE (all_platforms.py CraigslistAdapter)
- [x] ~~Implement VarageSale template~~ ✅ DONE (all_platforms.py VarageSaleAdapter)
- [x] ~~Implement Chairish template~~ ✅ DONE (all_platforms.py ChairishAdapter)
- [x] ~~Implement OfferUp template~~ ✅ DONE (all_platforms.py OfferUpAdapter as CSV)
- [ ] **[PRIORITY 7]** Add copy/paste UI to mobile app

### Phase 5: Mobile App Updates (Week 10-11) ⚠️ IN PROGRESS
- [x] ~~Add platform selector UI~~ ✅ DONE (templates/create.html)
- [x] ~~Add CSV download feature~~ ✅ DONE (web app only, see [PRIORITY 1] for mobile)
- [ ] **[PRIORITY 6]** Add feed management
- [ ] **[PRIORITY 7]** Add template copy/paste (duplicate - see Phase 4)
- [ ] **[PRIORITY 8]** Add platform status indicators
- [ ] **[PRIORITY 9]** Update onboarding flow

### Additional Priority Tasks
- [ ] **[PRIORITY 10]** Complete API integration testing and OAuth credential validation

---

## 💰 Monetization by Platform Type

### Free Tier
- Template generation (Craigslist, VarageSale, etc.)
- CSV export for 2 platforms
- 10 listings/month total

### Pro Tier ($9.99/month)
- CSV export for all platforms
- Feed/catalog for 2 platforms (Facebook, Google)
- API posting to 3 platforms
- Unlimited listings

### Business Tier ($29.99/month)
- All platforms unlocked
- Unlimited API posting
- Bulk tools
- Auto-sync feeds
- Priority support

---

## 🎯 Success Metrics

- **Compliance:** 100% of integrations TOS-compliant
- **Coverage:** Support 15+ platforms
- **User satisfaction:** 90%+ positive reviews
- **Ban rate:** 0% (due to compliant methods)
- **Time saved:** 80% reduction in listing time

---

## 📞 Platform Contact Info

If API access is needed:

- **Etsy:** https://www.etsy.com/developers/register
- **Shopify:** https://partners.shopify.com/
- **Depop:** business@depop.com
- **Facebook:** https://developers.facebook.com/
- **Pinterest:** https://developers.pinterest.com/
- **Google:** https://merchants.google.com/

---

**Last Updated:** 2025-11-18
**Status:** Planning Phase
**Compliance:** 100% (all methods pre-approved)
