"""Structured extraction: raw OCR words → normalized fields with evidence.

Pure functions (no I/O) so they are unit-testable with synthetic OCR data.
Input line format: {"text": str, "words": [{"text": str, "conf": 0-100, "bbox": (x,y,w,h)}]}
Image dims (w, h) in pixels; bboxes are normalized to 0..1 with source_image_id.
"""
import re
from typing import List, Dict, Any, Optional
from app.services.normalize import (
    clean_text, normalize_quantity, normalize_mrp, normalize_date, normalize_phone_email,
)

HIGH_DEFAULT = 0.75
MED_DEFAULT = 0.45

def _mean_conf(words) -> float:
    cs = [max(0.0, min(100.0, float(w.get("conf", -1)))) for w in words if w.get("text", "").strip()]
    cs = [c for c in cs if c >= 0]
    return (sum(cs) / len(cs) / 100.0) if cs else 0.0

def _union(words, W, H, image_id) -> dict:
    boxes = [w["bbox"] for w in words if w.get("bbox")]
    if not boxes or not W or not H:
        return {"image_id": image_id}
    x0 = min(b[0] for b in boxes) / W
    y0 = min(b[1] for b in boxes) / H
    x1 = max(b[0] + b[2] for b in boxes) / W
    y1 = max(b[1] + b[3] for b in boxes) / H
    return {"x": round(x0, 4), "y": round(y0, 4), "w": round(x1 - x0, 4),
            "h": round(y1 - y0, 4), "image_id": image_id}

def _mk_field(value, conf, source, bbox, normalizer=None, high=HIGH_DEFAULT, med=MED_DEFAULT):
    norm = normalizer(value) if (value and normalizer) else {"raw": value, "normalized": value}
    if not (value or "").strip():
        return {"value": "", "normalized": "", "confidence": 0.0, "source": source,
                "status": "MISSING", "bbox": {"image_id": bbox.get("image_id")}}
    if conf < med:
        status = "UNREADABLE"
    else:
        status = "OK"
    return {"value": value, "normalized": norm.get("normalized", value), "confidence": round(conf, 3),
            "source": source, "status": status, "bbox": bbox}

def _find_lines(lines, pattern):
    rx = re.compile(pattern, re.I)
    return [(i, ln) for i, ln in enumerate(lines) if rx.search(ln.get("text", ""))]

FIELD_PATTERNS = {
    "mrp": r"m\s*\.?\s*r\s*\.?\s*p|retail\s+price|maximum\s+retail|mrp\s*rs",
    "net_quantity": r"net\s*(wt|weight|qty|quantity|content|vol)",
    "mfg_date": r"\bmfg\b|\bmfd\b|manufactured|date\s+of\s+(manufacture|mfg|pack)|packed?\s+on|\bpkd\b",
    "expiry_date": r"\bexp\b|expiry|best\s+before|use\s+by|\bbbd\b|expires?",
    "batch_lot": r"batch|lot\s*no|b\.?\s?no\.?",
    "consumer_care": r"care|toll|complaint|feedback|helpline|customercare|1800|1860",
    "manufacturer": r"manufactured\s+by|mfg\s+by|manufactured\s*:|packed\s+by|\bpacker\b|marketed\s+by|mktd",
    "importer": r"\bimporter\b|imported\s+by|imported\s+and\s+marketed",
    "country_of_origin": r"country\s+of\s+origin|made\s+in|product\s+of\s+\w+|origin\s*:",
    "unit_sale_price": r"unit\s+(sale\s+)?price",
}

QTY_FALLBACK = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|gm|grams?|ml|litre?s?|ltr?|L\b|mg|pcs?)\b", re.I)
CURR_FALLBACK = re.compile(r"(₹|rs\.?|inr)\s*\.?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)", re.I)
DATE_FALLBACK = re.compile(r"(\d{1,2}[/\-.]\d{2,4})|((jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})", re.I)
EMAIL_PHONE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|(?:1800|1860|\+?91[\-\s]?)?\d[\d\-\s]{7,14}\d")

def parse_ocr(lines: List[dict], image_id: str = "", W: int = 0, H: int = 0,
              source: str = "tesseract_ocr", high: float = HIGH_DEFAULT,
              med: float = MED_DEFAULT) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    norm_map = {"mrp": normalize_mrp, "net_quantity": normalize_quantity,
                "mfg_date": normalize_date, "expiry_date": normalize_date,
                "consumer_care": normalize_phone_email}

    def matched_value(key, line_idx, extra_idx=None):
        ln = lines[line_idx]
        txt = clean_text(ln.get("text", ""))
        if extra_idx is not None and 0 <= extra_idx < len(lines):
            txt = clean_text(txt + " " + lines[extra_idx].get("text", ""))
            words = list(ln.get("words", [])) + list(lines[extra_idx].get("words", []))
        else:
            words = list(ln.get("words", []))
        conf = _mean_conf(words)
        bbox = _union(words, W, H, image_id)
        return txt, conf, bbox

    for key, pat in FIELD_PATTERNS.items():
        hits = _find_lines(lines, pat)
        if key == "mfg_date" and hits:
            # "Mfg by <name>" manufacturer lines also match — require date-like content
            dated = [h for h in hits if DATE_FALLBACK.search(h[1].get("text", ""))]
            if dated:
                hits = dated
            else:
                i, _ = hits[0]
                txt, conf, bbox = matched_value(key, i)
                out[key] = _mk_field(txt, min(conf, med - 0.01), source, bbox,
                                     norm_map.get(key), high, med)
                continue
        if hits:
            i, _ = hits[0]
            nxt = i + 1 if (key in ("manufacturer", "importer") and i + 1 < len(lines)
                            and len(clean_text(lines[i + 1].get("text", ""))) > 3) else None
            txt, conf, bbox = matched_value(key, i, nxt)
            out[key] = _mk_field(txt, conf, source, bbox, norm_map.get(key), high, med)
        else:
            out[key] = _mk_field("", 0.0, source, {"image_id": image_id}, norm_map.get(key), high, med)

    # fallbacks: bare quantity / price / date / contact lines without keywords
    if out["net_quantity"]["status"] == "MISSING":
        for ln in lines:
            m = QTY_FALLBACK.search(ln.get("text", ""))
            if m:
                words = ln.get("words", [])
                out["net_quantity"] = _mk_field(clean_text(m.group(0)), _mean_conf(words),
                                               source, _union(words, W, H, image_id),
                                               normalize_quantity, high, med)
                break
    if out["mrp"]["status"] == "MISSING":
        for ln in lines:
            m = CURR_FALLBACK.search(ln.get("text", ""))
            if m:
                words = ln.get("words", [])
                out["mrp"] = _mk_field(clean_text(m.group(0)), _mean_conf(words),
                                       source, _union(words, W, H, image_id),
                                       normalize_mrp, high, med)
                break
    USP_FALLBACK = re.compile(
        r"(₹|rs\.?|inr)\s*\.?\s*\d+(?:,\d+)*(?:\.\d{1,2})?\s*(/|per)\s*(100\s?g|kg|g\b|litre|ml|pc|piece)", re.I)
    for ln in lines:
        m = USP_FALLBACK.search(ln.get("text", ""))
        if m and out["unit_sale_price"]["status"] == "MISSING":
            words = ln.get("words", [])
            out["unit_sale_price"] = _mk_field(
                clean_text(ln.get("text", "")), _mean_conf(words),
                source, _union(words, W, H, image_id), None, high, med)
            break
    if out["mfg_date"]["status"] == "MISSING" and out["expiry_date"]["status"] == "MISSING":
        for ln in lines:
            if DATE_FALLBACK.search(ln.get("text", "")) and not QTY_FALLBACK.search(ln.get("text", "")):
                words = ln.get("words", [])
                out["mfg_date"] = _mk_field(clean_text(ln["text"]), _mean_conf(words),
                                            source, _union(words, W, H, image_id),
                                            normalize_date, high, med)
                break
    if out["consumer_care"]["status"] == "MISSING":
        for ln in lines:
            if EMAIL_PHONE.search(ln.get("text", "")):
                words = ln.get("words", [])
                out["consumer_care"] = _mk_field(clean_text(ln["text"]), _mean_conf(words),
                                                 source, _union(words, W, H, image_id),
                                                 normalize_phone_email, high, med)
                break
    if out["batch_lot"]["status"] == "MISSING":
        for ln in lines:
            if re.search(r"\b[A-Z0-9]{4,12}\b", ln.get("text", "")) and DATE_FALLBACK.search(ln.get("text", "")):
                words = ln.get("words", [])
                out["batch_lot"] = _mk_field(clean_text(ln["text"]), _mean_conf(words),
                                             source, _union(words, W, H, image_id), None, high, med)
                break

    # product_name: first substantial non-keyword line (low-confidence heuristic)
    skip = re.compile("|".join(f"(?:{p})" for p in FIELD_PATTERNS.values()), re.I)
    pname, pconf, pbbox = "", 0.0, {"image_id": image_id}
    for ln in lines:
        t = clean_text(ln.get("text", ""))
        if len(t) >= 4 and not skip.search(t) and re.search(r"[A-Za-z]{3,}", t):
            pname, pconf, pbbox = t, max(0.5, _mean_conf(ln.get("words", []))), _union(ln.get("words", []), W, H, image_id)
            break
    out["product_name"] = _mk_field(pname, pconf, source, pbbox, None, high, med=0.0)
    if pname and pconf < med:
        out["product_name"]["status"] = "UNREADABLE"
    return out

def merge_fields(primary: Dict[str, dict], secondary: Dict[str, dict]) -> Dict[str, dict]:
    """Combine multi-image extraction: keep highest-confidence value per field,
    always preserving which image supplied it (bbox.image_id)."""
    merged = dict(primary)
    for key, cand in secondary.items():
        cur = merged.get(key)
        if cur is None or cand.get("confidence", 0) > cur.get("confidence", 0):
            if cand.get("value"):
                merged[key] = cand
    return merged

ALL_FIELDS = ("product_name", "net_quantity", "mrp", "manufacturer", "consumer_care",
              "mfg_date", "expiry_date", "batch_lot", "unit_sale_price",
              "importer", "country_of_origin")

def empty_fields(source: str = "") -> Dict[str, dict]:
    """MISSING skeleton so every known declaration is represented explicitly —
    never silently omitted."""
    return {k: {"value": "", "normalized": "", "confidence": 0.0, "source": source,
                "status": "MISSING", "bbox": {}} for k in ALL_FIELDS}
