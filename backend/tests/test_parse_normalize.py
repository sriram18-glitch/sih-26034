import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.normalize import (
    normalize_quantity, normalize_mrp, normalize_date, normalize_phone_email, clean_text)
from app.services.parse import parse_ocr, merge_fields

def W(text, conf=90, box=(10, 10, 100, 20)):
    return {"text": text, "conf": conf, "bbox": box}

def L(text, conf=90):
    words, x = [], 10
    for tok in text.split():
        words.append(W(tok, conf, (x, 10, len(tok) * 8, 20)))
        x += len(tok) * 8 + 8
    return {"text": text, "words": words}

def test_clean_text():
    assert clean_text("  MRP   ₹250\n") == "MRP ₹250"

def test_normalize_quantity():
    q = normalize_quantity("Net Wt. 5kg")
    assert q["number"] == 5 and q["unit"] == "kg" and q["normalized"] == "5 kg"
    q = normalize_quantity("500 g")
    assert q["normalized"] == "500 g"

def test_normalize_mrp():
    m = normalize_mrp("MRP Rs. 250.00 (incl. of all taxes)")
    assert m["currency"] == "₹" and m["amount"] == 250.0 and m["incl_all_taxes"] is True

def test_normalize_date():
    assert normalize_date("01/2026")["normalized"] == "01/2026"
    assert normalize_date("Jan 2025")["month"] == 1
    assert normalize_date("Best before 6 months")["relative"] is True

def test_normalize_contact():
    c = normalize_phone_email("care@abc.in, 1800-123-456")
    assert "care@abc.in" in c["emails"] and c["phones"]

def test_parse_mrp_line():
    fields = parse_ocr([L("MRP Rs 285 inclusive of all taxes", 92)], image_id="img1", W=1000, H=500)
    assert fields["mrp"]["status"] == "OK"
    assert "285" in fields["mrp"]["value"]
    assert fields["mrp"]["bbox"]["image_id"] == "img1"
    assert fields["mrp"]["normalized"]

def test_parse_missing_is_missing_not_invented():
    fields = parse_ocr([L("Hello world", 90)], image_id="img1", W=1000, H=500)
    assert fields["mrp"]["status"] == "MISSING" and fields["mrp"]["value"] == ""
    assert fields["net_quantity"]["status"] == "MISSING"

def test_parse_low_conf_is_unreadable():
    fields = parse_ocr([L("MRP Rs 285", 20)], image_id="img1", W=1000, H=500)
    assert fields["mrp"]["status"] == "UNREADABLE"

def test_parse_manufacturer_and_dates():
    lines = [L("Mfg by ABC Foods Pvt Ltd", 88), L("MIDC Mumbai 400093", 85),
             L("MFD 01/2026 B.No B1092", 87), L("care@abc.in 1800123456", 86)]
    fields = parse_ocr(lines, image_id="img2", W=1000, H=500)
    assert "ABC Foods" in fields["manufacturer"]["value"]
    assert fields["mfg_date"]["status"] == "OK"
    assert fields["consumer_care"]["status"] == "OK"

def test_parse_unit_price():
    fields = parse_ocr([L("Unit Sale Price Rs 57 per kg", 91)], image_id="i", W=500, H=500)
    assert fields["unit_sale_price"]["status"] == "OK"

def test_merge_keeps_best_with_source():
    a = {"mrp": {"value": "Rs 2O5", "confidence": 0.4, "status": "OK", "bbox": {"image_id": "img1"}}}
    b = {"mrp": {"value": "Rs 285", "confidence": 0.9, "status": "OK", "bbox": {"image_id": "img2"}}}
    m = merge_fields(a, b)
    assert m["mrp"]["value"] == "Rs 285"
    assert m["mrp"]["bbox"]["image_id"] == "img2"

def test_merge_does_not_invent():
    m = merge_fields({}, {"mrp": {"value": "", "confidence": 0.0, "status": "MISSING", "bbox": {}}})
    assert "mrp" not in m or m["mrp"]["status"] == "MISSING"
