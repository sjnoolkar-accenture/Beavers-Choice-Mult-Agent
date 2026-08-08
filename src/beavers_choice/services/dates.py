"""Date normalization and supplier lead-time policies."""

from __future__ import annotations

from datetime import date, datetime, timedelta


def normalize_date(value: str | date | datetime) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date: {value!r}")


def supplier_delivery_date(input_date: str, quantity: int) -> str:
    start = datetime.strptime(normalize_date(input_date), "%Y-%m-%d").date()
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7
    return (start + timedelta(days=days)).isoformat()
