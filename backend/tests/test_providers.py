import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services import vision
from app.services.vision import (
    DemoVisionProvider, TesseractVisionProvider, get_provider, tesseract_available)

def test_demo_provider_deterministic():
    p = DemoVisionProvider()
    a = p.extract("", "compliant sample")
    b = p.extract("", "compliant sample")
    assert a["fields"]["mrp"]["value"] == b["fields"]["mrp"]["value"]
    assert a["provider"] == "demo_ocr"

def test_demo_violation_missing_not_invented():
    p = DemoVisionProvider()
    res = p.extract("", "violation")
    assert res["fields"]["net_quantity"]["status"] == "MISSING"
    assert res["fields"]["net_quantity"]["value"] == ""

def test_get_provider_routing(monkeypatch):
    monkeypatch.setenv("VISION_PROVIDER", "demo")
    assert isinstance(get_provider(""), DemoVisionProvider)
    assert isinstance(get_provider("tesseract"), TesseractVisionProvider)

def test_tesseract_missing_image_fails_openly():
    p = TesseractVisionProvider()
    try:
        p.extract("/nonexistent/path.jpg")
        assert False, "should have raised"
    except RuntimeError as e:
        assert "No image" in str(e)

def test_tesseract_available_probe_shape():
    info = tesseract_available()
    assert "available" in info and "cmd" in info
    # binary was installed on this machine; if present it must report a version
    if info["available"]:
        assert info["version"].startswith("tesseract") or info["version"][0].isdigit()

def test_describe_providers_no_secrets():
    d = vision.describe_providers()
    assert d["demo"]["available"] is True
    assert "thresholds" in d
    blob = str(d)
    assert "API_KEY" not in blob and "SERVICE_ROLE" not in blob
