from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
import io, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.main import app

c = TestClient(app)
img = Image.new("RGB", (1600, 1100), "white")
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 52)
except OSError:
    font = ImageFont.load_default()
lines = ["ABC Whole Wheat Atta", "Net Wt 5 kg", "MRP Rs 285 inclusive of all taxes",
         "Mfg by ABC Foods Pvt Ltd", "MIDC Mumbai 400093", "care@abcfoods.in 1800123456",
         "MFD 01/2026 Best before 6 months", "Batch B1092", "Unit Sale Price Rs 57 per kg"]
y = 60
for t in lines:
    d.text((60, y), t, fill="black", font=font)
    y += 105
buf = io.BytesIO()
img.save(buf, format="PNG")
buf.seek(0)

iid = c.post("/api/inspections",
             json={"product_name": "Smoke Atta", "is_demo": False, "demo_hint": ""}).json()["id"]
up = c.post(f"/api/inspections/{iid}/upload",
            files={"file": ("label.png", buf.read(), "image/png")}).json()
print("upload:", up)
r = c.post(f"/api/inspections/{iid}/analyze?provider=tesseract").json()
print("overall:", r["overall"], "| provider:", r["provider"],
      "| images:", r["images_processed"], "| detected:", r["fields_detected"],
      "| review:", r["fields_needing_review"])
for k, v in r["fields"].items():
    print("  ", k, "=", repr(v["value"][:45]), "[" + v["status"], str(v["confidence"]) + "]")
print("rules:", [(x["rule_code"], x["status"], x["rule_status"]) for x in r["results"]])
ex = c.get(f"/api/inspections/{iid}/extraction").json()
print("extraction endpoint fields:", len(ex["fields"]))
rl = c.get(f"/api/inspections/{iid}/rules").json()
print("rules endpoint versions:", rl["rule_version_used"])
rv = c.post(f"/api/inspections/{iid}/review",
            json={"actor": "officer@gov.in", "corrections": {}, "notes": "smoke review"}).json()
print("review:", rv)
rep = c.post(f"/api/inspections/{iid}/reports").json()
print("report:", rep)
aud = [a["event"] for a in c.get(f"/api/audit/{iid}").json()]
print("audit:", aud)
assert r["provider"] == "tesseract_ocr"
assert "OCR_STARTED" in aud and "OCR_COMPLETED" in aud and "RULE_VERSION_USED" in aud
print("SMOKE OK")
