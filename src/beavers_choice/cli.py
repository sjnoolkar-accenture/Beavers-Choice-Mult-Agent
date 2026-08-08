"""Command-line interface for operations, evaluation, and diagrams."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from .application import create_application
from .diagram import generate_workflow_diagram
from .evaluation import evaluate_requests
from .services.dates import normalize_date


def json_default(value: Any) -> str:
    return str(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Beaver's Choice multi-agent sales system"
    )
    parser.add_argument(
        "--database", type=Path, default=Path("beavers_choice.db")
    )
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--evaluate", type=Path)
    parser.add_argument("--results", type=Path, default=Path("test_results.csv"))
    parser.add_argument("--request")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--report")
    parser.add_argument("--diagram", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.diagram:
        generate_workflow_diagram(args.diagram)
        print(f"Diagram written to {args.diagram}")
        return

    application = create_application(args.database, reset=args.reset)
    if args.evaluate:
        summary = evaluate_requests(
            application, args.evaluate, args.results
        )
        print(summary.model_dump_json(indent=2))
        return
    if args.request:
        result = application.agents.handle_request(args.request, args.date)
        print(result.model_dump_json(indent=2))
        return
    if args.report:
        report = application.reporting.financial_report(
            normalize_date(args.report)
        )
        print(json.dumps(report, indent=2, default=json_default))
        return
    print("Use --request, --evaluate, --report, or --diagram. See --help.")


if __name__ == "__main__":
    main()
