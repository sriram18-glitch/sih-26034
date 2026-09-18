"""Cross-image / cross-field intelligence. Pure deterministic functions.

Compares normalized values of the SAME declaration across captured views and
reports factual inconsistencies — never legal conclusions, never risk scores.
"""
import re
from typing import Dict, List

# Fields compared across views + their attention weight when conflicting.
COMPARABLE = {
    "net_quantity": "HIGH",
    "mrp": "HIGH",
    "mfg_date": "WARNING",
    "expiry_date": "WARNING",
    "manufacturer": "WARNING",
    "importer": "WARNING",
    "product_name": "WARNING",
    "batch_lot": "INFO",
}

# Declaration coverage tracked per inspection (applicability decided by rules).
COVERAGE_FIELDS = (
    "product_name", "manufacturer", "net_quantity", "mrp",
    "mfg_date", "expiry_date", "consumer_care", "unit_sale_price",
    "batch_lot", "importer", "country_of_origin",
)

def _norm_key(field: str, f: dict) -> str:
    """Canonical comparison key: normalized value, cleaned + casefolded."""
    raw = (f.get("normalized") or f.get("value") or "")
    key = re.sub(r"\s+", " ", str(raw)).strip().casefold()
    # ignore tax disclaimers / whitespace-only differences for MRP
    key = re.sub(r"\(.*tax.*\)", "", key).strip()
    return key

def detect_conflicts(per_image: Dict[str, Dict[str, dict]]) -> List[dict]:
    """per_image: {image_id: {field: field_dict}}. Returns finding dicts."""
    findings = []
    # {field: {normkey: [(image_id, field_dict)]}}
    seen: Dict[str, Dict[str, list]] = {}
    for img_id, fields in (per_image or {}).items():
        for fname, f in (fields or {}).items():
            if fname not in COMPARABLE:
                continue
            if not (f.get("value") or "").strip():
                continue
            if f.get("status") not in ("OK",):
                continue  # only compare confident reads, never guesses
            seen.setdefault(fname, {}).setdefault(_norm_key(fname, f), []).append((img_id, f))
    for fname, variants in seen.items():
        keys = [k for k in variants if k]
        if len(keys) > 1:
            vals = []
            for k in keys:
                img_id, f = variants[k][0]
                vals.append({"value": f.get("value", ""), "normalized": f.get("normalized", ""),
                             "confidence": f.get("confidence", 0), "image_id": img_id,
                             "bbox": f.get("bbox", {})})
            findings.append({
                "kind": "CONFLICT",
                "field": fname,
                "level": "HIGH" if COMPARABLE[fname] == "HIGH" else "MEDIUM",
                "title": f"Conflicting {fname.replace('_', ' ')} across views",
                "detail": (f"{fname.replace('_', ' ')} declarations differ across captured views. "
                           "Officer verification required — values and source images preserved below."),
                "values": vals,
                "evidence": [{"image_id": v["image_id"], "bbox": v["bbox"],
                              "value": v["value"]} for v in vals],
            })
    return findings

def coverage(merged: Dict[str, dict]) -> List[dict]:
    """Per-declaration coverage from merged extraction."""
    out = []
    for fname in COVERAGE_FIELDS:
        f = (merged or {}).get(fname, {})
        val = (f.get("value") or "").strip()
        status = f.get("status", "MISSING")
        try:
            conf = float(f.get("confidence", 0))
        except (TypeError, ValueError):
            conf = 0.0
        if not val:
            state = "MISSING"
        elif status == "UNREADABLE" or conf < 0.45:
            state = "UNREADABLE"
        elif conf < 0.75:
            state = "LOW_CONFIDENCE"
        else:
            state = "FOUND"
        out.append({"field": fname, "state": state, "value": val,
                    "confidence": conf, "source_image_id": f.get("source_image_id", "") or (f.get("bbox") or {}).get("image_id", "")})
    return out

def attention(findings: List[dict], rule_results: List[dict], cov: List[dict]) -> dict:
    """Factual review prioritization. Levels: HIGH / MEDIUM / LOW.
    No probabilities, no 'risk scores' — every item cites its reason."""
    high, medium = [], []
    for f in findings or []:
        (high if f.get("level") == "HIGH" else medium).append(
            f"Conflicting {f.get('field')} across views" if f.get("kind") == "CONFLICT"
            else f.get("title", "finding"))
    for r in rule_results or []:
        if r.get("status") == "FAIL" and r.get("severity") == "HIGH":
            high.append(f"Rule check failed: {r.get('rule_code')}")
        elif r.get("status") in ("FAIL", "REVIEW"):
            medium.append(f"Rule check needs review: {r.get('rule_code')} ({r.get('status')})")
    unread = [c["field"] for c in cov or [] if c["state"] in ("UNREADABLE", "LOW_CONFIDENCE")]
    missing = [c["field"] for c in cov or [] if c["state"] == "MISSING"]
    if unread:
        medium.append(f"Incomplete/unreadable information: {', '.join(unread)}")
    if missing:
        medium.append(f"Declarations not detected: {', '.join(missing)}")
    level = "HIGH" if high else ("MEDIUM" if medium else "LOW")
    return {"level": level, "high": high, "medium": medium,
            "summary": (f"{len(high)} high-attention, {len(medium)} review items"
                        if (high or medium) else "No detected issues")}
