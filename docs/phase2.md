# Phase 2 — Real OCR + Verified Rule Engine

## What already existed (reused, not replaced)
VisionProvider ABC, DemoVisionProvider, basic TesseractVisionProvider,
`evaluate_all()` / `aggregate()`, evidence dicts, review workflow with
original preservation, audit architecture, API contracts, Live/Demo Mode.

## What changed
- `services/preprocess.py` (new): EXIF transpose, resize ≤2000px, grayscale,
  autocontrast, median denoise, unsharp mask. Original kept; processed copy in
  `inspection-images/<id>/processed/`.
- `services/normalize.py` (new): quantity / MRP / date / phone-email parsing.
  Every field keeps raw + normalized.
- `services/parse.py` (new): keyword + fallback regex extraction over Tesseract
  TSV word data → value, normalized, confidence (mean word conf), status
  (OK/UNREADABLE/MISSING), union bbox + source_image_id. `merge_fields()` for
  multi-image, `empty_fields()` skeleton so missing declarations are explicit.
- `services/vision.py`: Tesseract provider rewritten on the above; open failure
  when binary/image unusable; `TESSERACT_CMD` + Windows auto-detect;
  `describe_providers()` (health endpoint, no secrets).
- `rules/registry.py`: 10 rules (same 8 codes + COMMON_NAME_PRESENT +
  UNIT_SALE_PRICE_PRESENT), versions 2.0.0/1.0.0, VERIFIED ×8 (PCR 2011 Rule 6,
  sources S1–S3) / UNVERIFIED ×2. No clause text invented; out-of-scope items
  (numeral heights, permissible error, pack sizes) documented in notes.
- `rules/engine.py`: same `evaluate_all/aggregate` contract + statuses;
  confidence gate (< OCR_HIGH_CONF → REVIEW); new rules never auto-FAIL;
  results carry rule_status, source_url, verification_notes.
- `main.py`: multi-image analyze loop, per-image OCR_* audits, FIELD_EXTRACTED,
  RULE_VERSION_USED, FIELD_REVIEWED; new GET /extraction + /rules; provider +
  rule_version_used stamped on inspection; Live-with-demo-config → 503;
  report sections split into AI-extracted / deterministic / officer decisions.
- Models + `supabase/migrations/0002_phase2.sql` (additive only).
- Frontend: Result ANALYSIS summary panel (images/provider/detected/review
  counts), VERIFIED/UNVERIFIED pills + source links; Rules page same.
  No redesign.

## Verification
- `pytest tests -q`: 29 passed (rules, parse/normalize, providers).
- Synthetic PIL label → tesseract_ocr: 9/9 fields @91–96%, COMPLIANT, full
  audit chain, PDF generated.
- 2-image inspection: fields attributed to correct source images.
- `npm run build`: success.
