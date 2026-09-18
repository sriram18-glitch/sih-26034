"""Normalization utilities. Always keep raw_value AND normalized_value —
normalization must never change legal meaning, only formatting."""
import re
from datetime import datetime

CURRENCY_WORDS = {"rs": "₹", "re": "₹", "inr": "₹", "rupees": "₹", "₹": "₹", "$": "$"}

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

UNIT_MAP = {
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    "kg": "kg", "kgs": "kg", "kilo": "kg", "kilogram": "kg",
    "ml": "ml", "millilitre": "ml", "milliliter": "ml",
    "l": "L", "lt": "L", "ltr": "L", "litre": "L", "liter": "L",
    "mg": "mg", "pcs": "pcs", "pc": "pcs", "nos": "pcs", "units": "pcs",
}

def normalize_quantity(raw: str) -> dict:
    """Parse '500 g', 'Net Wt. 5kg', '1 L' → {number, unit, normalized}."""
    t = clean_text(raw).lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*([a-z]+)?", t)
    if not m:
        return {"raw": raw, "normalized": clean_text(raw), "number": None, "unit": None}
    number = float(m.group(1))
    unit = UNIT_MAP.get((m.group(2) or "").strip(), (m.group(2) or "").strip() or None)
    norm = f"{int(number) if number == int(number) else number} {unit}" if unit else str(m.group(1))
    return {"raw": raw, "normalized": norm.strip(), "number": number, "unit": unit}

def normalize_mrp(raw: str) -> dict:
    """Parse 'MRP ₹250', 'Rs. 250.00', 'INR 250 (incl. of all taxes)'."""
    t = clean_text(raw)
    cur = None
    for word, sym in CURRENCY_WORDS.items():
        if re.search(rf"{re.escape(word)}", t, re.I):
            cur = sym
            break
    m = re.search(r"(\d+(?:\.\d{1,2})?)", t.replace(",", ""))
    amount = float(m.group(1)) if m else None
    incl_taxes = bool(re.search(r"incl[^a-z]*of all taxes|inclusive of all taxes", t, re.I))
    norm = f"{cur or ''}{int(amount) if amount == int(amount) else amount}" if amount is not None else t
    return {"raw": raw, "normalized": norm, "currency": cur, "amount": amount,
            "incl_all_taxes": incl_taxes}

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

def normalize_date(raw: str) -> dict:
    """Parse '01/2026', 'Jan 2025', '12-2024', 'Best before 6 months'."""
    t = clean_text(raw)
    m = re.search(r"(\d{1,2})[/\-.](\d{2,4})", t)
    if m:
        a, b = int(m.group(1)), m.group(2)
        year = int(b) if len(b) == 4 else (2000 + int(b) if int(b) < 50 else 1900 + int(b))
        month = a if 1 <= a <= 12 else None
        return {"raw": raw, "normalized": f"{month:02d}/{year}" if month else t,
                "month": month, "year": year}
    m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{2,4})", t, re.I)
    if m:
        y = m.group(2)
        year = int(y) if len(y) == 4 else (2000 + int(y) if int(y) < 50 else 1900 + int(y))
        return {"raw": raw, "normalized": f"{MONTHS[m.group(1).lower()]:02d}/{year}",
                "month": MONTHS[m.group(1).lower()], "year": year}
    m = re.search(r"best\s+(before|use by|within)[^\d]*(\d+)\s*(month|day|year)", t, re.I)
    if m:
        return {"raw": raw, "normalized": clean_text(m.group(0)), "month": None, "year": None,
                "relative": True}
    return {"raw": raw, "normalized": t, "month": None, "year": None}

def normalize_phone_email(raw: str) -> dict:
    t = clean_text(raw)
    phones = re.findall(r"(?:1800|1860|\+?91[\-\s]?)?\d[\d\-\s]{7,14}\d", t)
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", t)
    return {"raw": raw, "normalized": t, "phones": phones, "emails": emails}
