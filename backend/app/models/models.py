"""Relational schema: inspections, images, products, fields, rules, results, evidence, reviews, reports, audits."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from app.db.database import Base

def uid():
    return str(uuid.uuid4())

class Inspection(Base):
    __tablename__ = "inspections"
    id = Column(String, primary_key=True, default=uid)
    officer_id = Column(String, default="officer-demo")
    officer_email = Column(String, default="officer@gov.in")
    status = Column(String, default="CREATED")  # CREATED, ANALYZED, REVIEWED, REPORTED
    compliance_status = Column(String, default="PENDING")  # COMPLIANT, POTENTIAL_VIOLATION, REVIEW_REQUIRED
    product_name = Column(String, default="")
    is_demo = Column(Boolean, default=False)
    provider = Column(String, default="")  # extraction provider used at analyze time
    rule_version_used = Column(String, default="")  # engine registry snapshot, e.g. "v2.0.0-2026-09"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InspectionImage(Base):
    __tablename__ = "inspection_images"
    id = Column(String, primary_key=True, default=uid)
    inspection_id = Column(String, ForeignKey("inspections.id"), index=True)
    storage_path = Column(String, default="")
    processed_path = Column(String, default="")  # OCR-preprocessed copy; original is evidence
    role = Column(String, default="")  # front/back/side/label — officer-labelled
    original_filename = Column(String, default="")
    mime_type = Column(String, default="")
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    id = Column(String, primary_key=True, default=uid)
    inspection_id = Column(String, ForeignKey("inspections.id"), index=True)
    field = Column(String, index=True)
    value = Column(Text, default="")  # raw extracted value (never overwritten by review)
    normalized_value = Column(Text, default="")  # formatted variant; raw preserved in value
    source_image_id = Column(String, default="")  # which image supplied this field
    confidence = Column(Float, default=0.0)
    source = Column(String, default="demo_ocr")
    status = Column(String, default="OK")  # OK, UNREADABLE, MISSING
    bbox = Column(JSON, default=dict)  # {x,y,w,h} normalized 0..1
    is_corrected = Column(Boolean, default=False)
    original_value = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class ComplianceRule(Base):
    __tablename__ = "compliance_rules"
    id = Column(String, primary_key=True, default=uid)
    rule_code = Column(String, unique=True, index=True)
    rule_version = Column(String, default="1.0.0")
    title = Column(String, default="")
    description = Column(Text, default="")
    requirement = Column(Text, default="")
    severity = Column(String, default="WARNING")
    source_reference = Column(String, default="")
    rule_status = Column(String, default="UNVERIFIED")  # VERIFIED / UNVERIFIED
    source_document = Column(String, default="")
    source_section = Column(String, default="")
    source_url = Column(String, default="")
    verification_notes = Column(Text, default="")
    is_demo_rule = Column(Boolean, default=False)
    active = Column(Boolean, default=True)

class RuleResult(Base):
    __tablename__ = "rule_results"
    id = Column(String, primary_key=True, default=uid)
    inspection_id = Column(String, ForeignKey("inspections.id"), index=True)
    rule_code = Column(String, index=True)
    rule_version = Column(String, default="1.0.0")
    rule_status = Column(String, default="UNVERIFIED")
    source_url = Column(String, default="")
    status = Column(String, default="REVIEW")  # PASS, FAIL, REVIEW, NOT_APPLICABLE
    severity = Column(String, default="WARNING")
    field = Column(String, default="")
    expected = Column(Text, default="")
    observed = Column(Text, default="")
    explanation = Column(Text, default="")
    evidence = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

class ReviewAction(Base):
    __tablename__ = "review_actions"
    id = Column(String, primary_key=True, default=uid)
    inspection_id = Column(String, ForeignKey("inspections.id"), index=True)
    actor = Column(String, default="officer-demo")
    action = Column(String, default="NOTE")
    field = Column(String, default="")
    before = Column(Text, default="")
    after = Column(Text, default="")
    reason = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=uid)
    inspection_id = Column(String, default="", index=True)
    event = Column(String, index=True)
    actor = Column(String, default="system")
    before = Column(JSON, default=dict)
    after = Column(JSON, default=dict)
    reason = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True, default=uid)
    inspection_id = Column(String, ForeignKey("inspections.id"), index=True)
    pdf_path = Column(String, default="")
    generated_by = Column(String, default="officer-demo")
    created_at = Column(DateTime, default=datetime.utcnow)

class Finding(Base):
    """Cross-image/cross-field intelligence finding. Deterministic, evidence-backed.
    Never a legal conclusion — officer resolves via review."""
    __tablename__ = "findings"
    id = Column(String, primary_key=True, default=uid)
    inspection_id = Column(String, ForeignKey("inspections.id"), index=True)
    kind = Column(String, default="CONFLICT")  # CONFLICT
    field = Column(String, default="")
    level = Column(String, default="MEDIUM")  # HIGH / MEDIUM
    title = Column(Text, default="")
    detail = Column(Text, default="")
    evidence = Column(JSON, default=list)  # [{image_id, bbox, value}]
    status = Column(String, default="OPEN")  # OPEN / VERIFIED / FALSE_POSITIVE
    resolved_by = Column(String, default="")
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
