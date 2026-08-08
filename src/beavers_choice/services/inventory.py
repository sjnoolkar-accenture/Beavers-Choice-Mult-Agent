"""Inventory visibility, supplier timing, and replenishment decisions."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from ..models import ReorderDecision
from ..repositories import ProductRepository, TransactionRepository
from .dates import normalize_date, supplier_delivery_date


class InventoryService:
    def __init__(
        self,
        products: ProductRepository,
        transactions: TransactionRepository,
    ):
        self.products = products
        self.transactions = transactions

    def snapshot(
        self, as_of_date: str, connection: sqlite3.Connection | None = None
    ) -> dict[str, int]:
        return self.transactions.inventory(normalize_date(as_of_date), connection)

    def stock_level(
        self,
        item_name: str,
        as_of_date: str,
        connection: sqlite3.Connection | None = None,
    ) -> int:
        return self.transactions.stock_level(
            item_name, normalize_date(as_of_date), connection
        )

    def reorder(
        self,
        item_name: str,
        quantity: int,
        request_date: str,
        required_by: str,
        connection: sqlite3.Connection,
    ) -> ReorderDecision:
        product = self.products.get(item_name, connection)
        request_date = normalize_date(request_date)
        required_by = normalize_date(required_by)
        arrival = supplier_delivery_date(request_date, quantity)
        purchase_cost = (
            Decimal(quantity) * Decimal(product["unit_price"])
        ).quantize(Decimal("0.01"))
        cash = self.transactions.cash_balance(request_date, connection)
        if arrival > required_by:
            return ReorderDecision(
                approved=False,
                arrival=arrival,
                reason=(
                    f"supplier arrival {arrival} is after required date "
                    f"{required_by}"
                ),
            )
        if purchase_cost > cash:
            return ReorderDecision(
                approved=False,
                arrival=arrival,
                reason="available company funds cannot safely cover replenishment",
            )
        transaction_id = self.transactions.create(
            item_name,
            "stock_orders",
            quantity,
            purchase_cost,
            request_date,
            connection,
        )
        return ReorderDecision(
            approved=True,
            arrival=arrival,
            cost=purchase_cost,
            transaction_id=transaction_id,
        )
