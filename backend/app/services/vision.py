"""Vision/OCR provider abstraction. Never hard-code to a single vendor.

Providers: demo | tesseract  (select via VISION_PROVIDER env or ?provider=).
Keys/secrets stay server-side (env vars). Frontend never sees them.
"""
from abc import ABC, abstractmethod
from typing import Dict, List
import os
import shutil

from app.services.parse import HIGH_DEFAULT, MED_DEFAULT

def _high() -> float:
    try:
        return float(os.getenv("OCR_HIGH_CONF", str(HIGH_DEFAULT)))
    except ValueError:
        return HIGH_DEFAULT

def _med() -> float:
    try:
        return float(os.getenv("OCR_MED_CONF", str(MED_DEFAULT)))
    except ValueError:
        return MED_DEFAULT

class VisionProvider(ABC):
    name: str = "base"
    @abstractmethod
    def extract(self, image_path: str, hint: str = "") -> Dict:
        """Return {fields: {name: {value, normalized, confidence, source, status, bbox}},
        raw_text, provider}"""
        raise NotImplementedError

def _mk(value, confidence, source, bbox=None, status="OK"):
    return {"value": value, "confidence": confidence, "source": source,
            "status": status if value else "MISSING", "bbox": bbox or {}}

class DemoVisionProvider(VisionProvider):
    """Deterministic demo extraction — clearly labelled, no fake AI claims."""
    name = "demo_ocr"
    def extract(self, image_path: str, hint: str = "") -> Dict:
        h = (hint or "").lower()
        if "violat" in h:
            fields = {
                "product_name": _mk("ABC Masala Powder", 0.9, self.name, {"x": .2, "y": .1, "w": .6, "h": .12}),
                "net_quantity": _mk("", 0.0, self.name, {}, "MISSING"),
                "mrp": _mk("120", 0.55, self.name, {"x": .6, "y": .7, "w": .3, "h": .1}),
                "manufacturer": _mk("", 0.0, self.name, {}, "MISSING"),
                "consumer_care": _mk("", 0.0, self.name, {}, "MISSING"),
                "mfg_date": _mk("", 0.0, self.name, {}, "MISSING"),
                "expiry_date": _mk("", 0.0, self.name, {}, "MISSING"),
                "batch_lot": _mk("B234", 0.7, self.name, {"x": .1, "y": .8, "w": .3, "h": .08}),
                "importer": _mk("", 0.0, self.name, {}, "MISSING"),
                "country_of_origin": _mk("", 0.0, self.name, {}, "MISSING"),
            }
            return {"fields": fields, "raw_text": "DEMO extraction (violation sample)", "provider": self.name}
        if "review" in h:
            fields = {
                "product_name": _mk("ABC Masala Powder", 0.85, self.name, {"x": .2, "y": .1, "w": .6, "h": .12}),
                "net_quantity": _mk("500 g?", 0.42, self.name, {"x": .2, "y": .5, "w": .3, "h": .1}, "UNREADABLE"),
                "mrp": _mk("Rs 120?", 0.48, self.name, {"x": .6, "y": .7, "w": .3, "h": .1}, "UNREADABLE"),
                "manufacturer": _mk("ABC Foods, Mumbai", 0.6, self.name, {"x": .1, "y": .6, "w": .5, "h": .12}),
                "consumer_care": _mk("", 0.0, self.name, {}, "MISSING"),
                "mfg_date": _mk("", 0.0, self.name, {}, "MISSING"),
                "expiry_date": _mk("", 0.0, self.name, {}, "MISSING"),
                "batch_lot": _mk("", 0.0, self.name, {}, "MISSING"),
                "importer": _mk("", 0.0, self.name, {}, "MISSING"),
                "country_of_origin": _mk("", 0.0, self.name, {}, "MISSING"),
            }
            return {"fields": fields, "raw_text": "DEMO extraction (review sample)", "provider": self.name}
        # compliant default
        fields = {
            "product_name": _mk("ABC Whole Wheat Atta", 0.97, self.name, {"x": .2, "y": .08, "w": .6, "h": .12}),
            "net_quantity": _mk("5 kg", 0.96, self.name, {"x": .25, "y": .5, "w": .3, "h": .1}),
            "mrp": _mk("₹285 (incl. of all taxes)", 0.95, self.name, {"x": .6, "y": .68, "w": .32, "h": .12}),
            "manufacturer": _mk("ABC Foods Pvt Ltd, MIDC Mumbai 400093", 0.93, self.name, {"x": .08, "y": .6, "w": .5, "h": .14}),
            "consumer_care": _mk("care@abcfoods.in, 1800-123-456", 0.9, self.name, {"x": .08, "y": .76, "w": .5, "h": .1}),
            "mfg_date": _mk("01/2026", 0.88, self.name, {"x": .1, "y": .86, "w": .25, "h": .08}),
            "expiry_date": _mk("Best before 6 months", 0.87, self.name, {"x": .4, "y": .86, "w": .4, "h": .08}),
            "unit_sale_price": _mk("₹57.00 per kg", 0.9, self.name, {"x": .6, "y": .78, "w": .3, "h": .08}),
            "batch_lot": _mk("B1092", 0.9, self.name, {"x": .1, "y": .8, "w": .3, "h": .08}),
            "importer": _mk("", 0.0, self.name, {}, "MISSING"),
            "country_of_origin": _mk("", 0.0, self.name, {}, "MISSING"),
        }
        return {"fields": fields, "raw_text": "DEMO extraction (compliant sample)", "provider": self.name}

def _tesseract_cmd() -> str:
    explicit = os.getenv("TESSERACT_CMD", "").strip()
    if explicit:
        return explicit
    found = shutil.which("tesseract")
    if found:
        return found
    for cand in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                 r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                 "/usr/bin/tesseract", "/usr/local/bin/tesseract"):
        if os.path.exists(cand):
            return cand
    return "tesseract"

def tesseract_available() -> dict:
    """Probe the OCR binary. Returns {available, version|error, cmd}."""
    cmd = _tesseract_cmd()
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = cmd
        ver = str(pytesseract.get_tesseract_version())
        return {"available": True, "version": ver, "cmd": cmd}
    except Exception as e:
        return {"available": False, "error": str(e), "cmd": cmd}

def _tsv_to_lines(tsv: dict, W: int, H: int) -> List[dict]:
    """pytesseract image_to_data dict → line structures with word boxes/conf."""
    n = len(tsv.get("text", []))
    lines: Dict[tuple, dict] = {}
    for i in range(n):
        try:
            conf = float(tsv["conf"][i])
        except (ValueError, TypeError):
            conf = -1.0
        word = (tsv["text"][i] or "").strip()
        if not word:
            continue
        key = (tsv["page_num"][i], tsv["block_num"][i], tsv["par_num"][i], tsv["line_num"][i])
        entry = lines.setdefault(key, {"words": []})
        try:
            entry["words"].append({"text": word, "conf": conf,
                "bbox": (int(tsv["left"][i]), int(tsv["top"][i]),
                         int(tsv["width"][i]), int(tsv["height"][i]))})
        except (ValueError, TypeError):
            entry["words"].append({"text": word, "conf": conf})
    out = []
    for key in sorted(lines):
        words = lines[key]
        out.append({"text": " ".join(w["text"] for w in words["words"]), "words": words["words"]})
    return [ln for ln in out if ln["text"].strip()]

class TesseractVisionProvider(VisionProvider):
    """Real OCR: preprocess → Tesseract TSV → structured parsing.

    Fails OPENLY (raises) when the binary is missing or the image is
    unreadable — callers must surface this, never substitute demo output.
    """
    name = "tesseract_ocr"
    def extract(self, image_path: str, hint: str = "") -> Dict:
        if not image_path or not os.path.exists(image_path):
            raise RuntimeError("No image available for OCR.")
        from app.services.preprocess import preprocess
        from app.services.parse import parse_ocr
        prep = preprocess(image_path)
        psm = os.getenv("OCR_PSM", "6").strip() or "6"
        try:
            import pytesseract
            from PIL import Image
            pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd()
            img = Image.open(prep["processed"])
            tsv = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=f"--psm {psm}")
            lines = _tsv_to_lines(tsv, prep["width"], prep["height"])
            psm_used = psm
            if not lines and psm != "3":
                # honest retry with fully automatic segmentation before giving up
                tsv = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config="--psm 3")
                lines = _tsv_to_lines(tsv, prep["width"], prep["height"])
                psm_used = "3"
        except Exception as e:
            raise RuntimeError(
                "Live OCR engine unavailable. Install Tesseract-OCR and set TESSERACT_CMD "
                f"if needed. Detail: {e}")
        if not lines:
            raise RuntimeError("OCR produced no readable text. Upload a clearer, well-lit image.")
        fields = parse_ocr(lines, image_id=os.path.basename(image_path),
                           W=prep["width"], H=prep["height"],
                           source=self.name, high=_high(), med=_med())
        raw = "\n".join(ln["text"] for ln in lines)[:4000]
        return {"fields": fields, "raw_text": raw, "provider": self.name,
                "processed_image": prep["processed"], "lines": len(lines),
                "psm": psm_used}

def get_provider(name: str = "") -> VisionProvider:
    name = (name or os.getenv("VISION_PROVIDER", "demo")).lower()
    if name.startswith("tesseract"):
        return TesseractVisionProvider()
    return DemoVisionProvider()

def describe_providers() -> dict:
    t = tesseract_available()
    return {
        "demo": {"available": True, "label": "Demo / Simulated OCR"},
        "tesseract": {"available": t["available"], "label": "Live OCR (Tesseract)",
                      "version": t.get("version", ""), "error": t.get("error", "")},
        "thresholds": {"high_confidence": _high(), "medium_confidence": _med(),
                       "note": "System OCR confidence thresholds (configurable, not legal thresholds)."},
    }
