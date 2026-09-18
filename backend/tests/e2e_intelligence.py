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

def label(lines):
    img = Image.new("RGB", (1600, 1000), "white")
    d = ImageDraw.Draw(img)
    y = 60
    for t in lines:
        d.text((60, y), t, fill="black", font=font)
        y += 110
    b = io.BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b.read()

# Inspection 1: front says 1 kg / Rs 100, back says 500 g / Rs 120 -> conflicts
i1 = c.post("/api/inspections", json={"product_name": "Conflict Pack", "is_demo": False, "demo_hint": ""}).json()["id"]
front = ["Fresh Milk", "Net 1 kg", "MRP Rs 100 inclusive of all taxes", "Mfg by Dairy Co"]
back = ["Fresh Milk", "Net Qty 500 g", "MRP Rs 120 inclusive of all taxes", "Mfg by Dairy Co", "care@dairy.in 1800123456", "MFD 02/2026"]
c.post(f"/api/inspections/{i1}/upload", files={"file": ("front.png", front and label(front), "image/png")})
c.post(f"/api/inspections/{i1}/upload", files={"file": ("back.png", back and label(back), "image/png")})
r = c.post(f"/api/inspections/{i1}/analyze?provider=tesseract").json()
print("overall:", r["overall"], "| findings:", [(f["field"], f["level"]) for f in r["findings"]])
print("attention:", r["attention"]["level"], "-", r["attention"]["summary"])
assert any(f["field"] == "net_quantity" and f["level"] == "HIGH" for f in r["findings"]), "expected HIGH net-qty conflict"
assert any(f["field"] == "mrp" for f in r["findings"]), "expected MRP conflict"
assert r["attention"]["level"] == "HIGH"

# Inspection 2: clean pack -> compare while i1 conflicts are still OPEN
i2 = c.post("/api/inspections", json={"product_name": "Clean Pack", "is_demo": False, "demo_hint": ""}).json()["id"]
c.post(f"/api/inspections/{i2}/upload", files={"file": ("one.png", label(["Fresh Milk", "Net 1 kg", "MRP Rs 100"]), "image/png")})
c.post(f"/api/inspections/{i2}/analyze?provider=tesseract")
cmp = c.get(f"/api/inspections/compare?ids={i1},{i2}").json()
diffs = [x["field"] for x in cmp["rows"] if x["differs"]]
print("compare differs:", diffs)
assert "mrp" in diffs and "net_quantity" in diffs

# findings endpoint + resolve
fl = c.get(f"/api/inspections/{i1}/findings").json()
assert len(fl) >= 2
fid = [f["id"] for f in fl if f["field"] == "mrp"][0]
rv = c.post(f"/api/inspections/{i1}/findings/{fid}/resolve",
            json={"actor": "officer@gov.in", "decision": "VERIFIED", "reason": "checked both panels"}).json()
assert rv["status"] == "VERIFIED"
fl2 = c.get(f"/api/inspections/{i1}/findings").json()
assert [f for f in fl2 if f["id"] == fid][0]["status"] == "VERIFIED"
print("resolve OK")

# attention queue shows it
att = c.get("/api/dashboard/attention?demo=false").json()
assert any(q["id"] == i1 for q in att["queue"]), att["counts"]
print("attention queue OK:", att["counts"])

# review with finding resolution + report
c.post(f"/api/inspections/{i1}/review",
       json={"actor": "officer@gov.in", "corrections": {}, "notes": "conflict confirmed on label",
             "resolve_findings": [f["id"] for f in fl2 if f["status"] == "OPEN"],
             "finding_decision": "VERIFIED"})
rep = c.post(f"/api/inspections/{i1}/reports").json()
assert rep["pdf"]
aud = [a["event"] for a in c.get(f"/api/audit/{i1}").json()]
for ev in ["CONSISTENCY_EVALUATED", "FINDING_RESOLVED", "REPORT_GENERATED"]:
    assert ev in aud, ev
print("INTELLIGENCE E2E OK")
