"""Live/Demo isolation + versioning + evidence-serving guarantees."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)

def _mk(product, is_demo, hint=""):
    return c.post("/api/inspections",
                  json={"product_name": product, "is_demo": is_demo,
                        "demo_hint": hint}).json()["id"]

def test_list_isolation():
    live = _mk("LiveIso", False)
    demo = _mk("DemoIso", True, "compliant")
    c.post(f"/api/inspections/{demo}/analyze")
    ids_live = {r["id"] for r in c.get("/api/inspections?demo=false").json()}
    ids_demo = {r["id"] for r in c.get("/api/inspections?demo=true").json()}
    assert live in ids_live and demo not in ids_live
    assert demo in ids_demo and live not in ids_demo

def test_stats_isolation():
    s_live = c.get("/api/dashboard/stats?demo=false").json()
    s_demo = c.get("/api/dashboard/stats?demo=true").json()
    assert s_live["total"] >= 1 and s_demo["total"] >= 1
    assert s_live["total"] + s_demo["total"] >= s_live["total"]

def test_audit_isolation():
    a_live = c.get("/api/audit?demo=false").json()
    a_demo = c.get("/api/audit?demo=true").json()
    live_ids = {r["id"] for r in c.get("/api/inspections?demo=false").json()}
    demo_ids = {r["id"] for r in c.get("/api/inspections?demo=true").json()}
    assert all(a["inspection_id"] in live_ids for a in a_live)
    assert all(a["inspection_id"] in demo_ids for a in a_demo)
    assert not (set(a["inspection_id"] for a in a_live) & set(a["inspection_id"] for a in a_demo))

def test_live_never_silent_demo(monkeypatch):
    monkeypatch.setenv("VISION_PROVIDER", "demo")
    iid = _mk("LiveNoFallback", False)
    import io
    from PIL import Image
    img = Image.new("RGB", (200, 200), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    c.post(f"/api/inspections/{iid}/upload",
           files={"file": ("x.png", buf.read(), "image/png")})
    r = c.post(f"/api/inspections/{iid}/analyze")
    assert r.status_code == 503
    assert "Live OCR" in r.text

def _upload_blank(iid):
    import io
    from PIL import Image
    img = Image.new("RGB", (200, 200), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    r = c.post(f"/api/inspections/{iid}/upload",
               files={"file": ("x.png", buf.read(), "image/png")})
    assert r.status_code == 200

def test_rule_versions_recorded():
    iid = _mk("VerCheck", True, "compliant")
    _upload_blank(iid)
    res = c.post(f"/api/inspections/{iid}/analyze").json()
    assert res["results"], "expected rule results"
    assert all(r["rule_version"] for r in res["results"])
    got = c.get(f"/api/inspections/{iid}").json()
    assert got["rule_version_used"]
    assert all(r.get("rule_status") in ("VERIFIED", "UNVERIFIED") for r in got["results"])

def test_image_endpoint_guards():
    assert c.get("/api/images/does-not-exist").status_code == 404
    iid = _mk("ImgCheck", True, "compliant")
    import io
    from PIL import Image
    img = Image.new("RGB", (200, 200), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    c.post(f"/api/inspections/{iid}/upload",
           files={"file": ("x.png", buf.read(), "image/png")})
    got = c.get(f"/api/inspections/{iid}").json()
    assert got["images"] and got["images"][0]["id"]
    img_res = c.get(f"/api/images/{got['images'][0]['id']}")
    assert img_res.status_code == 200
    assert img_res.headers["content-type"].startswith("image/")
