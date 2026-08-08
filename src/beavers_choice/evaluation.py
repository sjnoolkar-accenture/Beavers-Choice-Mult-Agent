"""CSV evaluation harness used by the rubric and regression tests."""

from __future__ import annotations

import csv
from pathlib import Path

from .application import BeaverChoiceApplication
from .models import EvaluationSummary
from .services.dates import normalize_date


def evaluate_requests(
    application: BeaverChoiceApplication,
    requests_path: Path,
    results_path: Path,
) -> EvaluationSummary:
    with requests_path.open(newline="", encoding="utf-8-sig") as source:
        requests = list(csv.DictReader(source))

    rows = []
    for request_id, request in enumerate(requests, start=1):
        request_date = normalize_date(request["request_date"])
        evaluation_date = application.parser.parse_due_date(
            request["request"], request_date
        )
        cash_before = application.transactions.cash_balance(evaluation_date)
        result = application.agents.handle_request(
            request["request"], request_date
        )
        report = application.reporting.financial_report(evaluation_date)
        cash_changed = report["cash_balance"] != cash_before
        rows.append(
            {
                "request_id": request_id,
                "request_date": request_date,
                "job": request.get("job", ""),
                "event": request.get("event", ""),
                "status": result.status,
                "fulfilled": result.fulfilled,
                "promised_date": result.promised_date or "",
                "total_amount": f"{result.total_amount:.2f}",
                "cash_balance": f"{report['cash_balance']:.2f}",
                "inventory_value": f"{report['inventory_value']:.2f}",
                "cash_changed": cash_changed,
                "response": result.response,
            }
        )

    results_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    with results_path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    fulfilled = sum(bool(row["fulfilled"]) for row in rows)
    return EvaluationSummary(
        requests=len(rows),
        fulfilled=fulfilled,
        rejected=len(rows) - fulfilled,
        cash_changes=sum(bool(row["cash_changed"]) for row in rows),
        results_path=str(results_path),
    )
