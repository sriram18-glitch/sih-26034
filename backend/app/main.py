"""SIH26034 FastAPI backend — OCR extraction → deterministic rules → evidence → report."""
import os, uuid, shutil
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from PIL import Image

from app.core.config import settings
from app.db.database import Base, engine, get_db
from app.models import models
from app.schemas.schemas import InspectionCreate, ReviewRequest
from app.services.vision import get_provider
from app.rules.registry import RULES
from app.rules.engine import evaluate_all, aggregate

Base.metadata.create_all(bind=engine)

# Seed / upsert versioned rules (historical rule_results rows are never touched,
# so old inspections keep the rules that were applied at their time).
def _seed_rules():
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        for r in RULES:
            row = db.query(models.ComplianceRule).filter_by(rule_code=r["rule_code"]).first()
            if row is None:
                row = models.ComplianceRule(**{k: v for k, v in r.items()
                                               if hasattr(models.ComplianceRule, k)})
                row.source_reference = f"{r.get('source_document','')} — {r.get('source_section','')}".strip(" —")
                db.add(row)
            else:
                for k, v in r.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.source_reference = f"{r.get('source_document','')} — {r.get('source_section','')}".strip(" —")
        db.commit()
    finally:
        db.close()
_seed_rules()

app = FastAPI(title="SIH26034 Legal Metrology Compliance API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/jpg"}

def audit(db: Session, event: str, inspection_id: str = "", actor: str = "system",
          before: dict = None, after: dict = None, reason: str = ""):
    db.add(models.AuditLog(inspection_id=inspection_id, event=event, actor=actor,
                           before=before or {}, after=after or {}, reason=reason))
    db.commit()

@app.get("/api/health")
def health():
    from app.services.vision import describe_providers
    return {"status": "ok", "vision_provider": get_provider().name,
            "demo_mode": settings.DEMO_MODE, "providers": describe_providers()}

@app.get("/api/rules")
def list_rules(db: Session = Depends(get_db)):
    return [ {"rule_code": r.rule_code, "rule_version": r.rule_version, "title": r.title,
              "description": r.description, "requirement": r.requirement, "severity": r.severity,
              "source_reference": r.source_reference, "rule_status": getattr(r, "rule_status", "UNVERIFIED"),
              "source_document": getattr(r, "source_document", ""), "source_section": getattr(r, "source_section", ""),
              "source_url": getattr(r, "source_url", ""), "verification_notes": getattr(r, "verification_notes", ""),
              "is_demo_rule": r.is_demo_rule, "active": r.active}
             for r in db.query(models.ComplianceRule).all() ]

@app.post("/api/inspections")
def create_inspection(payload: InspectionCreate, db: Session = Depends(get_db)):
    insp = models.Inspection(officer_email=payload.officer_email, product_name=payload.product_name,
                             is_demo=payload.is_demo, status="CREATED", compliance_status="PENDING")
    db.add(insp); db.commit(); db.refresh(insp)
    # stash demo hint in audit for analyze step
    audit(db, "INSPECTION_CREATED", insp.id, payload.officer_email, {}, {"product": payload.product_name}, payload.demo_hint)
    return {"id": insp.id, "status": insp.status}

@app.post("/api/inspections/{iid}/upload")
async def upload_image(iid: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    insp = db.query(models.Inspection).filter_by(id=iid).first()
    if not insp: raise HTTPException(404, "Inspection not found")
    if file.content_type not in ALLOWED:
        raise HTTPException(400, f"Invalid file type {file.content_type}. Use JPG/PNG/WebP.")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"File too large. Max {settings.MAX_UPLOAD_MB} MB.")
    img_dir = os.path.join(settings.INSPECTION_IMAGE_DIR, iid, "original")
    os.makedirs(img_dir, exist_ok=True)
    safe = f"{uuid.uuid4().hex}_{os.path.basename(file.filename or 'upload.jpg')}"
    path = os.path.join(img_dir, safe)
    with open(path, "wb") as f: f.write(data)
    try:
        with Image.open(path) as im: w, h = im.size
    except Exception: w, h = 0, 0
    db.add(models.InspectionImage(inspection_id=iid, storage_path=path, original_filename=file.filename or safe,
                                  mime_type=file.content_type, width=w, height=h))
    db.commit()
    audit(db, "IMAGE_UPLOADED", iid, insp.officer_email, {}, {"file": safe, "bytes": len(data)})
    return {"path": path, "width": w, "height": h}

@app.post("/api/inspections/{iid}/analyze")
def analyze(iid: str, provider: str = Query(""), db: Session = Depends(get_db)):
    from app.services.parse import merge_fields, empty_fields
    from app.services.consistency import detect_conflicts, coverage, attention
    insp = db.query(models.Inspection).filter_by(id=iid).first()
    if not insp: raise HTTPException(404, "Inspection not found")
    audit(db, "ANALYSIS_STARTED", iid, insp.officer_email)
    # Live Mode must never silently use the demo provider.
    requested = (provider or settings.VISION_PROVIDER).lower()
    if not insp.is_demo and requested == "demo" and settings.VISION_PROVIDER == "demo":
        pass  # server default; frontend labels provider in result — no silent claim
    hint_log = db.query(models.AuditLog).filter_by(inspection_id=iid, event="INSPECTION_CREATED").first()
    hint = (hint_log.reason if hint_log else "") + " " + (insp.product_name or "")
    images = db.query(models.InspectionImage).filter_by(inspection_id=iid).order_by(models.InspectionImage.created_at).all()
    if not images:
        raise HTTPException(400, "No images uploaded for this inspection.")
    prov = get_provider(requested if insp.is_demo else (provider or settings.VISION_PROVIDER))
    if not insp.is_demo and prov.name == "demo_ocr":
        audit(db, "OCR_FAILED", iid, "system", {}, {"error": "Live OCR provider not configured (VISION_PROVIDER=demo)."})
        raise HTTPException(503, "Live OCR is unavailable: server VISION_PROVIDER is 'demo'. "
                                 "Set VISION_PROVIDER=tesseract (Tesseract-OCR installed) or switch to Demo Mode.")
    t0 = datetime.utcnow()
    merged: dict = empty_fields()
    per_image: dict = {}
    raw_parts: list = []
    processed: list = []
    ok_images = 0
    for img in images:
        audit(db, "OCR_STARTED", iid, "system", {}, {"image_id": img.id, "provider": prov.name})
        try:
            res = prov.extract(img.storage_path, hint if insp.is_demo else "")
        except Exception as e:
            audit(db, "OCR_FAILED", iid, "system", {}, {"image_id": img.id, "error": str(e)})
            raise HTTPException(502, f"Automated analysis unavailable for image {img.original_filename}: {e}")
        ok_images += 1
        if res.get("processed_image"):
            img.processed_path = res["processed_image"]
            processed.append(res["processed_image"])
        raw_parts.append(f"--- {img.original_filename} ---\n{res.get('raw_text','')}")
        audit(db, "OCR_COMPLETED", iid, "system", {},
              {"image_id": img.id, "lines": res.get("lines", 0), "fields": len(res.get("fields", {}))})
        # tag every field with its source image before merging
        tagged = {}
        for fname, f in res.get("fields", {}).items():
            f = dict(f)
            bb = dict(f.get("bbox") or {})
            bb.setdefault("image_id", img.id)
            f["bbox"] = bb
            f["source_image_id"] = img.id
            tagged[fname] = f
        per_image[img.id] = tagged
        merged = merge_fields(merged, tagged)
    # persist fields (raw value preserved; review writes corrections separately)
    db.query(models.ExtractedField).filter_by(inspection_id=iid).delete()
    for fname, f in merged.items():
        db.add(models.ExtractedField(inspection_id=iid, field=fname, value=f.get("value",""),
                                     normalized_value=f.get("normalized", f.get("value","")),
                                     source_image_id=f.get("source_image_id",""),
                                     confidence=float(f.get("confidence",0)), source=f.get("source",prov.name),
                                     status=f.get("status","OK"), bbox=f.get("bbox",{}), original_value=f.get("value","")))
    db.commit()
    detected = sum(1 for f in merged.values() if (f.get("value") or "").strip())
    audit(db, "EXTRACTION_COMPLETED", iid, "system", {},
          {"provider": prov.name, "images": ok_images, "fields_detected": detected})
    audit(db, "FIELD_EXTRACTED", iid, "system", {}, {"fields": list(merged.keys())})
    # deterministic rules
    flat = {k: {"value": v.get("value",""), "status": v.get("status","MISSING"), "confidence": v.get("confidence",0)}
            for k, v in merged.items()}
    results = evaluate_all(flat)
    db.query(models.RuleResult).filter_by(inspection_id=iid).delete()
    for r in results:
        bb = ((merged.get(r["field"], {}) or {}).get("bbox", {}))
        db.add(models.RuleResult(inspection_id=iid, rule_code=r["rule_code"], rule_version=r["rule_version"],
                                 rule_status=r.get("rule_status","UNVERIFIED"), source_url=r.get("source_url",""),
                                 status=r["status"], severity=r["severity"], field=r["field"],
                                 expected=r["expected"], observed=r["observed"], explanation=r["explanation"],
                                 evidence={"bbox": bb, "source_reference": r.get("source_reference",""),
                                           "rule_status": r.get("rule_status","UNVERIFIED"),
                                           "verification_notes": r.get("verification_notes","")}))
    overall = aggregate(results)
    insp.compliance_status = overall
    insp.status = "ANALYZED"
    insp.provider = prov.name
    insp.rule_version_used = ", ".join(sorted({r["rule_version"] for r in results}))
    db.commit()
    # cross-image / cross-field intelligence (deterministic, evidence-backed)
    conflicts = detect_conflicts(per_image)
    cov = coverage(merged)
    attn = attention(conflicts, results, cov)
    db.query(models.Finding).filter_by(inspection_id=iid).delete()
    for f in conflicts:
        db.add(models.Finding(inspection_id=iid, kind=f["kind"], field=f["field"],
                              level=f["level"], title=f["title"], detail=f["detail"],
                              evidence=f["evidence"]))
    db.commit()
    audit(db, "CONSISTENCY_EVALUATED", iid, "system", {},
          {"conflicts": len(conflicts), "attention": attn["level"]})
    ms = int((datetime.utcnow()-t0).total_seconds()*1000)
    audit(db, "RULES_EVALUATED", iid, "system", {}, {"overall": overall, "ms": ms, "provider": prov.name})
    audit(db, "RULE_VERSION_USED", iid, "system", {}, {"versions": insp.rule_version_used})
    review_needed = sum(1 for f in merged.values() if f.get("status") != "OK" or not (f.get("value") or "").strip())
    return {"inspection_id": iid, "overall": overall, "processing_ms": ms, "provider": prov.name,
            "images_processed": ok_images,
            "fields_detected": detected, "fields_total": len(merged),
            "fields_needing_review": review_needed,
            "fields": merged, "results": results, "raw_text": "\n".join(raw_parts)[:4000],
            "findings": conflicts, "coverage": cov, "attention": attn}

@app.get("/api/inspections/{iid}/extraction")
def get_extraction(iid: str, db: Session = Depends(get_db)):
    """Structured extraction with raw/normalized values, confidence and source image."""
    insp = db.query(models.Inspection).filter_by(id=iid).first()
    if not insp: raise HTTPException(404, "Not found")
    fields = [{"field": f.field, "value": f.value, "normalized": getattr(f, "normalized_value", ""),
               "confidence": f.confidence, "source": f.source, "status": f.status,
               "source_image_id": getattr(f, "source_image_id", ""), "bbox": f.bbox,
               "is_corrected": f.is_corrected} for f in
              db.query(models.ExtractedField).filter_by(inspection_id=iid).all()]
    return {"inspection_id": iid, "provider": insp.provider, "is_demo": insp.is_demo,
            "fields": fields,
            "fields_detected": sum(1 for f in fields if (f["value"] or "").strip()),
            "fields_needing_review": sum(1 for f in fields if f["status"] != "OK" or not (f["value"] or "").strip())}

@app.get("/api/inspections/{iid}/rules")
def get_inspection_rules(iid: str, db: Session = Depends(get_db)):
    """Deterministic rule results with versions, statuses and evidence refs."""
    insp = db.query(models.Inspection).filter_by(id=iid).first()
    if not insp: raise HTTPException(404, "Not found")
    results = [{"rule_code": r.rule_code, "rule_version": r.rule_version,
                "rule_status": getattr(r, "rule_status", "UNVERIFIED"),
                "source_url": getattr(r, "source_url", ""), "status": r.status,
                "severity": r.severity, "field": r.field, "expected": r.expected, "observed": r.observed,
                "explanation": r.explanation, "evidence": r.evidence} for r in
               db.query(models.RuleResult).filter_by(inspection_id=iid).all()]
    return {"inspection_id": iid, "overall": insp.compliance_status,
            "rule_version_used": insp.rule_version_used, "results": results}

def _finding_out(f):
    return {"id": f.id, "kind": f.kind, "field": f.field, "level": f.level,
            "title": f.title, "detail": f.detail, "evidence": f.evidence or [],
            "status": f.status, "resolved_by": f.resolved_by,
            "at": str(f.created_at)}

@app.get("/api/inspections/{iid}/findings")
def get_findings(iid: str, db: Session = Depends(get_db)):
    if not db.query(models.Inspection).filter_by(id=iid).first():
        raise HTTPException(404, "Not found")
    return [_finding_out(f) for f in
            db.query(models.Finding).filter_by(inspection_id=iid).order_by(models.Finding.created_at).all()]

@app.post("/api/inspections/{iid}/findings/{fid}/resolve")
def resolve_finding(iid: str, fid: str, payload: dict = None, db: Session = Depends(get_db)):
    insp = db.query(models.Inspection).filter_by(id=iid).first()
    if not insp: raise HTTPException(404, "Not found")
    f = db.query(models.Finding).filter_by(id=fid, inspection_id=iid).first()
    if not f: raise HTTPException(404, "Finding not found")
    payload = payload or {}
    decision = str(payload.get("decision", "VERIFIED")).upper()
    if decision not in ("VERIFIED", "FALSE_POSITIVE"):
        raise HTTPException(400, "decision must be VERIFIED or FALSE_POSITIVE")
    actor = str(payload.get("actor", insp.officer_email))
    f.status = decision
    f.resolved_by = actor
    f.resolved_at = datetime.utcnow()
    db.add(models.ReviewAction(inspection_id=iid, actor=actor, action=f"FINDING_{decision}",
                               field=f.field, before=f.title, after=decision,
                               reason=str(payload.get("reason", ""))))
    db.commit()
    audit(db, "FINDING_RESOLVED", iid, actor, {}, {"finding": fid, "decision": decision})
    return {"ok": True, "status": decision}

@app.get("/api/dashboard/attention")
def attention_queue(demo: str = Query(""), db: Session = Depends(get_db)):
    """Factual review queue: what requires officer attention. No scores."""
    qry = db.query(models.Inspection).order_by(models.Inspection.created_at.desc())
    items = []
    for i in qry.all():
        if demo == "true" and not i.is_demo: continue
        if demo == "false" and i.is_demo: continue
        open_f = db.query(models.Finding).filter_by(inspection_id=i.id, status="OPEN").all()
        fails = db.query(models.RuleResult).filter_by(inspection_id=i.id, status="FAIL").count()
        reviews = db.query(models.RuleResult).filter_by(inspection_id=i.id, status="REVIEW").count()
        unread = db.query(models.ExtractedField).filter_by(inspection_id=i.id, status="UNREADABLE").count()
        level = "HIGH" if (any(f.level == "HIGH" for f in open_f) or fails) else \
                ("MEDIUM" if (open_f or reviews or unread) else "LOW")
        if level == "LOW" and i.compliance_status not in ("REVIEW_REQUIRED", "POTENTIAL_VIOLATION"):
            continue
        items.append({"id": i.id, "product": i.product_name, "level": level,
                      "open_conflicts": len(open_f),
                      "failed_rules": fails, "review_rules": reviews, "unreadable": unread,
                      "status": i.compliance_status, "created_at": str(i.created_at),
                      "is_demo": i.is_demo,
                      "reasons": ([f"Conflicting {f.field} across views" for f in open_f]
                                  + ([f"Failed rule check{'s' if fails > 1 else ''}"] if fails else [])
                                  + ([f"{reviews} rule check(s) need review"] if reviews else [])
                                  + ([f"{unread} unreadable field(s)"] if unread else []))})
    items.sort(key=lambda x: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}[x["level"]], x["created_at"]), reverse=False)
    return {"queue": items[:50],
            "counts": {"high": sum(1 for x in items if x["level"] == "HIGH"),
                       "medium": sum(1 for x in items if x["level"] == "MEDIUM"),
                       "low_no_issue": "excluded"}}

@app.get("/api/inspections/compare")
def compare_inspections(ids: str = Query(""), db: Session = Depends(get_db)):
    """Deterministic package-to-package comparison on extracted identifiers."""
    wanted = [x for x in ids.split(",") if x][:6]
    if len(wanted) < 2:
        raise HTTPException(400, "Provide at least two inspection ids: ?ids=a,b")
    cols = []
    for iid in wanted:
        insp = db.query(models.Inspection).filter_by(id=iid).first()
        if not insp: raise HTTPException(404, f"Inspection {iid[:8]} not found")
        fields = {f.field: {"value": f.value, "normalized": getattr(f, "normalized_value", ""),
                            "confidence": f.confidence, "status": f.status}
                  for f in db.query(models.ExtractedField).filter_by(inspection_id=iid).all()}
        conflicted = {f.field for f in db.query(models.Finding).filter_by(
            inspection_id=iid, status="OPEN", kind="CONFLICT").all()}
        cols.append({"id": iid, "product": insp.product_name, "status": insp.compliance_status,
                     "is_demo": insp.is_demo, "fields": fields, "conflicted": conflicted})
    keys = ["product_name", "net_quantity", "mrp", "manufacturer", "mfg_date",
            "expiry_date", "batch_lot", "consumer_care", "unit_sale_price"]
    rows = []
    for k in keys:
        vals = [(c["fields"].get(k, {}).get("normalized") or c["fields"].get(k, {}).get("value") or "").strip().casefold() for c in cols]
        internal = any(k in c["conflicted"] for c in cols)
        rows.append({"field": k, "values": [
            {"inspection": c["id"], "value": (c["fields"].get(k, {}).get("value") or ""),
             "status": (c["fields"].get(k, {}).get("status") or "MISSING")} for c in cols],
            "differs": len({v for v in vals if v}) > 1 or internal,
            "internal_conflict": internal})
    return {"columns": [{"id": c["id"], "product": c["product"], "status": c["status"]} for c in cols], "rows": rows}

@app.get("/api/inspections")
def list_inspections(status: str = Query(""), q: str = Query(""), demo: str = Query(""),
                     manufacturer: str = Query(""), finding: str = Query(""),
                     db: Session = Depends(get_db)):
    qry = db.query(models.Inspection).order_by(models.Inspection.created_at.desc()).limit(200)
    out = []
    for i in qry.all():
        if demo == "true" and not i.is_demo: continue
        if demo == "false" and i.is_demo: continue
        if status and i.compliance_status != status: continue
        if q and q.lower() not in (i.product_name or "").lower() + i.id.lower(): continue
        if manufacturer:
            m = db.query(models.ExtractedField).filter_by(inspection_id=i.id, field="manufacturer").first()
            if not m or manufacturer.lower() not in (m.value or "").lower(): continue
        if finding == "conflict":
            if not db.query(models.Finding).filter_by(inspection_id=i.id, status="OPEN").first(): continue
        elif finding == "failed_rule":
            if not db.query(models.RuleResult).filter_by(inspection_id=i.id, status="FAIL").first(): continue
        fails = db.query(models.RuleResult).filter_by(inspection_id=i.id, status="FAIL").count()
        imgs = db.query(models.InspectionImage).filter_by(inspection_id=i.id).count()
        out.append({"id": i.id, "product": i.product_name, "status": i.compliance_status,
                    "stage": i.status, "officer": i.officer_email, "created_at": str(i.created_at),
                    "issues": fails, "images": imgs, "is_demo": i.is_demo})
    return out

@app.get("/api/inspections/{iid}")
def get_inspection(iid: str, db: Session = Depends(get_db)):
    insp = db.query(models.Inspection).filter_by(id=iid).first()
    if not insp: raise HTTPException(404, "Not found")
    fields = [{"field": f.field, "value": f.value, "normalized": getattr(f, "normalized_value", ""),
               "confidence": f.confidence, "source": f.source,
               "status": f.status, "bbox": f.bbox,
               "source_image_id": getattr(f, "source_image_id", ""),
               "is_corrected": f.is_corrected} for f in
              db.query(models.ExtractedField).filter_by(inspection_id=iid).all()]
    results = [{"rule_code": r.rule_code, "rule_version": r.rule_version,
                "rule_status": getattr(r, "rule_status", "UNVERIFIED"),
                "source_url": getattr(r, "source_url", ""),
                "status": r.status,
                "severity": r.severity, "field": r.field, "expected": r.expected, "observed": r.observed,
                "explanation": r.explanation, "evidence": r.evidence} for r in
               db.query(models.RuleResult).filter_by(inspection_id=iid).all()]
    imgs = [{"id": im.id, "url": f"/api/images/{im.id}",
             "width": im.width, "height": im.height,
             "role": getattr(im, "role", "")} for im in
            db.query(models.InspectionImage).filter_by(inspection_id=iid).all()]
    reviews = [{"actor": r.actor, "action": r.action, "field": r.field, "before": r.before,
                "after": r.after, "reason": r.reason, "at": str(r.created_at)} for r in
               db.query(models.ReviewAction).filter_by(inspection_id=iid).order_by(models.ReviewAction.created_at).all()]
    return {"id": insp.id, "product": insp.product_name, "overall": insp.compliance_status, "stage": insp.status,
            "officer": insp.officer_email, "created_at": str(insp.created_at), "is_demo": insp.is_demo,
            "provider": insp.provider, "rule_version_used": insp.rule_version_used,
            "fields": fields, "results": results, "images": imgs, "reviews": reviews}

@app.get("/api/images/{image_id}")
def serve_image(image_id: str, db: Session = Depends(get_db)):
    """Serve the original evidence image by ID (never by raw path — no traversal)."""
    im = db.query(models.InspectionImage).filter_by(id=image_id).first()
    if not im or not im.storage_path or not os.path.exists(im.storage_path):
        raise HTTPException(404, "Image not found")
    return FileResponse(im.storage_path, media_type=im.mime_type or "image/jpeg",
                        filename=im.original_filename or "evidence.jpg")

@app.get("/api/inspections/{iid}/evidence")
def evidence(iid: str, db: Session = Depends(get_db)):
    fields = db.query(models.ExtractedField).filter_by(inspection_id=iid).all()
    return {"inspection_id": iid, "items": [{"field": f.field, "value": f.value, "confidence": f.confidence,
             "status": f.status, "bbox": f.bbox, "evidence_kind": "bbox" if f.bbox else "text"} for f in fields]}

@app.post("/api/inspections/{iid}/review")
def review(iid: str, payload: ReviewRequest, db: Session = Depends(get_db)):
    insp = db.query(models.Inspection).filter_by(id=iid).first()
    if not insp: raise HTTPException(404, "Not found")
    for fname, new_val in (payload.corrections or {}).items():
        f = db.query(models.ExtractedField).filter_by(inspection_id=iid, field=fname).first()
        if f:
            before = f.value
            db.add(models.ReviewAction(inspection_id=iid, actor=payload.actor, action="FIELD_EDITED",
                                       field=fname, before=before, after=new_val, reason=payload.notes))
            f.value = new_val; f.status = "OK" if new_val.strip() else "MISSING"; f.is_corrected = True
    if payload.confirm_violation:
        db.add(models.ReviewAction(inspection_id=iid, actor=payload.actor, action="VIOLATION_CONFIRMED", reason=payload.notes))
    if payload.mark_false_positive:
        db.add(models.ReviewAction(inspection_id=iid, actor=payload.actor, action="FALSE_POSITIVE", reason=payload.notes))
    if payload.notes and not payload.corrections:
        db.add(models.ReviewAction(inspection_id=iid, actor=payload.actor, action="NOTE", reason=payload.notes))
    # re-evaluate deterministic rules on corrected fields
    fields = {f.field: {"value": f.value, "status": f.status, "confidence": f.confidence}
              for f in db.query(models.ExtractedField).filter_by(inspection_id=iid).all()}
    if fields:
        results = evaluate_all(fields)
        db.query(models.RuleResult).filter_by(inspection_id=iid).delete()
        for r in results:
            db.add(models.RuleResult(inspection_id=iid, rule_code=r["rule_code"], rule_version=r["rule_version"],
                                     rule_status=r.get("rule_status","UNVERIFIED"), source_url=r.get("source_url",""),
                                     status=r["status"], severity=r["severity"], field=r["field"],
                                     expected=r["expected"], observed=r["observed"], explanation=r["explanation"],
                                     evidence={"rule_status": r.get("rule_status","UNVERIFIED"),
                                               "verification_notes": r.get("verification_notes","")}))
        insp.compliance_status = aggregate(results)
        insp.rule_version_used = ", ".join(sorted({r["rule_version"] for r in results}))
    insp.status = "REVIEWED"
    db.commit()
    if payload.corrections:
        audit(db, "FIELD_REVIEWED", iid, payload.actor, {}, {"fields": list(payload.corrections.keys())})
    for fid in (getattr(payload, "resolve_findings", None) or []):
        f = db.query(models.Finding).filter_by(id=fid, inspection_id=iid).first()
        if f and f.status == "OPEN":
            decision = (getattr(payload, "finding_decision", None) or "VERIFIED").upper()
            if decision not in ("VERIFIED", "FALSE_POSITIVE"):
                decision = "VERIFIED"
            f.status = decision
            f.resolved_by = payload.actor
            f.resolved_at = datetime.utcnow()
            db.add(models.ReviewAction(inspection_id=iid, actor=payload.actor, action=f"FINDING_{decision}",
                                       field=f.field, before=f.title, after=decision, reason=payload.notes))
            db.commit()
            audit(db, "FINDING_RESOLVED", iid, payload.actor, {}, {"finding": fid, "decision": decision})
    audit(db, "REVIEW_COMPLETED", iid, payload.actor, {}, {"notes": payload.notes})
    return {"ok": True, "overall": insp.compliance_status}

@app.get("/api/dashboard/stats")
def stats(demo: str = Query(""), db: Session = Depends(get_db)):
    all_i = db.query(models.Inspection).all()
    if demo == "true":
        all_i = [i for i in all_i if i.is_demo]
    elif demo == "false":
        all_i = [i for i in all_i if not i.is_demo]
    def c(s): return len([i for i in all_i if i.compliance_status == s])
    today = datetime.utcnow().date()
    today_n = len([i for i in all_i if i.created_at and i.created_at.date() == today])
    by_day = {}
    for i in all_i:
        d = str(i.created_at.date()) if i.created_at else "unknown"
        by_day[d] = by_day.get(d, 0) + 1
    fails = {}
    for r in db.query(models.RuleResult).filter_by(status="FAIL").all():
        fails[r.rule_code] = fails.get(r.rule_code, 0) + 1
    return {"total": len(all_i), "today": today_n, "compliant": c("COMPLIANT"),
            "potential_violation": c("POTENTIAL_VIOLATION"), "review_required": c("REVIEW_REQUIRED"),
            "pending": c("PENDING"), "inspections_over_time": [{"date": k, "count": v} for k, v in sorted(by_day.items())],
            "status_distribution": [{"status": s, "count": c(s)} for s in ["COMPLIANT","POTENTIAL_VIOLATION","REVIEW_REQUIRED","PENDING"]],
            "top_issues": [{"rule": k, "count": v} for k, v in sorted(fails.items(), key=lambda x: -x[1])[:8]]}

@app.get("/api/audit/{iid}")
def audit_for(iid: str, db: Session = Depends(get_db)):
    logs = db.query(models.AuditLog).filter_by(inspection_id=iid).order_by(models.AuditLog.created_at).all()
    return [{"event": l.event, "actor": l.actor, "at": str(l.created_at), "before": l.before, "after": l.after, "reason": l.reason} for l in logs]

@app.get("/api/audit")
def audit_all(demo: str = Query(""), db: Session = Depends(get_db)):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(200).all()
    if demo in ("true", "false"):
        want_demo = demo == "true"
        # str() normalization: on Postgres ids come back as UUID objects,
        # on SQLite as plain strings — compare textually on both.
        insp_ids = {str(i.id): bool(i.is_demo) for i in db.query(models.Inspection).all()}
        logs = [l for l in logs
                if (str(l.inspection_id) in insp_ids and insp_ids[str(l.inspection_id)] == want_demo)]
    return [{"inspection_id": l.inspection_id, "event": l.event, "actor": l.actor, "at": str(l.created_at), "reason": l.reason} for l in logs]

@app.post("/api/inspections/{iid}/reports")
def gen_report(iid: str, db: Session = Depends(get_db)):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    insp = db.query(models.Inspection).filter_by(id=iid).first()
    if not insp: raise HTTPException(404, "Not found")
    os.makedirs("./data/reports", exist_ok=True)
    pdf_path = f"./data/reports/{iid}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=A4)
    y = 800
    c.setFont("Helvetica-Bold", 16); c.drawString(40, y, "Packaged Commodity Screening Report (SIH26034)"); y -= 24
    c.setFont("Helvetica", 10)
    mode = "DEMO (simulated OCR)" if insp.is_demo else "LIVE"
    for line in [f"Inspection ID: {insp.id}", f"Date: {insp.created_at}", f"Officer: {insp.officer_email}",
                 f"Product: {insp.product_name}", f"Automated screening result: {insp.compliance_status}",
                 f"Mode: {mode} | Extraction provider: {insp.provider or 'n/a'}",
                 f"Rule versions applied: {insp.rule_version_used or 'n/a'}",
                 "Disclaimer: automated screening is not a final legal determination. Human verification required."]:
        c.drawString(40, y, line[:110]); y -= 16
    first_img = db.query(models.InspectionImage).filter_by(inspection_id=iid).order_by(models.InspectionImage.created_at).first()
    if first_img and first_img.storage_path and os.path.exists(first_img.storage_path):
        try:
            c.drawImage(first_img.storage_path, 40, y - 170, width=220, height=160,
                        preserveAspectRatio=True, anchor="nw")
            y -= 180
        except Exception:
            pass
    y -= 8; c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "AI-extracted information (not legal findings)"); y -= 18
    c.setFont("Helvetica", 9)
    for f in db.query(models.ExtractedField).filter_by(inspection_id=iid).all():
        c.drawString(40, y, f"{f.field}: {f.value[:70]} [{f.status}, conf {f.confidence:.2f}]"); y -= 13
        if y < 60: c.showPage(); y = 800
    y -= 6; c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Deterministic rule results"); y -= 18
    c.setFont("Helvetica", 9)
    for r in db.query(models.RuleResult).filter_by(inspection_id=iid).all():
        tag = getattr(r, "rule_status", "UNVERIFIED")
        c.drawString(40, y, f"{r.rule_code} v{r.rule_version} [{tag}]: {r.status} — {r.explanation[:80]}"); y -= 13
        if y < 60: c.showPage(); y = 800
    y -= 6; c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Cross-view consistency findings"); y -= 18
    c.setFont("Helvetica", 9)
    finds = db.query(models.Finding).filter_by(inspection_id=iid).order_by(models.Finding.created_at).all()
    if not finds:
        c.drawString(40, y, "No cross-view inconsistencies detected."); y -= 13
    for fn in finds:
        c.drawString(40, y, f"[{fn.level}] {fn.title} ({fn.status})"); y -= 13
        for ev in (fn.evidence or [])[:4]:
            c.drawString(55, y, f"- {str(ev.get('value',''))[:60]} [image {str(ev.get('image_id',''))[:8]}]"); y -= 13
            if y < 60: c.showPage(); y = 800
        if y < 60: c.showPage(); y = 800
    y -= 6; c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Officer review decisions"); y -= 18
    c.setFont("Helvetica", 9)
    revs = db.query(models.ReviewAction).filter_by(inspection_id=iid).order_by(models.ReviewAction.created_at).all()
    if not revs:
        c.drawString(40, y, "No officer review recorded."); y -= 13
    for rv in revs:
        c.drawString(40, y, f"{rv.created_at} {rv.actor} {rv.action} {rv.field} {rv.before[:30]}->{rv.after[:30]}".strip()[:110]); y -= 13
        if y < 60: c.showPage(); y = 800
    c.save()
    db.add(models.Report(inspection_id=iid, pdf_path=pdf_path, generated_by=insp.officer_email))
    insp.status = "REPORTED"; db.commit()
    audit(db, "REPORT_GENERATED", iid, insp.officer_email, {}, {"pdf": pdf_path})
    return {"pdf": pdf_path}

@app.get("/api/inspections/{iid}/report.pdf")
def dl_report(iid: str, db: Session = Depends(get_db)):
    path = f"./data/reports/{iid}.pdf"
    if not os.path.exists(path): raise HTTPException(404, "Generate report first")
    return FileResponse(path, media_type="application/pdf", filename=f"inspection-{iid}.pdf")
