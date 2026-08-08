"""SQLite repositories with optional shared transaction connections."""

from __future__ import annotations

import sqlite3
from contextlib import nullcontext
from decimal import Decimal
from typing import Any, ContextManager

from .database import Database


def cents_to_decimal(value: int) -> Decimal:
    return (Decimal(value) / Decimal(100)).quantize(Decimal("0.01"))


def decimal_to_cents(value: Decimal) -> int:
    return int((value * Decimal(100)).quantize(Decimal("1")))


class Repository:
    def __init__(self, database: Database):
        self.database = database

    def connection(
        self, connection: sqlite3.Connection | None
    ) -> ContextManager[sqlite3.Connection]:
        return nullcontext(connection) if connection is not None else self.database.read()


class ProductRepository(Repository):
    def get(
        self, item_name: str, connection: sqlite3.Connection | None = None
    ) -> dict[str, Any]:
        with self.connection(connection) as active:
            row = active.execute(
                "SELECT * FROM products WHERE item_name = ?", (item_name,)
            ).fetchone()
        if row is None:
            raise ValueError(f"Item not carried: {item_name}")
        result = dict(row)
        result["unit_price"] = cents_to_decimal(result.pop("unit_price_cents"))
        return result

    def names(self, connection: sqlite3.Connection | None = None) -> list[str]:
        with self.connection(connection) as active:
            rows = active.execute(
                "SELECT item_name FROM products ORDER BY item_name"
            ).fetchall()
        return [str(row["item_name"]) for row in rows]


class TransactionRepository(Repository):
    def create(
        self,
        item_name: str | None,
        transaction_type: str,
        quantity: int | None,
        amount: Decimal,
        transaction_date: str,
        connection: sqlite3.Connection,
    ) -> int:
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("transaction_type must be 'stock_orders' or 'sales'")
        cursor = connection.execute(
            """
            INSERT INTO transactions(
                item_name, transaction_type, units, amount_cents, transaction_date
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                item_name,
                transaction_type,
                quantity,
                decimal_to_cents(amount),
                transaction_date,
            ),
        )
        return int(cursor.lastrowid)

    def stock_level(
        self,
        item_name: str,
        as_of_date: str,
        connection: sqlite3.Connection | None = None,
    ) -> int:
        with self.connection(connection) as active:
            row = active.execute(
                """
                SELECT COALESCE(
                    SUM(CASE WHEN transaction_type = 'stock_orders' THEN units
                             WHEN transaction_type = 'sales' THEN -units ELSE 0 END),
                    0
                ) AS current_stock
                FROM transactions
                WHERE item_name = ? AND transaction_date <= ?
                """,
                (item_name, as_of_date),
            ).fetchone()
        return int(row["current_stock"])

    def inventory(
        self, as_of_date: str, connection: sqlite3.Connection | None = None
    ) -> dict[str, int]:
        with self.connection(connection) as active:
            rows = active.execute(
                """
                SELECT item_name,
                       SUM(CASE WHEN transaction_type = 'stock_orders' THEN units
                                WHEN transaction_type = 'sales' THEN -units
                                ELSE 0 END) AS stock
                FROM transactions
                WHERE item_name IS NOT NULL AND transaction_date <= ?
                GROUP BY item_name
                HAVING stock > 0
                ORDER BY item_name
                """,
                (as_of_date,),
            ).fetchall()
        return {str(row["item_name"]): int(row["stock"]) for row in rows}

    def cash_balance(
        self, as_of_date: str, connection: sqlite3.Connection | None = None
    ) -> Decimal:
        with self.connection(connection) as active:
            row = active.execute(
                """
                SELECT COALESCE(SUM(
                    CASE WHEN transaction_type = 'sales' THEN amount_cents
                         WHEN transaction_type = 'stock_orders' THEN -amount_cents
                         ELSE 0 END
                ), 0) AS cash_cents
                FROM transactions
                WHERE transaction_date <= ?
                """,
                (as_of_date,),
            ).fetchone()
        return cents_to_decimal(int(row["cash_cents"]))


class QuoteRepository(Repository):
    def search(
        self,
        search_terms: list[str],
        limit: int = 5,
        connection: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]:
        terms = [term.strip().lower() for term in search_terms if term.strip()]
        with self.connection(connection) as active:
            rows = active.execute(
                """
                SELECT request_text AS original_request, total_amount_cents,
                       quote_explanation, order_date
                FROM quotes
                ORDER BY order_date DESC
                """
            ).fetchall()
        matches = []
        for row in rows:
            searchable = (
                f"{row['original_request']} {row['quote_explanation']}".lower()
            )
            if not terms or all(term in searchable for term in terms):
                record = dict(row)
                record["total_amount"] = cents_to_decimal(
                    record.pop("total_amount_cents")
                )
                matches.append(record)
            if len(matches) == limit:
                break
        return matches

    def save(
        self,
        request_text: str,
        total: Decimal,
        explanation: str,
        quote_date: str,
        connection: sqlite3.Connection,
    ) -> None:
        connection.execute(
            """
            INSERT INTO quotes(
                request_text, total_amount_cents, quote_explanation, order_date
            ) VALUES (?, ?, ?, ?)
            """,
            (
                request_text,
                decimal_to_cents(total),
                explanation,
                quote_date,
            ),
        )


class ReportingRepository(Repository):
    def financial_report(
        self, as_of_date: str, connection: sqlite3.Connection | None = None
    ) -> dict[str, Any]:
        with self.connection(connection) as active:
            rows = active.execute(
                """
                SELECT p.item_name, p.unit_price_cents,
                       COALESCE(SUM(
                           CASE WHEN t.transaction_type = 'stock_orders' THEN t.units
                                WHEN t.transaction_type = 'sales' THEN -t.units
                                ELSE 0 END
                       ), 0) AS stock
                FROM products p
                LEFT JOIN transactions t
                  ON t.item_name = p.item_name AND t.transaction_date <= ?
                GROUP BY p.item_name, p.unit_price_cents
                ORDER BY p.item_name
                """,
                (as_of_date,),
            ).fetchall()
            cash_row = active.execute(
                """
                SELECT COALESCE(SUM(
                    CASE WHEN transaction_type = 'sales' THEN amount_cents
                         WHEN transaction_type = 'stock_orders' THEN -amount_cents
                         ELSE 0 END
                ), 0) AS cash_cents
                FROM transactions
                WHERE transaction_date <= ?
                """,
                (as_of_date,),
            ).fetchone()
            top_rows = active.execute(
                """
                SELECT item_name, SUM(units) AS total_units,
                       SUM(amount_cents) AS total_revenue_cents
                FROM transactions
                WHERE transaction_type = 'sales' AND item_name IS NOT NULL
                  AND transaction_date <= ?
                GROUP BY item_name
                ORDER BY total_revenue_cents DESC
                LIMIT 5
                """,
                (as_of_date,),
            ).fetchall()

        summary = []
        inventory_cents = 0
        for row in rows:
            stock = int(row["stock"])
            value_cents = stock * int(row["unit_price_cents"])
            inventory_cents += value_cents
            summary.append(
                {
                    "item_name": row["item_name"],
                    "stock": stock,
                    "unit_price": cents_to_decimal(int(row["unit_price_cents"])),
                    "value": cents_to_decimal(value_cents),
                }
            )
        cash = cents_to_decimal(int(cash_row["cash_cents"]))
        inventory_value = cents_to_decimal(inventory_cents)
        return {
            "as_of_date": as_of_date,
            "cash_balance": cash,
            "inventory_value": inventory_value,
            "total_assets": cash + inventory_value,
            "inventory_summary": summary,
            "top_selling_products": [
                {
                    "item_name": row["item_name"],
                    "total_units": int(row["total_units"]),
                    "total_revenue": cents_to_decimal(
                        int(row["total_revenue_cents"])
                    ),
                }
                for row in top_rows
            ],
        }
