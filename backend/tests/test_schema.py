"""Schema-convention guard: the app uses plain str ids everywhere (URL params,
filters, JSON evidence). Every id / inspection_id column must therefore be
String in the models, matching TEXT columns on Postgres (migration 0004).
A UUID-typed column would leak uuid.UUID objects into Python and crash JSON
serialization — and Postgres rejects TEXT<->UUID foreign keys outright."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqlalchemy import String
from app.models import models


def test_all_id_columns_are_string():
    for cls in (models.Inspection, models.InspectionImage, models.ExtractedField,
                models.ComplianceRule, models.RuleResult, models.ReviewAction,
                models.AuditLog, models.Report, models.Finding):
        assert isinstance(cls.__table__.c.id.type, String), cls.__tablename__


def test_all_inspection_fk_columns_are_string():
    for cls in (models.InspectionImage, models.ExtractedField, models.RuleResult,
                models.Report, models.Finding):
        col = cls.__table__.c.inspection_id
        assert isinstance(col.type, String), cls.__tablename__
        assert list(col.foreign_keys), cls.__tablename__
