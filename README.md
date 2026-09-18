# SIH26034 — AI-Assisted Legal Metrology Packaged Commodities Compliance System

> AI-assisted packaged commodity compliance **screening and inspection platform**.
> AI READS and EXTRACTS. Rule engine CHECKS. Officer REVIEWS. System DOCUMENTS.

## Architecture
IMAGE → preprocessing → OCR/vision (provider abstraction) → structured extraction
→ deterministic rule engine → COMPLIANT / POTENTIAL_VIOLATION / REVIEW_REQUIRED
→ evidence + human review → report → Supabase Postgres → dashboard.

- Frontend: React + TS + Vite + Tailwind + Router + Recharts + TanStack Table (`frontend/`)
- Backend: FastAPI + Pydantic + SQLAlchemy (`backend/app/`)
- DB: Supabase Postgres (prod) / SQLite fallback (local dev). Schema in `supabase/migrations/0001_init.sql`
- Storage: Supabase Storage `inspection-images/` or local `./data/images`

## Quickstart
### Backend
```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev   # http://localhost:5173 (proxies /api → :8000)
```

Copy `.env.example` → `.env` and fill Supabase keys for prod. Never commit `.env`.

## Demo (2–3 min)
1. Dashboard → New Inspection → choose demo scenario (compliant / violation / review)
2. Upload any JPG/PNG/WebP → Analyze → see fields + bboxes + rule results
3. Review/edit → confirm → generate PDF → history + stats update

Demo extraction is deterministic and labelled DEMO DATA. No fake AI claims.

## Rules
10 versioned rules in `backend/app/rules/registry.py`, pure functions in `engine.py`.
8 × VERIFIED against Legal Metrology (Packaged Commodities) Rules, 2011 Rule 6
(Dept. of Consumer Affairs sources, see registry docstring); 2 × UNVERIFIED
(unit sale price — conditional applicability; batch/lot — not a PCR mandate).
## Inspection intelligence (no extra manual work)
- **Smart Scan**: guided multi-view capture — the app retains useful frames with
  measured quality verdicts (brightness/contrast/blur) and warns on
  near-duplicate views (dHash). Officer reviews exceptions, not every photo.
- **Coverage map**: per-declaration FOUND / LOW_CONFIDENCE / UNREADABLE / MISSING.
  Missing alone is never a violation — applicability comes from verified rules.
- **Cross-view conflicts**: same declaration differing across views (e.g. 1 kg vs
  500 g) becomes an evidence-backed finding (`POTENTIAL INCONSISTENCY —
  officer verification required`), never an auto-violation.
- **Attention queue** (`GET /api/dashboard/attention`): HIGH / MEDIUM / LOW
  factual buckets with reasons — no risk scores, no probabilities.
- **Package comparison** (`GET /api/inspections/compare?ids=a,b`): deterministic
  side-by-side of extracted values with differences highlighted.
- Findings persist (`findings` table, migration `0003_findings.sql`) and resolve
  via review (VERIFIED / FALSE_POSITIVE) with full audit trail.
Tests: `cd backend; python -m pytest tests -q` (43 passed).
UI shows VERIFIED / UNVERIFIED pills with source links. Details: `docs/phase2.md`.

## Phase 2 — Real OCR
`VISION_PROVIDER=tesseract` uses real Tesseract OCR 5.4: EXIF fix → resize →
grayscale/autocontrast/denoise/sharpen → word-level TSV → regex structured
extraction (`services/parse.py`) → normalization (`services/normalize.py`,
raw + normalized kept). Original preserved; processed copy stored alongside.
Setup: install Tesseract-OCR (Windows: `winget install UB-Mannheim.TesseractOCR`),
optionally set `TESSERACT_CMD`. Confidence thresholds via `OCR_HIGH_CONF`
(0.75) / `OCR_MED_CONF` (0.45) — system thresholds, not legal ones.
Multi-image: all images OCR'd, fields merged by best confidence with
per-field `source_image_id`. Live Mode with unconfigured OCR returns 503 —
never silent demo fallback.

## API
POST /api/inspections, POST .../upload, POST .../analyze, GET .../{id},
GET /api/inspections, POST .../review, POST .../reports, GET .../report.pdf,
GET /api/dashboard/stats, GET /api/rules, GET /api/audit[/{id}], GET /api/health

## Limitations
- Live OCR needs the Tesseract binary (see Phase 2); without it Live analyze returns 503
- Handwriting, curved/glossy labels,Hindi/regional scripts need additional OCR tuning
- Quantitative metrology (numeral heights, permissible error, pack sizes) is out of scope
- Auth is officer-email passthrough (Supabase Auth can be wired)
- SQLite fallback uses string UUIDs; Supabase uses uuid type — migration provided
- Reports are server PDFs without embedded photo (photo shown in UI evidence)

## Deployment
- Frontend: Vercel/Netlify (`frontend/dist` via `npm run build`)
- Backend: Render/Railway/Fly (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`)
- DB/Storage: Supabase (run migration, create `inspection-images` bucket, set DATABASE_URL + keys)
