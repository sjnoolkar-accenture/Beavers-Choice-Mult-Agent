"""SQLite connection lifecycle, schema management, and seed data."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .constants import CATALOG, HISTORICAL_QUOTES, INITIAL_DATE, STARTING_CASH_CENTS


class Database:
    """Own SQLite connections and transaction boundaries."""

    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            if connection.in_transaction:
                connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self, reset: bool = False) -> None:
        if reset and self.path.exists():
            self.path.unlink()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    item_name TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents > 0),
                    min_stock_level INTEGER NOT NULL CHECK(min_stock_level >= 0)
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT REFERENCES products(item_name),
                    transaction_type TEXT NOT NULL
                        CHECK(transaction_type IN ('stock_orders', 'sales')),
                    units INTEGER,
                    amount_cents INTEGER NOT NULL,
                    transaction_date TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_text TEXT NOT NULL,
                    total_amount_cents INTEGER NOT NULL,
                    quote_explanation TEXT NOT NULL,
                    order_date TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_transactions_item_date_type
                    ON transactions(item_name, transaction_date, transaction_type);
                CREATE INDEX IF NOT EXISTS idx_transactions_date
                    ON transactions(transaction_date);
                CREATE INDEX IF NOT EXISTS idx_quotes_order_date
                    ON quotes(order_date DESC);
                """
            )
            if connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
                return
            connection.executemany(
                """
                INSERT INTO products(
                    item_name, category, unit_price_cents, min_stock_level
                ) VALUES (?, ?, ?, ?)
                """,
                [
                    (name, category, cents, minimum)
                    for name, category, cents, _, minimum in CATALOG
                ],
            )
            connection.execute(
                """
                INSERT INTO transactions(
                    item_name, transaction_type, units, amount_cents, transaction_date
                ) VALUES (NULL, 'sales', NULL, ?, ?)
                """,
                (STARTING_CASH_CENTS, INITIAL_DATE),
            )
            connection.executemany(
                """
                INSERT INTO transactions(
                    item_name, transaction_type, units, amount_cents, transaction_date
                ) VALUES (?, 'stock_orders', ?, ?, ?)
                """,
                [
                    (name, stock, stock * cents, INITIAL_DATE)
                    for name, _, cents, stock, _ in CATALOG
                ],
            )
            connection.executemany(
                """
                INSERT INTO quotes(
                    request_text, total_amount_cents, quote_explanation, order_date
                ) VALUES (?, ?, ?, ?)
                """,
                HISTORICAL_QUOTES,
            )
