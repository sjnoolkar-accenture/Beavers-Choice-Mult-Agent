# Beaver's Choice Paper Company Multi-Agent System

## Executive summary

This project implements a text-only sales and inventory workflow for Beaver's
Choice Paper Company. It uses **four `pydantic-ai` agents**, below the limit of
five, and a shared SQLite database. The system answers stock questions,
calculates explainable quotes, reorders feasible shortages, rejects impossible
deadlines or unsupported products, records completed sales, and generates
financial reports.

The implementation is intentionally deterministic. `pydantic-ai` defines the
agents, their instructions, and framework-native tools, while auditable Python
rules perform product resolution, discounting, delivery checks, and transaction
updates. This makes the evaluation repeatable and avoids requiring an API key.

## Submitted artifacts

- `agent_workflow.png` - workflow and tool ownership diagram.
- `beavers_choice_agents.py` - the complete implementation in one Python file.
- `PROJECT_REPORT.md` - this design, evaluation, and reflection report.
- `test_results.csv` - results from all 20 supplied sample requests.

`quote_requests_sample.csv` is retained beside the solution as the evaluation
input. The generated SQLite database and local virtual environment are runtime
artifacts and are not submission source files.

## Framework and architecture

The selected orchestration framework is **pydantic-ai**. Four `Agent` objects
are declared with non-overlapping instructions:

| Agent | Responsibility |
|---|---|
| Orchestrator Agent | Parses the inquiry, validates the extracted products, delegates inventory/quote/fulfillment steps, and creates the final customer-safe response. |
| Inventory Agent | Reads inventory, checks individual stock, estimates supplier delivery dates, checks purchasing cash, and records approved replenishment commitments. |
| Quoting Agent | Searches comparable historical quotes, calculates line prices, and applies transparent volume discounts. |
| Fulfillment Agent | Runs a financial health check, verifies final stock, and records approved sales. |

The agents use `model=None`, so no external LLM is needed during evaluation.
This is a deliberate reliability decision: quantities, money, inventory, and
deadlines should be controlled by deterministic business rules. The framework
still provides the agent boundaries and `@agent.tool_plain` tool contracts.

## Workflow

The flow shown in `agent_workflow.png` is:

1. The customer submits free text containing products, quantities, and usually a
   requested delivery date.
2. The Orchestrator extracts line items, normalizes aliases such as "printer
   paper," and rejects text that has no valid quantity/product pair.
3. The Inventory Agent checks each product. If stock is short, it calculates the
   supplier arrival date and approves a replenishment only when the deadline and
   cash checks both pass.
4. The Quoting Agent combines catalog cost, a bounded historical quote anchor,
   and a volume discount of 0%, 5%, 10%, or 15%.
5. The Fulfillment Agent runs a business-health check and records the sale only
   after every line in the order is feasible. Orders are atomic: the system does
   not silently fulfill only part of an order.
6. The Orchestrator returns the products, quantities, unit prices, total,
   promised date, discount rationale, or a specific rejection reason.

## Starter helper review and tool assignment

All seven rubric-required starter helpers are used inside framework tool
definitions.

| Starter helper | Purpose | Agent tool assignment |
|---|---|---|
| `create_transaction` | Records a stock purchase or sale in SQLite and returns its ID. | Inventory `reorder_tool`; Fulfillment `record_sale_tool` |
| `get_all_inventory` | Calculates positive stock balances as of a date. | Inventory `inventory_snapshot_tool` |
| `get_stock_level` | Calculates the available units for one catalog product. | Inventory `stock_level_tool`; Fulfillment `record_sale_tool` |
| `get_supplier_delivery_date` | Converts order size into a supplier lead time and arrival date. | Inventory `supplier_timeline_tool`; Inventory `reorder_tool` |
| `get_cash_balance` | Calculates sales inflows less stock-order outflows through a date. | Inventory `reorder_tool` |
| `generate_financial_report` | Produces cash, inventory value, total assets, inventory details, and top sellers. | Fulfillment `business_health_tool` |
| `search_quote_history` | Retrieves relevant prior quote records for pricing context. | Quoting `quote_history_tool` |

The implementation also provides database initialization, date normalization,
catalog resolution, request parsing, due-date extraction, quote calculation,
atomic rollback, evaluation, and diagram generation functions.

## Database design

SQLite is the single source of truth:

- `inventory` stores canonical product names, category, unit cost, and minimum
  stock level.
- `transactions` stores opening cash, starting inventory purchases,
  replenishment commitments, and sales.
- `quotes` stores historical and newly accepted quotes so later prices can use
  comparable evidence.

Opening assets are $50,000: $47,885 cash plus $2,115 of starting inventory.
Every report is reconstructed from transactions rather than a mutable cached
balance.

## Inventory and reorder policy

The Inventory Agent first uses stock already available. A shortage triggers a
supplier check using the starter lead-time bands:

- 10 units or fewer: same day
- 11-100 units: 1 day
- 101-1,000 units: 4 days
- More than 1,000 units: 7 days

A reorder is rejected when its arrival falls after the customer's deadline or
when available cash cannot fund it. Approved stock purchases and customer sales
are recorded on the commitment date; the calculated supplier arrival remains
the promised delivery constraint. This prevents later requests from
double-booking inventory already committed to an accepted order.

## Quoting strategy

The quote calculation starts from catalog unit cost with a 35% operating uplift.
When comparable historical quotes exist, their approximate unit price contributes
25% of the pricing anchor and current catalog pricing contributes 75%. A price
floor of 12% above catalog cost prevents a historical outlier from creating a
loss-making quote.

Volume discounts encourage larger purchases:

| Quantity | Discount |
|---:|---:|
| 1-499 | 0% |
| 500-999 | 5% |
| 1,000-1,999 | 10% |
| 2,000+ | 15% |

Customer responses explain the applied discount but do not expose internal
profit margins, cash balances, database errors, or unrelated customer data.

## Evaluation method

The command below reset the database, processed every row in the supplied CSV in
request-date order, and wrote `test_results.csv`:

```powershell
.\.venv\Scripts\python.exe .\beavers_choice_agents.py `
  --evaluate .\quote_requests_sample.csv `
  --results .\test_results.csv --reset
```

Each result records request ID/date, job and event context, status, fulfillment
flag, promised date, quote total, cash balance, inventory value, whether cash
changed, and the complete customer-facing response.

## Evaluation results

| Metric | Result |
|---|---:|
| Requests evaluated | 20 |
| Successfully fulfilled | 10 |
| Rejected/unfulfilled | 10 |
| Requests changing cash balance | 10 |
| Fulfilled quote value | $4,143.67 |
| Final cash balance in the evaluation horizon | $50,180.67 |

The system exceeds the minimum requirement of three fulfilled requests and three
cash changes, while intentionally leaving some requests unfulfilled.

Two requests were rejected because the catalog does not carry a requested item:
balloons in request 2 and tickets in request 20. Eight later requests were
rejected because replenishment could not arrive by the specified event date.
For example, request 9 needed A4 paper by April 10, but the supplier estimate was
April 11. These messages provide actionable reasons instead of generic failure
text.

### Strengths demonstrated

1. **Reliable constraint handling:** Stock, supplier lead time, cash, and deadline
   checks happen before a sale is committed.
2. **Accurate transaction effects:** Every fulfilled request changed the cash
   balance, while rejected requests did not.
3. **Explainable customer output:** Fulfilled responses include quantities, unit
   prices, total, delivery date, and discount rationale. Rejections identify the
   unsupported item or impossible timeline.
4. **No hallucinated products:** Unknown products are not silently mapped to the
   nearest catalog item.
5. **Atomic orders:** Replenishment transactions are rolled back if any line
   fails, preventing partial database updates.
6. **Repeatable evaluation:** The rules do not depend on model temperature,
   network availability, or an API key.

## Limitations and improvements

1. **Add a fifth Business Advisor Agent.** It could analyze sell-through,
   rejection causes, cash utilization, and reorder frequency, then recommend new
   reorder points or catalog additions. Repeated balloon/ticket requests could
   become evidence for product expansion.
2. **Use reservations and receiving states.** A production database should
   distinguish purchase orders, in-transit stock, physical receipts, customer
   reservations, shipments, and invoices instead of representing the commitment
   with one transaction date.
3. **Improve product understanding.** A guarded LLM or embedding-based resolver
   could propose catalog matches for unfamiliar wording, with confidence
   thresholds and deterministic validation before any transaction.
4. **Optimize quotes at the order level.** The current discount applies per line.
   A future version could consider total order value, customer segment, capacity,
   seasonality, and a maximum approved discount.
5. **Add negotiation and customer confirmation.** A Customer Agent could offer a
   later delivery date, substitute product, or reduced quantity instead of
   immediately rejecting an infeasible request. A final confirmation step would
   separate quotation from binding sale.

## Running the solution

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install "pydantic-ai>=0.4.2" matplotlib
```

Process one request:

```powershell
.\.venv\Scripts\python.exe .\beavers_choice_agents.py `
  --request "Please quote 500 sheets of glossy paper by April 15, 2025." `
  --date 2025-04-08
```

Generate a financial report:

```powershell
.\.venv\Scripts\python.exe .\beavers_choice_agents.py --report 2025-05-15
```

Regenerate the workflow image:

```powershell
.\.venv\Scripts\python.exe .\beavers_choice_agents.py `
  --diagram .\agent_workflow.png
```
