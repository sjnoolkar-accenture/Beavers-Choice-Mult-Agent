"""Deterministic parsing with strict catalog resolution."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from ..constants import ALIASES, DUE_DATE_PATTERN, ITEM_PATTERN, QUALIFIERS
from ..models import LineItem
from .dates import normalize_date


class RequestParser:
    def resolve_item_name(self, raw_name: str) -> str | None:
        normalized = re.sub(r"[^a-z0-9]+", " ", raw_name.lower()).strip()
        for keyword, item in QUALIFIERS:
            if keyword in normalized:
                return item
        if "a3" in normalized:
            return "A3 paper"
        if "a4" in normalized:
            return "A4 paper"
        if "printer" in normalized or "printing" in normalized:
            return "Standard copy paper"
        for alias, item in sorted(
            ALIASES.items(), key=lambda pair: len(pair[0]), reverse=True
        ):
            if alias in normalized:
                return item
        return None

    def parse_items(self, request_text: str) -> list[LineItem]:
        text = DUE_DATE_PATTERN.sub("", request_text)
        text = re.sub(
            r'8\.5\s*"\s*x\s*11\s*"', "letter-sized ", text, flags=re.IGNORECASE
        )
        items = []
        for match in ITEM_PATTERN.finditer(text):
            quantity = int(match.group("quantity").replace(",", ""))
            name = re.sub(r"\s+", " ", match.group("name")).strip(" ,-:")
            name = re.sub(
                r"^(?:sheets?|reams?|rolls?|packets?|packs?|boxes?|units?)"
                r"\s+(?:of\s+)?",
                "",
                name,
                flags=re.IGNORECASE,
            ).strip()
            name = re.sub(
                r"\b(?:in|for)\s+(?:assorted|various|different)\s+colors?.*$",
                "",
                name,
                flags=re.IGNORECASE,
            ).strip()
            if quantity > 0 and name:
                items.append(
                    LineItem(name, self.resolve_item_name(name), quantity)
                )

        unique: dict[tuple[str, int], LineItem] = {}
        for item in items:
            unique[(item.requested_name.lower(), item.quantity)] = item

        aggregated: dict[str, LineItem] = {}
        for item in unique.values():
            key = item.item_name or item.requested_name.lower()
            if key in aggregated:
                previous = aggregated[key]
                aggregated[key] = LineItem(
                    f"{previous.requested_name}; {item.requested_name}",
                    item.item_name,
                    previous.quantity + item.quantity,
                )
            else:
                aggregated[key] = item
        return list(aggregated.values())

    def parse_due_date(self, request_text: str, request_date: str) -> str:
        match = DUE_DATE_PATTERN.search(request_text)
        if match:
            parsed = datetime.strptime(
                f"{match.group('month')} {match.group('day')} {match.group('year')}",
                "%B %d %Y",
            )
            return parsed.date().isoformat()
        start = datetime.strptime(normalize_date(request_date), "%Y-%m-%d").date()
        return (start + timedelta(days=14)).isoformat()
