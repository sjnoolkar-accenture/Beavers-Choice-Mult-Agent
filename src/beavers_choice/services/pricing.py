"""Historical quote retrieval and bounded volume pricing."""

from __future__ import annotations

import sqlite3
from decimal import Decimal, ROUND_HALF_UP

from ..models import QuoteLine
from ..repositories import ProductRepository, QuoteRepository
from .parsing import RequestParser

CENT = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


class PricingService:
    def __init__(
        self,
        products: ProductRepository,
        quotes: QuoteRepository,
        parser: RequestParser,
    ):
        self.products = products
        self.quotes = quotes
        self.parser = parser

    @staticmethod
    def volume_discount(quantity: int) -> Decimal:
        if quantity >= 2000:
            return Decimal("0.15")
        if quantity >= 1000:
            return Decimal("0.10")
        if quantity >= 500:
            return Decimal("0.05")
        return Decimal("0")

    def quote_history(
        self,
        item_name: str,
        limit: int = 5,
        connection: sqlite3.Connection | None = None,
    ) -> list[dict]:
        terms = [word for word in item_name.lower().split() if len(word) > 2]
        return self.quotes.search(terms, limit, connection)

    def build_quote(
        self,
        item_name: str,
        quantity: int,
        connection: sqlite3.Connection | None = None,
    ) -> QuoteLine:
        product = self.products.get(item_name, connection)
        cost = Decimal(product["unit_price"])
        discount = self.volume_discount(quantity)
        history = self.quote_history(item_name, 5, connection)
        base_unit = cost * Decimal("1.35")

        historical_units = []
        for record in history:
            comparable_items = self.parser.parse_items(record["original_request"])
            comparable_quantity = sum(item.quantity for item in comparable_items)
            if comparable_quantity:
                historical_units.append(
                    Decimal(record["total_amount"]) / comparable_quantity
                )
        if historical_units:
            historical_mean = sum(historical_units) / len(historical_units)
            base_unit = (
                Decimal("0.75") * base_unit
                + Decimal("0.25") * historical_mean
            )

        quoted_unit = max(
            cost * Decimal("1.12"),
            base_unit * (Decimal("1") - discount),
        ).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)
        line_total = (quoted_unit * quantity).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        return QuoteLine(
            item_name=item_name,
            quantity=quantity,
            unit_price=quoted_unit,
            line_total=line_total,
            discount_rate=discount,
        )
