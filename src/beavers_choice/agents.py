"""Pydantic-AI agent definitions and framework-native tools."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pydantic_ai import Agent

from .helpers import (
    create_transaction,
    generate_financial_report,
    get_all_inventory,
    get_cash_balance,
    get_stock_level,
    get_supplier_delivery_date,
    search_quote_history,
)
from .models import ProcessResult

if TYPE_CHECKING:
    from .application import BeaverChoiceApplication


class AgentSystem:
    """Own the orchestrator and three non-overlapping worker agents."""

    def __init__(self, application: BeaverChoiceApplication):
        self.application = application
        self.inventory_agent = Agent(
            model=None,
            name="inventory_agent",
            instructions=(
                "Own inventory visibility, stock risk, supplier lead times, "
                "and approved reorders."
            ),
        )
        self.quoting_agent = Agent(
            model=None,
            name="quoting_agent",
            instructions=(
                "Build competitive quotes from catalog cost, volume discounts, "
                "and quote history."
            ),
        )
        self.fulfillment_agent = Agent(
            model=None,
            name="fulfillment_agent",
            instructions=(
                "Validate business health and atomically record approved sales."
            ),
        )
        self.orchestrator_agent = Agent(
            model=None,
            name="orchestrator_agent",
            instructions=(
                "Parse each inquiry and delegate inventory, quoting, and "
                "fulfillment decisions."
            ),
        )
        self._register_tools()

    def _register_tools(self) -> None:
        application = self.application

        @self.inventory_agent.tool_plain
        def inventory_snapshot_tool(as_of_date: str) -> dict[str, int]:
            """List all inventory through get_all_inventory."""
            return get_all_inventory(as_of_date, application=application)

        @self.inventory_agent.tool_plain
        def stock_level_tool(item_name: str, as_of_date: str) -> int:
            """Check one product through get_stock_level."""
            return get_stock_level(
                item_name, as_of_date, application=application
            )

        @self.inventory_agent.tool_plain
        def supplier_timeline_tool(request_date: str, quantity: int) -> str:
            """Estimate arrival through get_supplier_delivery_date."""
            return get_supplier_delivery_date(request_date, quantity)

        @self.inventory_agent.tool_plain
        def reorder_tool(
            item_name: str,
            quantity: int,
            request_date: str,
            required_by: str,
        ) -> dict[str, Any]:
            """Approve a standalone reorder using cash and transaction helpers."""
            arrival = get_supplier_delivery_date(request_date, quantity)
            if arrival > required_by:
                return {
                    "approved": False,
                    "arrival": arrival,
                    "reason": "supplier arrival is after the required date",
                }
            product = application.products.get(item_name)
            cost = Decimal(quantity) * product["unit_price"]
            if get_cash_balance(request_date, application=application) < cost:
                return {
                    "approved": False,
                    "arrival": arrival,
                    "reason": "available funds cannot cover replenishment",
                }
            transaction_id = create_transaction(
                item_name,
                "stock_orders",
                quantity,
                cost,
                request_date,
                application=application,
            )
            return {
                "approved": True,
                "arrival": arrival,
                "cost": str(cost),
                "transaction_id": transaction_id,
            }

        @self.quoting_agent.tool_plain
        def quote_history_tool(
            item_name: str, limit: int = 5
        ) -> list[dict[str, Any]]:
            """Retrieve comparisons through search_quote_history."""
            terms = [
                word for word in item_name.lower().split() if len(word) > 2
            ]
            return search_quote_history(
                terms, limit, application=application
            )

        @self.quoting_agent.tool_plain
        def build_quote_tool(item_name: str, quantity: int) -> dict[str, Any]:
            """Create a typed quote using the pricing service."""
            return application.pricing.build_quote(
                item_name, quantity
            ).model_dump(mode="json")

        @self.fulfillment_agent.tool_plain
        def business_health_tool(as_of_date: str) -> dict[str, Any]:
            """Run generate_financial_report before large commitments."""
            report = generate_financial_report(
                as_of_date, application=application
            )
            return {
                "cash_balance": str(report["cash_balance"]),
                "inventory_value": str(report["inventory_value"]),
                "total_assets": str(report["total_assets"]),
            }

        @self.fulfillment_agent.tool_plain
        def record_sale_tool(
            item_name: str,
            quantity: int,
            amount: Decimal,
            sale_date: str,
        ) -> int:
            """Validate stock and record a sale through create_transaction."""
            stock = get_stock_level(
                item_name, sale_date, application=application
            )
            if stock < quantity:
                raise ValueError(
                    f"Cannot sell {quantity} units; only {stock} available."
                )
            return create_transaction(
                item_name,
                "sales",
                quantity,
                amount,
                sale_date,
                application=application,
            )

        @self.orchestrator_agent.tool_plain
        def process_customer_request_tool(
            request_text: str, request_date: str
        ) -> ProcessResult:
            """Delegate the complete request to the atomic order service."""
            return application.orders.process(request_text, request_date)

        self.inventory_snapshot_tool = inventory_snapshot_tool
        self.stock_level_tool = stock_level_tool
        self.supplier_timeline_tool = supplier_timeline_tool
        self.reorder_tool = reorder_tool
        self.quote_history_tool = quote_history_tool
        self.build_quote_tool = build_quote_tool
        self.business_health_tool = business_health_tool
        self.record_sale_tool = record_sale_tool
        self.process_customer_request_tool = process_customer_request_tool

    def handle_request(
        self, request_text: str, request_date: str
    ) -> ProcessResult:
        return self.process_customer_request_tool(request_text, request_date)
