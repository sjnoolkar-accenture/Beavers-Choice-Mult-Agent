from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from beavers_choice.application import create_application
from beavers_choice.evaluation import evaluate_requests


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_REQUESTS = ROOT / "quote_requests_sample.csv"


def make_app(tmp_path: Path):
    return create_application(tmp_path / "test.db", reset=True)


def test_opening_assets_balance(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    report = app.reporting.financial_report("2025-01-01")
    assert report["cash_balance"] == Decimal("47885.00")
    assert report["inventory_value"] == Decimal("2115.00")
    assert report["total_assets"] == Decimal("50000.00")


def test_parser_resolves_customer_language(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    items = app.parser.parse_items(
        '500 sheets of 8.5"x11" colored paper, '
        "300 sheets of cardstock, and 200 rolls of decorative washi tape."
    )
    assert [(item.item_name, item.quantity) for item in items] == [
        ("Colored paper", 500),
        ("Cardstock", 300),
        ("Decorative adhesive tape (washi tape)", 200),
    ]


def test_unknown_product_is_rejected_without_cash_change(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    cash_before = app.transactions.cash_balance("2025-04-15")
    result = app.agents.handle_request(
        "Please deliver 200 balloons by April 15, 2025.", "2025-04-03"
    )
    assert not result.fulfilled
    assert "not carried" in result.response
    assert app.transactions.cash_balance("2025-04-15") == cash_before


def test_multi_line_failure_rolls_back_earlier_reorder(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    stock_before = app.inventory.stock_level("A4 paper", "2025-04-01")
    cash_before = app.transactions.cash_balance("2025-04-01")
    result = app.agents.handle_request(
        "I need 2,000 sheets of A4 paper and 5,000 sheets of A3 paper "
        "by April 5, 2025.",
        "2025-04-01",
    )
    assert not result.fulfilled
    assert "supplier arrival" in result.response
    assert app.inventory.stock_level("A4 paper", "2025-04-01") == stock_before
    assert app.transactions.cash_balance("2025-04-01") == cash_before


def test_fulfilled_order_updates_stock_and_cash(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    stock_before = app.inventory.stock_level("Glossy paper", "2025-04-01")
    cash_before = app.transactions.cash_balance("2025-04-01")
    result = app.agents.handle_request(
        "Please deliver 200 sheets of glossy paper by April 15, 2025.",
        "2025-04-01",
    )
    assert result.fulfilled
    assert result.total_amount > 0
    assert (
        app.inventory.stock_level("Glossy paper", "2025-04-01")
        == stock_before - 200
    )
    assert app.transactions.cash_balance("2025-04-01") > cash_before


def test_volume_discount_boundaries(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    assert app.pricing.volume_discount(499) == Decimal("0")
    assert app.pricing.volume_discount(500) == Decimal("0.05")
    assert app.pricing.volume_discount(1000) == Decimal("0.10")
    assert app.pricing.volume_discount(2000) == Decimal("0.15")


def test_full_evaluation_is_deterministic_and_meets_rubric(
    tmp_path: Path,
) -> None:
    first_app = create_application(tmp_path / "first.db", reset=True)
    second_app = create_application(tmp_path / "second.db", reset=True)
    first_results = tmp_path / "first.csv"
    second_results = tmp_path / "second.csv"

    first = evaluate_requests(first_app, SAMPLE_REQUESTS, first_results)
    second = evaluate_requests(second_app, SAMPLE_REQUESTS, second_results)

    assert first.requests == 20
    assert first.fulfilled >= 3
    assert first.rejected >= 1
    assert first.cash_changes >= 3
    assert first.model_dump(exclude={"results_path"}) == second.model_dump(
        exclude={"results_path"}
    )
    assert first_results.read_bytes() == second_results.read_bytes()

    with first_results.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert all(row["response"] for row in rows if row["fulfilled"] == "False")
