# Architecture
See README. Key separation: `services/vision.py` (AI), `rules/engine.py` (deterministic), `main.py` (orchestration), React (presentation). No LLM legal verdicts.
# Rule engine
Pure functions `evaluate_all(fields) → results`, `aggregate(results) → status`. Statuses PASS/FAIL/REVIEW/NOT_APPLICABLE; severities INFO/WARNING/HIGH. Overall: any HIGH FAIL or any FAIL → POTENTIAL_VIOLATION; else any REVIEW → REVIEW_REQUIRED; else COMPLIANT.
# Database
Tables: inspections, inspection_images, extracted_fields, compliance_rules, rule_results, review_actions, audit_logs, reports. Migration: supabase/migrations/0001_init.sql.
# API
REST JSON, correct codes, no stack traces. See README list.
# Demo
Scan page scenario select drives DemoVisionProvider hint: compliant/violation/review. Labelled DEMO DATA.
