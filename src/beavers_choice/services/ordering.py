"""Atomic end-to-end order orchestration."""

from __future__ import annotations

from decimal import Decimal

from ..database import Database
from ..models import ProcessResult
from ..repositories import (
    QuoteRepository,
    ReportingRepository,
    TransactionRepository,
)
from .dates import normalize_date
from .inventory import InventoryService
from .parsing import RequestParser
from .pricing import PricingService


class OrderService:
    def __init__(
        self,
        database: Database,
        parser: RequestParser,
        inventory: InventoryService,
        pricing: PricingService,
        transactions: TransactionRepository,
        quotes: QuoteRepository,
        reporting: ReportingRepository,
    ):
        self.database = database
        self.parser = parser
        self.inventory = inventory
        self.pricing = pricing
        self.transactions = transactions
        self.quotes = quotes
        self.reporting = reporting

    def process(self, request_text: str, request_date: str) -> ProcessResult:
        request_date = normalize_date(request_date)
        due_date = self.parser.parse_due_date(request_text, request_date)
        items = self.parser.parse_items(request_text)
        if not items:
            return self._rejection(
                request_date,
                "We could not identify a valid product and quantity. "
                "Please provide both.",
                [],
            )

        unknown = [item.requested_name for item in items if item.item_name is None]
        if unknown:
            return self._rejection(
                request_date,
                "We cannot fulfill this order because these products are not "
                f"carried: {', '.join(unknown)}.",
                [item.__dict__ for item in items],
            )

        with self.database.transaction() as connection:
            health = self.reporting.financial_report(request_date, connection)
            if health["cash_balance"] <= 0:
                return self._rejection(
                    request_date,
                    "We cannot accept the order while purchasing funds are "
                    "unavailable.",
                    [item.__dict__ for item in items],
                )

            availability = []
            promised_date = request_date
            for item in items:
                assert item.item_name is not None
                stock = self.inventory.stock_level(
                    item.item_name, request_date, connection
                )
                shortfall = max(0, item.quantity - stock)
                available_on = request_date
                if shortfall:
                    reorder = self.inventory.reorder(
                        item.item_name,
                        shortfall,
                        request_date,
                        due_date,
                        connection,
                    )
                    if not reorder.approved:
                        connection.rollback()
                        return self._rejection(
                            request_date,
                            (
                                "We cannot meet the requested deadline for "
                                f"{item.item_name}: {reorder.reason}."
                            ),
                            [line.__dict__ for line in items],
                        )
                    available_on = reorder.arrival
                    promised_date = max(promised_date, available_on)
                availability.append(
                    {
                        "item_name": item.item_name,
                        "quantity": item.quantity,
                        "available_on": available_on,
                        "reordered": bool(shortfall),
                    }
                )

            if promised_date > due_date:
                connection.rollback()
                return self._rejection(
                    request_date,
                    f"We cannot deliver by {due_date}; earliest complete delivery "
                    f"is {promised_date}.",
                    availability,
                )

            quote_lines = [
                self.pricing.build_quote(
                    item["item_name"], int(item["quantity"]), connection
                )
                for item in availability
            ]
            total = sum(
                (line.line_total for line in quote_lines), Decimal("0")
            ).quantize(Decimal("0.01"))

            for line in quote_lines:
                stock = self.inventory.stock_level(
                    line.item_name, request_date, connection
                )
                if stock < line.quantity:
                    raise RuntimeError(
                        f"Atomic stock invariant failed for {line.item_name}"
                    )
                self.transactions.create(
                    line.item_name,
                    "sales",
                    line.quantity,
                    line.line_total,
                    request_date,
                    connection,
                )

            discount_notes = sorted(
                {
                    f"{int(line.discount_rate * 100)}% volume discount"
                    for line in quote_lines
                    if line.discount_rate > 0
                }
            )
            rationale = (
                ", ".join(discount_notes)
                if discount_notes
                else "standard competitive pricing"
            )
            explanation = (
                f"Quote uses {rationale}, catalog pricing, and comparable "
                "historical quotes."
            )
            self.quotes.save(
                request_text, total, explanation, request_date, connection
            )
            line_summary = "; ".join(
                f"{line.quantity} {line.item_name} at "
                f"${line.unit_price:.4f}/unit"
                for line in quote_lines
            )
            response = (
                f"Order confirmed for delivery by {promised_date}. "
                f"{line_summary}. Total: ${total:.2f}. {explanation}"
            )
            return ProcessResult(
                status="fulfilled",
                fulfilled=True,
                request_date=request_date,
                promised_date=promised_date,
                total_amount=total,
                response=response,
                items=[
                    line.model_dump(mode="json") for line in quote_lines
                ],
            )

    @staticmethod
    def _rejection(
        request_date: str, response: str, items: list[dict]
    ) -> ProcessResult:
        return ProcessResult(
            status="rejected",
            fulfilled=False,
            request_date=request_date,
            promised_date=None,
            total_amount=Decimal("0"),
            response=response,
            items=items,
        )
