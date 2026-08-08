"""Starter-compatible helper facade used by framework agent tools."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from .services.dates import normalize_date, supplier_delivery_date

if TYPE_CHECKING:
    from .application import BeaverChoiceApplication

_default_application: BeaverChoiceApplication | None = None


def configure_default_application(application: BeaverChoiceApplication) -> None:
    global _default_application
    _default_application = application


def _app(
    application: BeaverChoiceApplication | None,
) -> BeaverChoiceApplication:
    selected = application or _default_application
    if selected is None:
        raise RuntimeError("No BeaverChoiceApplication has been configured")
    return selected


def create_transaction(
    item_name: str | None,
    transaction_type: str,
    quantity: int | None,
    price: Decimal | float,
    date_value: str | date | datetime,
    *,
    application: BeaverChoiceApplication | None = None,
) -> int:
    app = _app(application)
    with app.database.transaction() as connection:
        return app.transactions.create(
            item_name,
            transaction_type,
            quantity,
            Decimal(str(price)),
            normalize_date(date_value),
            connection,
        )


def get_all_inventory(
    as_of_date: str, *, application: BeaverChoiceApplication | None = None
) -> dict[str, int]:
    app = _app(application)
    return app.inventory.snapshot(as_of_date)


def get_stock_level(
    item_name: str,
    as_of_date: str | date | datetime,
    *,
    application: BeaverChoiceApplication | None = None,
) -> int:
    app = _app(application)
    return app.inventory.stock_level(item_name, normalize_date(as_of_date))


def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    return supplier_delivery_date(input_date_str, quantity)


def get_cash_balance(
    as_of_date: str | date | datetime,
    *,
    application: BeaverChoiceApplication | None = None,
) -> Decimal:
    app = _app(application)
    return app.transactions.cash_balance(normalize_date(as_of_date))


def generate_financial_report(
    as_of_date: str | date | datetime,
    *,
    application: BeaverChoiceApplication | None = None,
) -> dict[str, Any]:
    app = _app(application)
    return app.reporting.financial_report(normalize_date(as_of_date))


def search_quote_history(
    search_terms: list[str],
    limit: int = 5,
    *,
    application: BeaverChoiceApplication | None = None,
) -> list[dict[str, Any]]:
    app = _app(application)
    return app.quotes.search(search_terms, limit)
