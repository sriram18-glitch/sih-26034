import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.rules.engine import evaluate_all, aggregate

def F(value, status="OK", conf=0.9):
    return {"value": value, "status": status if value else "MISSING", "confidence": conf}

def full():
    return {"product_name": F("Atta"), "net_quantity": F("5 kg"), "mrp": F("₹285"),
            "manufacturer": F("ABC Foods"), "consumer_care": F("care@x"), "mfg_date": F("01/2026"),
            "expiry_date": F("6 months"), "batch_lot": F("B1"),
            "unit_sale_price": F("₹57 per kg"),
            "importer": F("", "MISSING"), "country_of_origin": F("", "MISSING")}

def test_valid_mrp_pass():
    res = {r["rule_code"]: r for r in evaluate_all(full())}
    assert res["MRP_PRESENT"]["status"] == "PASS"
    assert res["NET_QUANTITY_PRESENT"]["status"] == "PASS"

def test_missing_mrp_fail():
    f = full(); f["mrp"] = F("", "MISSING")
    res = {r["rule_code"]: r for r in evaluate_all(f)}
    assert res["MRP_PRESENT"]["status"] == "FAIL"
    assert aggregate(list(res.values())) == "POTENTIAL_VIOLATION"

def test_unreadable_mrp_review():
    f = full(); f["mrp"] = {"value": "???", "status": "UNREADABLE", "confidence": 0.3}
    res = {r["rule_code"]: r for r in evaluate_all(f)}
    assert res["MRP_PRESENT"]["status"] == "REVIEW"

def test_import_requires_origin():
    f = full(); f["importer"] = F("XYZ Imports")
    res = {r["rule_code"]: r for r in evaluate_all(f)}
    assert res["COUNTRY_OF_ORIGIN_FOR_IMPORT"]["status"] == "FAIL"

def test_compliant_aggregate():
    assert aggregate(evaluate_all(full())) == "COMPLIANT"

# ---- Phase 2: verified rules, versions, confidence gate ----

def test_verified_rules_carry_sources():
    res = evaluate_all(full())
    by = {r["rule_code"]: r for r in res}
    assert by["NET_QUANTITY_PRESENT"]["rule_status"] == "VERIFIED"
    assert by["MRP_PRESENT"]["rule_status"] == "VERIFIED"
    assert "consumeraffairs.gov.in" in by["MRP_PRESENT"]["source_url"]
    assert by["NET_QUANTITY_PRESENT"]["rule_version"] == "2.0.0"

def test_unverified_rules_flagged():
    res = {r["rule_code"]: r for r in evaluate_all(full())}
    assert res["UNIT_SALE_PRICE_PRESENT"]["rule_status"] == "UNVERIFIED"
    assert res["BATCH_LOT_PRESENT"]["rule_status"] == "UNVERIFIED"

def test_unit_price_never_fails():
    f = full(); f["unit_sale_price"] = F("", "MISSING")
    res = {r["rule_code"]: r for r in evaluate_all(f)}
    assert res["UNIT_SALE_PRICE_PRESENT"]["status"] == "REVIEW"

def test_common_name_never_auto_fails():
    f = full(); f["product_name"] = F("", "MISSING")
    res = {r["rule_code"]: r for r in evaluate_all(f)}
    assert res["COMMON_NAME_PRESENT"]["status"] == "REVIEW"

def test_low_confidence_downgrades_to_review():
    f = full(); f["mrp"] = F("₹285", "OK", conf=0.5)
    res = {r["rule_code"]: r for r in evaluate_all(f)}
    assert res["MRP_PRESENT"]["status"] == "REVIEW"
    assert "confidence" in res["MRP_PRESENT"]["explanation"]

def test_new_rules_present_in_output():
    codes = {r["rule_code"] for r in evaluate_all(full())}
    assert {"COMMON_NAME_PRESENT", "UNIT_SALE_PRICE_PRESENT"} <= codes
