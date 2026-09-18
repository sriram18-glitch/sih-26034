import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.consistency import detect_conflicts, coverage, attention

def F(value, normalized=None, conf=0.9, status="OK", img="img1"):
    return {"value": value, "normalized": normalized if normalized is not None else value,
            "confidence": conf, "status": status,
            "bbox": {"image_id": img}, "source_image_id": img}

def test_conflicting_net_quantity():
    per = {"a": {"net_quantity": F("1 kg", "1 kg")},
           "b": {"net_quantity": F("500 g", "500 g")}}
    out = detect_conflicts(per)
    assert len(out) == 1
    assert out[0]["kind"] == "CONFLICT" and out[0]["level"] == "HIGH"
    assert {v["image_id"] for v in out[0]["values"]} == {"a", "b"}

def test_same_value_different_format_no_conflict():
    per = {"a": {"net_quantity": F("5kg", "5 kg")},
           "b": {"net_quantity": F("5 kg", "5 kg")}}
    assert detect_conflicts(per) == []

def test_unreadable_never_conflicts():
    per = {"a": {"mrp": F("Rs 285", "Rs 285")},
           "b": {"mrp": F("Rs 2B5", "Rs 2B5", conf=0.3, status="UNREADABLE")}}
    assert detect_conflicts(per) == []

def test_missing_never_conflicts():
    per = {"a": {"mrp": F("Rs 285", "Rs 285")}, "b": {}}
    assert detect_conflicts(per) == []

def test_single_image_no_conflict():
    assert detect_conflicts({"a": {"mrp": F("Rs 1", "Rs 1")}}) == []

def test_conflicting_mrp_high():
    per = {"a": {"mrp": F("MRP Rs 100", "Rs100")},
           "b": {"mrp": F("MRP Rs 120", "Rs120")}}
    out = detect_conflicts(per)
    assert len(out) == 1 and out[0]["level"] == "HIGH"

def test_coverage_states():
    merged = {"mrp": F("Rs 5", "Rs 5", conf=0.95),
              "net_quantity": F("5g?", "5g?", conf=0.5),
              "mfg_date": F("", "", conf=0.0, status="MISSING")}
    cov = {c["field"]: c["state"] for c in coverage(merged)}
    assert cov["mrp"] == "FOUND"
    assert cov["net_quantity"] == "LOW_CONFIDENCE"
    assert cov["mfg_date"] == "MISSING"

def test_attention_levels_no_scores():
    a = attention([], [], coverage({"mrp": F("x", "x")}))
    assert a["level"] in ("LOW", "MEDIUM")
    assert "risk" not in str(a).lower() and "probab" not in str(a).lower()
    a2 = attention([{"kind": "CONFLICT", "field": "mrp", "level": "HIGH", "title": "t"}],
                   [{"rule_code": "X", "status": "FAIL", "severity": "HIGH"}], [])
    assert a2["level"] == "HIGH"
    assert len(a2["high"]) == 2
