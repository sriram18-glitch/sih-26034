"""Final hardening E2E: full LIVE workflow (real Tesseract OCR) + DEMO workflow,
asserting strict isolation between modes."""
import io, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
from app.main import app

c = TestClient(app)
try:
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 52)
except OSError:
    font = ImageFont.load_default()

def label_image(lines):
    img = Image.new("RGB", (1600, 1100), "white")
    d = ImageDraw.Draw(img)
    y = 60
    for t in lines:
        d.text((60, y), t, fill="black", font=font)
        y += 105
    b = io.BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b.read()

# ---------- LIVE ----------
live_lines = ["ABC Whole Wheat Atta", "Net Wt 5 kg", "MRP Rs 285 inclusive of all taxes",
              "Mfg by ABC Foods Pvt Ltd", "MIDC Mumbai 400093", "care@abcfoods.in 1800123456",
              "MFD 01/2026 Best before 6 months", "Batch B1092", "Unit Sale Price Rs 57 per kg"]
live = c.post("/api/inspections",
              json={"product_name": "Live Atta", "is_demo": False, "demo_hint": ""}).json()["id"]
c.post(f"/api/inspections/{live}/upload",
       files={"file": ("label.png", label_image(live_lines), "image/png")})
lr = c.post(f"/api/inspections/{live}/analyze?provider=tesseract").json()
assert lr["provider"] == "tesseract_ocr", lr
assert lr["overall"] in ("COMPLIANT", "REVIEW_REQUIRED", "POTENTIAL_VIOLATION")
lg = c.get(f"/api/inspections/{live}").json()
assert lg["images"] and lg["images"][0]["id"]
assert c.get(f"/api/images/{lg['images'][0]['id']}").status_code == 200
c.post(f"/api/inspections/{live}/review",
       json={"actor": "officer@gov.in", "corrections": {"mrp": "MRP Rs 285"},
             "notes": "verified against label"})
c.post(f"/api/inspections/{live}/reports")
print("LIVE:", lr["overall"], "| detected:", lr["fields_detected"], "| provider:", lr["provider"])

# ---------- DEMO ----------
demo = c.post("/api/inspections",
              json={"product_name": "Demo Atta", "is_demo": True,
                    "demo_hint": "compliant"}).json()["id"]
c.post(f"/api/inspections/{demo}/upload",
       files={"file": ("any.png", label_image(["x"]), "image/png")})
dr = c.post(f"/api/inspections/{demo}/analyze").json()
assert dr["provider"] == "demo_ocr", dr
print("DEMO:", dr["overall"], "| provider:", dr["provider"])

# ---------- ISOLATION ----------
live_ids = {r["id"] for r in c.get("/api/inspections?demo=false").json()}
demo_ids = {r["id"] for r in c.get("/api/inspections?demo=true").json()}
assert live in live_ids and live not in demo_ids
assert demo in demo_ids and demo not in live_ids
sl, sd = c.get("/api/dashboard/stats?demo=false").json(), c.get("/api/dashboard/stats?demo=true").json()
assert sl["total"] >= 1 and sd["total"] >= 1
al = {a["inspection_id"] for a in c.get("/api/audit?demo=false").json()}
ad = {a["inspection_id"] for a in c.get("/api/audit?demo=true").json()}
assert live in al and demo not in al and demo in ad and live not in ad
# reports only for inspections that generated them
assert c.get(f"/api/inspections/{live}/report.pdf").status_code == 200
print("ISOLATION OK — live total:", sl["total"], "| demo total:", sd["total"])
print("FINAL E2E OK")
