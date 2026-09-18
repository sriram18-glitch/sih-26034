"""Deterministic rule engine — no LLM calls. Pure functions, fully testable."""
import os
import re
from typing import Dict, List
from app.rules.registry import RULES

def _high_conf() -> float:
    try:
        return float(os.getenv("OCR_HIGH_CONF", "0.75"))
    except ValueError:
        return 0.75

def _field(fields: Dict, name: str):
    return fields.get(name, {"value": "", "status": "MISSING", "confidence": 0.0})

def _is_ok(f):
    return bool(f.get("value", "").strip()) and f.get("status", "MISSING") == "OK"

def _confident(f, high=None):
    """HIGH-confidence reads are auto-usable; below-high goes to human review."""
    try:
        return float(f.get("confidence", 0.0)) >= (high if high is not None else _high_conf())
    except (TypeError, ValueError):
        return False

def _result(rule, status, field, expected, observed, explanation, evidence=None):
    return {
        "rule_code": rule["rule_code"],
        "rule_version": rule["rule_version"],
        "status": status,
        "severity": rule["severity"],
        "field": field,
        "expected": expected,
        "observed": observed,
        "explanation": explanation,
        "evidence": evidence or {},
        "source_reference": f"{rule.get('source_document','')} — {rule.get('source_section','')}".strip(" —"),
        "source_url": rule.get("source_url", ""),
        "rule_status": rule.get("rule_status", "UNVERIFIED"),
        "verification_notes": rule.get("verification_notes", ""),
        "is_demo_rule": rule.get("is_demo_rule", False),
        "title": rule["title"],
    }

def evaluate_all(fields: Dict) -> List[dict]:
    by_code = {r["rule_code"]: r for r in RULES}
    high = _high_conf()
    out = []

    # NET_QUANTITY_PRESENT
    r = by_code["NET_QUANTITY_PRESENT"]
    f = _field(fields, "net_quantity")
    if _is_ok(f):
        out.append(_result(r, "PASS", "net_quantity", "Readable net quantity", f["value"], "Net quantity declaration found."))
    elif f.get("status") == "UNREADABLE":
        out.append(_result(r, "REVIEW", "net_quantity", "Readable net quantity", f["value"], "Net quantity could not be confidently read. Human verification required."))
    else:
        out.append(_result(r, "FAIL", "net_quantity", "Readable net quantity", f.get("value", ""), "Net quantity declaration missing. Potential non-compliance — verify."))

    # MRP_PRESENT
    r = by_code["MRP_PRESENT"]
    f = _field(fields, "mrp")
    if _is_ok(f):
        out.append(_result(r, "PASS", "mrp", "Readable MRP", f["value"], "MRP declaration found."))
    elif f.get("status") == "UNREADABLE":
        out.append(_result(r, "REVIEW", "mrp", "Readable MRP", f["value"], "MRP unreadable. Human verification required."))
    else:
        out.append(_result(r, "FAIL", "mrp", "Readable MRP", f.get("value", ""), "MRP missing. Potential non-compliance — verify."))

    # MRP_FORMAT_VALID
    r = by_code["MRP_FORMAT_VALID"]
    f = _field(fields, "mrp")
    v = (f.get("value") or "")
    has_cur = bool(re.search(r"(₹|rs\.?|inr)", v, re.I))
    has_num = bool(re.search(r"\d", v))
    if not _is_ok(f):
        out.append(_result(r, "NOT_APPLICABLE", "mrp", "Currency + number", v, "Skipped — MRP not readable."))
    elif has_cur and has_num:
        out.append(_result(r, "PASS", "mrp", "Currency + number", v, "MRP format looks valid."))
    else:
        out.append(_result(r, "REVIEW", "mrp", "Currency + number", v, "MRP format ambiguous. Verify currency symbol and value."))

    # MANUFACTURER
    r = by_code["MANUFACTURER_DETAILS_PRESENT"]
    f = _field(fields, "manufacturer")
    if _is_ok(f):
        out.append(_result(r, "PASS", "manufacturer", "Name + address", f["value"], "Manufacturer/packer details found."))
    elif f.get("status") == "UNREADABLE":
        out.append(_result(r, "REVIEW", "manufacturer", "Name + address", f["value"], "Manufacturer details unreadable. Verify."))
    else:
        out.append(_result(r, "FAIL", "manufacturer", "Name + address", f.get("value", ""), "Manufacturer/packer details missing. Potential non-compliance."))

    # CONSUMER CARE
    r = by_code["CONSUMER_CARE_PRESENT"]
    f = _field(fields, "consumer_care")
    if _is_ok(f):
        out.append(_result(r, "PASS", "consumer_care", "Contact details", f["value"], "Consumer-care details found."))
    elif f.get("status") == "UNREADABLE":
        out.append(_result(r, "REVIEW", "consumer_care", "Contact details", f["value"], "Consumer-care unreadable. Verify."))
    else:
        out.append(_result(r, "FAIL", "consumer_care", "Contact details", f.get("value", ""), "Consumer-care details missing."))

    # DATE
    r = by_code["DATE_DECLARATION_PRESENT"]
    d1 = _field(fields, "mfg_date")
    d2 = _field(fields, "expiry_date")
    if _is_ok(d1) or _is_ok(d2):
        out.append(_result(r, "PASS", "mfg_date", "Date declaration", f"{d1.get('value','')} {d2.get('value','')}".strip(), "Date declaration found."))
    elif d1.get("status") == "UNREADABLE" or d2.get("status") == "UNREADABLE":
        out.append(_result(r, "REVIEW", "mfg_date", "Date declaration", f"{d1.get('value','')} {d2.get('value','')}".strip(), "Date declaration ambiguous. Verify."))
    else:
        out.append(_result(r, "REVIEW", "mfg_date", "Date declaration", "", "Date declaration not found. Applicability varies — manual check advised."))

    # BATCH
    r = by_code["BATCH_LOT_PRESENT"]
    f = _field(fields, "batch_lot")
    if _is_ok(f):
        out.append(_result(r, "PASS", "batch_lot", "Batch/lot", f["value"], "Batch/lot found."))
    else:
        out.append(_result(r, "REVIEW", "batch_lot", "Batch/lot", f.get("value", ""), "Batch/lot not confidently found. Low severity."))

    # COUNTRY OF ORIGIN
    r = by_code["COUNTRY_OF_ORIGIN_FOR_IMPORT"]
    imp = _field(fields, "importer")
    coo = _field(fields, "country_of_origin")
    if not _is_ok(imp):
        out.append(_result(r, "NOT_APPLICABLE", "country_of_origin", "Required if importer present", coo.get("value", ""), "No importer declared — rule not applicable."))
    elif _is_ok(coo):
        out.append(_result(r, "PASS", "country_of_origin", "Required if importer present", coo["value"], "Country of origin present for import."))
    else:
        out.append(_result(r, "FAIL", "country_of_origin", "Required if importer present", coo.get("value", ""), "Importer present but country of origin missing."))

    # COMMON / GENERIC NAME (name detection is heuristic → never auto-FAIL)
    r = by_code["COMMON_NAME_PRESENT"]
    f = _field(fields, "product_name")
    if _is_ok(f) and _confident(f, high):
        out.append(_result(r, "PASS", "product_name", "Readable commodity name", f["value"], "Common/generic name found."))
    elif _is_ok(f) or f.get("status") == "UNREADABLE":
        out.append(_result(r, "REVIEW", "product_name", "Readable commodity name", f.get("value", ""), "Commodity name uncertain — verify against the image."))
    else:
        out.append(_result(r, "REVIEW", "product_name", "Readable commodity name", "", "No commodity name detected — verify against the image."))

    # UNIT SALE PRICE (conditional applicability → never FAIL)
    r = by_code["UNIT_SALE_PRICE_PRESENT"]
    f = _field(fields, "unit_sale_price")
    if _is_ok(f):
        out.append(_result(r, "PASS", "unit_sale_price", "Present where applicable", f["value"], "Unit sale price found."))
    else:
        out.append(_result(r, "REVIEW", "unit_sale_price", "Present where applicable", f.get("value", ""), "Unit sale price not detected. Applicability is conditional (exemptions apply) — officer to confirm."))

    # Confidence gate: HIGH-confidence reads are auto-usable; anything below
    # the system threshold goes to human review even when text was found.
    for res in out:
        if res["status"] == "PASS":
            fld = _field(fields, res["field"])
            if _is_ok(fld) and not _confident(fld, high):
                res["status"] = "REVIEW"
                try:
                    pct = float(fld.get("confidence", 0.0))
                except (TypeError, ValueError):
                    pct = 0.0
                res["explanation"] += (f" OCR confidence {pct:.0%} is below the "
                                       f"{high:.0%} system threshold — verify against the image.")

    return out

def aggregate(results: List[dict]) -> str:
    """COMPLIANT | POTENTIAL_VIOLATION | REVIEW_REQUIRED"""
    applicable = [x for x in results if x["status"] != "NOT_APPLICABLE"]
    if any(x["status"] == "FAIL" and x["severity"] == "HIGH" for x in applicable):
        return "POTENTIAL_VIOLATION"
    if any(x["status"] == "FAIL" for x in applicable):
        return "POTENTIAL_VIOLATION"
    if any(x["status"] == "REVIEW" for x in applicable):
        return "REVIEW_REQUIRED"
    return "COMPLIANT"
