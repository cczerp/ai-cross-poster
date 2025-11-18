# Compliance Investigation - Document Index

## Investigation Summary

Complete compliance audit of eBay and Mercari adapters with focus on:
1. Automation methods used
2. Official APIs vs browser automation
3. Terms of Service violations
4. Compliance risks and remediation

**Date:** 2025-11-18  
**Investigator:** AI Code Analysis  
**Status:** CRITICAL FINDINGS

---

## Quick Summary

```
eBay:            ✅ SAFE & COMPLIANT (Official API)
Mercari Shops:   ✅ SAFE & COMPLIANT (Official API)
Mercari Regular: ❌ HIGH RISK (Browser automation + TOS violations)
```

**Key Findings:**
- eBay implementation is fully compliant with official Sell API
- Mercari Shops API is compliant when available
- Mercari regular account automation uses prohibited techniques
- Multiple explicit TOS violations in Mercari automation code
- Account ban risk: 60-90% within 1-6 months of regular use

---

## Documents Included

### 1. COMPLIANCE_REPORT.md (25 KB, 817 lines)
**Comprehensive technical and legal analysis**

Contents:
- Executive summary of risk levels
- Detailed breakdown of automation methods (Sections 1-2)
- Complete TOS violation analysis (Section 3)
- Company policies on automation (Section 4)
- Detailed compliance risk assessment (Section 5)
- Specific code violations with examples (Section 6)
- Platform comparison (Section 7)
- Timeline estimates for detection (Section 8)
- Detailed remediation steps (Section 9)
- Summary tables and final verdict (Section 10)
- Legal references and citations

**Best For:** Legal review, detailed understanding, compliance meeting

---

### 2. COMPLIANCE_QUICK_REFERENCE.md (7.6 KB, 295 lines)
**Quick summary and action items**

Contents:
- TL;DR summary table
- Current implementation status
- Key issues identified
- What needs to change (by timeline)
- Platform comparison table
- Code change options (keep with warnings vs remove)
- Risk mitigation strategy
- Legal exposure summary
- Anti-detection assessment
- Checklist of action items

**Best For:** Developers, quick review, action planning

---

### 3. VIOLATIONS_SUMMARY.md (15 KB, 370 lines)
**Detailed code examples of every violation**

Contents:
- Overview of 4 violation categories
- VIOLATION #1: Automated Access
  - ToS quote
  - Code examples with line numbers
  - Analysis and risk assessment
- VIOLATION #2: Security Evasion
  - Hiding automation signals
  - Browser fingerprinting spoofing
  - Context spoofing
- VIOLATION #3: Credential Management
  - Plaintext password storage
  - Cookie persistence
  - Explicit bypass statements
- VIOLATION #4: Deceptive Behavior
  - Human simulation code
  - Login impersonation
  - Detection bypass techniques
- Summary table of all violations
- Bottom-line assessment

**Best For:** Code review, developers, understanding specific violations

---

## Key Findings Summary

### What's Working ✅

**eBay Adapter** (`src/adapters/ebay_adapter.py`)
- Uses official eBay Sell API
- OAuth 2.0 authentication with user consent
- All endpoints official and documented
- No detection risk or legal exposure
- **Status:** Production-ready

**Mercari Shops API** (`src/adapters/mercari_adapter.py` lines 27-187)
- Uses official Mercari Shops API (for approved sellers)
- Proper API key authentication
- No TOS violations
- **Status:** Production-ready if API available

### What's NOT Working ❌

**Mercari Regular Account Automation** 
- Files: `src/adapters/mercari_adapter.py` (lines 189-632) + `save_mercari_cookies.py`
- Uses Playwright browser automation (prohibited)
- Stores plaintext passwords (security violation)
- Hides automation signals (TOS violation)
- Spoofs browser properties (TOS violation)
- Simulates human behavior deliberately (deceptive)
- Explicit intent to bypass bot detection
- **Status:** NOT production-ready, HIGH RISK

---

## Critical Violations Identified

| # | Violation | Mercari ToS | Code Location | Risk |
|---|-----------|------------|---------------|------|
| 1 | Automated browser access | "No automated access unless authorized" | `mercari_adapter.py` 189-632 | 🔴 CRITICAL |
| 2 | Hiding automation signals | "No tools to circumvent security" | `mercari_adapter.py` 410-414 | 🔴 CRITICAL |
| 3 | Spoofing browser properties | "No circumvention techniques" | `mercari_adapter.py` 447-478 | 🔴 CRITICAL |
| 4 | Plaintext password storage | Security anti-pattern | `.env.example` 14-15 | 🔴 CRITICAL |
| 5 | Deceptive behavior simulation | "No deceptive practices" | `mercari_adapter.py` 244-257 | 🟠 HIGH |
| 6 | Explicit detection bypass | Intent to evade | `save_mercari_cookies.py` 8, 92 | 🟠 HIGH |

---

## Account Ban Risk Assessment

### Timeline to Detection (Estimated)

| Usage Level | Detection Timeline | Ban Probability | Notes |
|-------------|-------------------|-----------------|-------|
| <5 listings/week | 3-6 months | 40-60% | Low volume, slower detection |
| 10-20 listings/week | 1-3 months | 70-85% | Medium volume, high detection |
| >50 listings/week | 1-4 weeks | 90%+ | Very high volume, rapid ban |

### Why Detection Happens

1. **Behavioral Analysis:** Mercari tracks session patterns and detects unnatural behavior
2. **Technical Signals:** Detects Playwright/Puppeteer signatures (evasion techniques are known)
3. **Content Analysis:** Identifies AI-generated listing text patterns
4. **Rate Limiting:** Flags rapid-fire uploads and unusual request patterns

---

## Required Actions

### CRITICAL (Do Immediately)
- [ ] Review COMPLIANCE_REPORT.md Section 9.1
- [ ] Stop using Mercari automation for production listings
- [ ] Add deprecation warning to MercariAutomationAdapter
- [ ] Document the compliance issue in project

### HIGH (This Month)
- [ ] Add compliance section to README.md
- [ ] Choose: keep automation as deprecated OR remove entirely
- [ ] Update .env.example to remove plaintext passwords
- [ ] Update gitignore to exclude .env files

### MEDIUM (This Quarter)
- [ ] Remove Mercari automation code (if not deprecating)
- [ ] Document transition plan to Mercari Shops API
- [ ] Investigate alternative platforms (Poshmark, Etsy, Depop)
- [ ] Add compliance testing framework

---

## Code Changes Required

### Option A: Deprecate with Warnings (Maintain backward compatibility)

```python
# Add to MercariAutomationAdapter.__init__
warnings.warn(
    "MercariAutomationAdapter violates Mercari Terms of Service. "
    "Account termination is likely within 1-6 months. "
    "Please use MercariShopsAdapter instead.",
    DeprecationWarning,
    stacklevel=2
)
```

### Option B: Remove Entirely (Clean break)

```python
# Remove:
# - MercariAutomationAdapter class
# - save_mercari_cookies.py
# - Mercari credential storage from .env
```

---

## Platform Policies Summary

### eBay ✅
- **Official Position:** Encourages automated tools via official APIs
- **What's Allowed:** Using Sell API for bulk listing creation
- **What's Prohibited:** Login credential usage, screen scraping
- **Risk:** None when using official API
- **Support:** Official developer support available

### Mercari Shops ✅
- **Official Position:** Approved for shop sellers with API access
- **What's Allowed:** Using official API for listing creation
- **What's Prohibited:** Unauthorized automated access
- **Risk:** None when using official API
- **Support:** API partner support available

### Mercari Regular ❌
- **Official Position:** No public API, no official automation support
- **What's Allowed:** Manual listing creation via website
- **What's Prohibited:** Browser automation, bot detection bypass
- **Risk:** Account ban, IP ban, legal action possible
- **Support:** None - unsupported use case

---

## Compliance Checklist

- [ ] Read COMPLIANCE_REPORT.md (full details)
- [ ] Review VIOLATIONS_SUMMARY.md (code examples)
- [ ] Understand COMPLIANCE_QUICK_REFERENCE.md (action items)
- [ ] Assess current Mercari automation usage
- [ ] Plan deprecation/removal timeline
- [ ] Update documentation with compliance notices
- [ ] Add deprecation warnings to code
- [ ] Brief legal team on findings
- [ ] Document decision in project history
- [ ] Monitor Mercari account status if currently in use

---

## Legal & Liability Notes

### eBay
- **Liability Risk:** None (using official API)
- **Potential Exposure:** None if following rate limits and documentation

### Mercari Shops
- **Liability Risk:** None (using official API)
- **Potential Exposure:** None if API terms followed

### Mercari Regular
- **Liability Risk:** HIGH
- **Potential Exposure:**
  - Account termination (immediate impact)
  - Civil lawsuit for ToS violation
  - CFAA liability (Computer Fraud and Abuse Act)
  - DMCA implications (circumventing detection)
  - Damages: account value + lost sales + legal fees

---

## References

### eBay
- https://developer.ebay.com/api-docs/sell/inventory/overview.html
- https://www.ebay.com/help/api-center/api-terms-of-use
- https://www.ebay.com/help/policies/policy-topics/ebay-prohibited-and-restricted-items

### Mercari
- https://www.mercari.com/about/terms/
- https://www.mercari.com/rules/policies/
- https://www.mercari.com/about/privacy/

### Legal
- https://en.wikipedia.org/wiki/Computer_Fraud_and_Abuse_Act
- https://www.justice.gov/criminal-cccoms/digital-millennium-copyright-act
- https://en.wikipedia.org/wiki/HiQ_Labs_v._LinkedIn (relevant case law)

---

## Files Analyzed

### Adapter Code
- `/home/user/ai-cross-poster/src/adapters/ebay_adapter.py` (388 lines)
- `/home/user/ai-cross-poster/src/adapters/mercari_adapter.py` (632 lines)

### Browser Automation Scripts
- `/home/user/ai-cross-poster/save_mercari_cookies.py` (111 lines)

### Configuration
- `/home/user/ai-cross-poster/.env.example` (79 lines)
- `/home/user/ai-cross-poster/requirements.txt` (23 lines)

### Documentation
- `/home/user/ai-cross-poster/README.md` (745 lines)

---

## Report Statistics

| Document | Size | Lines | Focus Area |
|----------|------|-------|-----------|
| COMPLIANCE_REPORT.md | 25 KB | 817 | Comprehensive legal analysis |
| COMPLIANCE_QUICK_REFERENCE.md | 7.6 KB | 295 | Quick summary & actions |
| VIOLATIONS_SUMMARY.md | 15 KB | 370 | Code examples & specifics |
| **Total** | **47.6 KB** | **1,482** | Complete audit |

---

## Next Steps

1. **Read the Reports** (25-30 minutes)
   - Start with COMPLIANCE_QUICK_REFERENCE.md (TL;DR)
   - Read COMPLIANCE_REPORT.md (full details)
   - Review VIOLATIONS_SUMMARY.md (code evidence)

2. **Assess Impact** (15-20 minutes)
   - Determine if Mercari automation is currently in production use
   - Identify number of listings created via automation
   - Estimate timeline for action

3. **Plan Changes** (30-45 minutes)
   - Decide: Deprecate with warnings OR remove entirely
   - Plan migration for existing automated listings
   - Draft updates to README and documentation

4. **Implement Changes** (varies)
   - Add deprecation warnings
   - Update documentation
   - Remove/replace automation code
   - Brief stakeholders

---

**Report Prepared:** 2025-11-18  
**Classification:** INTERNAL - LEGAL & COMPLIANCE  
**Distribution:** Development Team, Legal Review  
**Action Required:** Yes - See Section 9 of COMPLIANCE_REPORT.md

