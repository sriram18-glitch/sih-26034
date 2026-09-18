"""Rule registry — versioned, sourced, status-labelled.

rule_status:
  VERIFIED   — requirement confirmed against the cited official source below.
  UNVERIFIED — heuristic/conditional; NOT an authoritative legal claim.

Sources (all official, Dept. of Consumer Affairs / Legal Metrology):
  S1 = Legal Metrology Division overview — mandatory declarations on pre-packaged
       commodities (i..x), https://consumeraffairs.gov.in/pages/legal-metrology-overview
  S2 = FAQs on Packaged Commodities Rules 2011 (Consumer Affairs),
       https://consumeraffairs.gov.in/public/upload/admin/cmsfiles/whatsnews/FAQs_on_Packaged_Commodities%2C_Rules_2011_whatsnews.pdf
  S3 = The Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6
       (declarations on every package) & Rule 9 (manner of declaration),
       https://www.indiacode.nic.in/.../lm_pcr_2011.pdf
  S4 = PIB amendment note 29-07-2024 (scope/uniformity proposal),
       https://www.pib.gov.in/PressReleasePage.aspx?PRID=2033114

These entries encode *presence/readability screening checks*, not quantitative
metrology (numeral heights, permissible error, standard pack sizes) — those
require physical measurement and are explicitly OUT OF SCOPE (see notes).
Verification re-checked Sept 2026 against Dept. of Consumer Affairs sources
(principal rules GSR 202(E) 07.03.2011; amendments ongoing, e.g. 2026 Second
Amendment on e-commerce country-of-origin filters). Amendments after the
verification date must be re-checked before operational use.
"""
S1 = "https://consumeraffairs.gov.in/pages/legal-metrology-overview"
S2 = ("https://consumeraffairs.gov.in/public/upload/admin/cmsfiles/whatsnews/"
      "FAQs_on_Packaged_Commodities%2C_Rules_2011_whatsnews.pdf")
S3 = "https://upload.indiacode.nic.in/showfile?actid=AC_MP_74_283_00006_00006_1547532512849&filename=lm_pcr_2011.pdf&type=rule"

RULES = [
    {
        "rule_code": "NET_QUANTITY_PRESENT",
        "rule_version": "2.0.0",
        "title": "Net quantity declaration present",
        "description": "Every package must declare net quantity in standard units of weight/measure/number (excl. wrapper).",
        "requirement": "net_quantity field must be present and readable",
        "severity": "HIGH",
        "rule_status": "VERIFIED",
        "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_section": "Rule 6(1) — mandatory declaration (iv): net quantity in standard units",
        "source_url": S1,
        "verification_notes": "Confirmed via Dept. of Consumer Affairs mandatory-declarations list (iv) and S2 FAQ Q8 (net quantity definition). Quantitative checks (standard units, permissible error, pack sizes) are NOT encoded.",
        "is_demo_rule": False,
    },
    {
        "rule_code": "MRP_PRESENT",
        "rule_version": "2.0.0",
        "title": "MRP declaration present",
        "description": "Retail sale price (Maximum Retail Price, inclusive of all taxes) must be declared.",
        "requirement": "mrp field must be present and readable",
        "severity": "HIGH",
        "rule_status": "VERIFIED",
        "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_section": "Rule 6(1)(e) — retail sale price of the package; S2 FAQ Q23 (sale below MRP permitted)",
        "source_url": S1,
        "verification_notes": "Presence check only. Lower-price stickers (Rule 6(3) proviso) and tax-inclusive wording are not distinguished by this check.",
        "is_demo_rule": False,
    },
    {
        "rule_code": "MRP_FORMAT_VALID",
        "rule_version": "2.0.0",
        "title": "MRP format includes currency and amount",
        "description": "MRP should be recognizable as a price: currency marker (Rs/INR/₹) plus numeric amount.",
        "requirement": "mrp value must contain currency marker and number",
        "severity": "WARNING",
        "rule_status": "VERIFIED",
        "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_section": "Rule 6 + Rule 9(1)(a) — declarations legible and prominent; Dept. overview (vii): 'MRP Rs… inclusive of all taxes'",
        "source_url": S1,
        "verification_notes": "PARTIAL: format heuristic only. Rule 9 numeral-height tables (amended GSR 629(E) 2017) require physical measurement and are NOT encoded.",
        "is_demo_rule": False,
    },
    {
        "rule_code": "COMMON_NAME_PRESENT",
        "rule_version": "1.0.0",
        "title": "Common/generic commodity name present",
        "description": "Package must bear the common or generic name of the commodity contained in it.",
        "requirement": "product_name field must be present and readable",
        "severity": "WARNING",
        "rule_status": "VERIFIED",
        "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_section": "Rule 6(1) — mandatory declaration (iii): common/generic name",
        "source_url": S1,
        "verification_notes": "Product-name detection from OCR is positional/heuristic; missing name yields REVIEW (extraction uncertainty), never an automatic violation.",
        "is_demo_rule": False,
    },
    {
        "rule_code": "MANUFACTURER_DETAILS_PRESENT",
        "rule_version": "2.0.0",
        "title": "Manufacturer/packer details present",
        "description": "Name and address of manufacturer (and packer where different; importer for imports) must be declared.",
        "requirement": "manufacturer field present and readable",
        "severity": "HIGH",
        "rule_status": "VERIFIED",
        "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_section": "Rule 6(1) — mandatory declaration (i): name/address of manufacturer/packer/importer (S2 FAQ Q19)",
        "source_url": S1,
        "verification_notes": "Presence check on name+address text. Distinguishing manufacturer vs packer vs marketer roles is out of scope.",
        "is_demo_rule": False,
    },
    {
        "rule_code": "CONSUMER_CARE_PRESENT",
        "rule_version": "2.0.0",
        "title": "Consumer care details present",
        "description": "Consumer-care contact (address/phone/email; working toll-free number accepted) must be declared.",
        "requirement": "consumer_care field present",
        "severity": "WARNING",
        "rule_status": "VERIFIED",
        "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_section": "Rule 6 — consumer care details; S2 FAQ Q28 (toll-free accepted), Q47–48",
        "source_url": S2,
        "verification_notes": "Presence of contact details only. Operational validity of phone/email is not verified.",
        "is_demo_rule": False,
    },
    {
        "rule_code": "DATE_DECLARATION_PRESENT",
        "rule_version": "2.0.0",
        "title": "Date declaration present",
        "description": "Month and year of manufacture/pre-packing/import; best-before/use-by where the commodity can become unfit.",
        "requirement": "mfg_date or expiry/best_before present",
        "severity": "WARNING",
        "rule_status": "VERIFIED",
        "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_section": "Rule 6(1) — declarations (v) month/year of manufacture, (vi) best-before/use-by; S1 overview (v)–(vi)",
        "source_url": S1,
        "verification_notes": "Applicability varies (food/seeds/cosmetics exceptions; 2022 amendments). Absence yields REVIEW with manual-check advice, not FAIL.",
        "is_demo_rule": False,
    },
    {
        "rule_code": "UNIT_SALE_PRICE_PRESENT",
        "rule_version": "1.0.0",
        "title": "Unit sale price present (conditional)",
        "description": "Unit sale price declaration applies from 01.10.2022 with exemptions (e.g. combination/group packages, wholesale).",
        "requirement": "unit sale price present where applicable",
        "severity": "INFO",
        "rule_status": "UNVERIFIED",
        "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011 (as amended)",
        "source_section": "Rule 6(11) exemptions; S2 FAQ Q11, Q35–37 — applicability conditional, configuration required",
        "source_url": S2,
        "verification_notes": "UNVERIFIED: applicability is conditional per commodity/package type. Never FAILs — REVIEW at most. Configure applicability before operational use.",
        "is_demo_rule": False,
    },
    {
        "rule_code": "BATCH_LOT_PRESENT",
        "rule_version": "2.0.0",
        "title": "Batch/lot identification present",
        "description": "Batch or lot marking aids traceability but is not in the PCR mandatory-declaration list.",
        "requirement": "batch_lot present",
        "severity": "INFO",
        "rule_status": "UNVERIFIED",
        "source_document": "Configuration heuristic",
        "source_section": "Not a PCR Rule 6 mandatory declaration — traceability aid only",
        "source_url": S1,
        "verification_notes": "UNVERIFIED: absence never fails. Informational only.",
        "is_demo_rule": False,
    },
    {
        "rule_code": "COUNTRY_OF_ORIGIN_FOR_IMPORT",
        "rule_version": "2.0.0",
        "title": "Country of origin for imported goods",
        "description": "Imported packages must declare country of origin/manufacture alongside importer details.",
        "requirement": "country_of_origin required when importer present",
        "severity": "WARNING",
        "rule_status": "VERIFIED",
        "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_section": "Rule 6(1) — mandatory declaration (ii): country of origin for imports (S2 FAQ Q19)",
        "source_url": S1,
        "verification_notes": "Conditional check: applies only when an importer declaration is detected.",
        "is_demo_rule": False,
    },
]
