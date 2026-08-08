# Beaver's Choice Paper Company Multi-Agent System

## Executive summary

This project implements a production-structured, text-only sales and inventory
workflow for Beaver's Choice Paper Company. It uses four `pydantic-ai` agents,
below the limit of five, with deterministic domain services and a transactional
SQLite persistence layer.

The system:

- answers inventory questions and evaluates replenishment needs;
- creates explainable quotes using catalog cost, historical quotes, and volume
  discounts;
- checks supplier lead time and available cash;
- atomically completes feasible orders;
- rejects unsupported products and impossible deadlines with clear reasons;
- generates financial and inventory reports; and
- evaluates all requests in `quote_requests_sample.csv`.

Business-critical decisions do not require an API key. The agents define role
boundaries and framework-native tools, while typed services control products,
quantities, prices, dates, stock, and database writes.

## Submitted artifacts

- `agent_workflow.png` - architecture, tool ownership, helper mappings, and data
  flow.
- `src/beavers_choice/` - installable production package.
- `beavers_choice_agents.py` - backward-compatible launcher.
- `pyproject.toml` - package metadata, dependencies, extras, and CLI entrypoint.
- `tests/test_system.py` - focused regression and rubric tests.
- `test_results.csv` - results from all 20 supplied sample requests.
- `PROJECT_REPORT.md` - this design and evaluation report.

## Production project structure

```text
Beavers-Choice-Mult-Agent/
|-- pyproject.toml
|-- beavers_choice_agents.py
|-- src/beavers_choice/
|   |-- agents.py
|   |-- application.py
|   |-- database.py
|   |-- repositories.py
|   |-- helpers.py
|   |-- models.py
|   |-- evaluation.py
|   |-- diagram.py
|   |-- cli.py
|   `-- services/
|       |-- dates.py
|       |-- parsing.py
|       |-- pricing.py
|       |-- inventory.py
|       `-- ordering.py
`-- tests/test_system.py
```

The boundaries are intentionally explicit:

- **Domain models** define typed agent and service contracts.
- **Repositories** own SQL and persistence conversion.
- **Services** own business rules.
- **AgentSystem** owns `pydantic-ai` agents and tools.
- **Application bootstrap** wires dependencies.
- **CLI/evaluation/diagram** are delivery adapters rather than business logic.

## Agent architecture

The system uses four agents:

| Agent | Responsibility |
|---|---|
| Orchestrator Agent | Owns `process_customer_request_tool`, parses and validates the inquiry, and delegates the complete atomic workflow. |
| Inventory Agent | Reads stock, estimates supplier arrival, checks cash, and creates approved replenishment transactions. |
| Quoting Agent | Searches historical quotes and creates typed, bounded quotes with volume discounts. |
| Fulfillment Agent | Runs business-health checks, validates final stock, and records approved sales. |

Each agent is a `pydantic_ai.Agent` with `model=None`. This retains framework
tool definitions without allowing probabilistic model output to mutate stock or
money. A future LLM can be added for conversational interpretation while the
same deterministic services remain authoritative.

## Orchestration flow

1. The customer sends free text with products, quantities, and a requested
   delivery date.
2. The Orchestrator invokes the atomic order service.
3. The parser extracts and aggregates line items, resolves catalog aliases, and
   removes deadline numbers from quantity parsing.
4. Unsupported products are rejected before any database transaction begins.
5. One SQLite transaction is opened for the complete order.
6. Inventory is checked for every line. Shortages are reordered only when cash
   and supplier lead time permit.
7. The pricing service retrieves comparable historical quotes and calculates
   each line.
8. Every sale and the accepted quote are inserted in the same transaction.
9. Any exception or infeasible later line rolls back all earlier writes.
10. The customer receives a quote, promised date, and rationale, or a precise
    rejection reason.

## Starter helper review and tool assignment

All seven rubric-required helpers remain available in `helpers.py` and are
called inside framework tool definitions in `agents.py`.

| Starter helper | Purpose | Agent tool assignment |
|---|---|---|
| `create_transaction` | Records a stock order or sale. | Inventory `reorder_tool`; Fulfillment `record_sale_tool` |
| `get_all_inventory` | Returns positive stock balances as of a date. | Inventory `inventory_snapshot_tool` |
| `get_stock_level` | Returns stock for one exact catalog item. | Inventory `stock_level_tool`; Fulfillment `record_sale_tool` |
| `get_supplier_delivery_date` | Applies quantity-based supplier lead time. | Inventory `supplier_timeline_tool`; Inventory `reorder_tool` |
| `get_cash_balance` | Returns sales inflows less stock purchasing costs. | Inventory `reorder_tool` |
| `generate_financial_report` | Returns cash, inventory value, assets, item detail, and top sellers. | Fulfillment `business_health_tool` |
| `search_quote_history` | Retrieves comparable historical quotes. | Quoting `quote_history_tool` |

The helper facade preserves the course API while accepting an injected
application internally. Production services use repositories directly inside a
shared transaction.

## Persistence and transaction design

SQLite contains three indexed tables:

- `products` - canonical product, category, unit price, and minimum stock;
- `transactions` - opening cash, stock purchases, and sales; and
- `quotes` - historical and accepted customer quotes.

Money is stored as **integer cents**, eliminating binary floating-point drift.
The public API converts values to `Decimal`.

Indexes cover transaction item/date/type lookups, date-based cash reporting, and
quote recency.

The financial report uses grouped SQL to calculate all product stock and value
in one query, eliminating the previous per-product N+1 query pattern.

### Atomicity

`Database.transaction()` uses `BEGIN IMMEDIATE`, commit-on-success, and
rollback-on-error. The complete order shares one connection. If line one needs
a replenishment but line two cannot meet its deadline, line one's replenishment
is rolled back automatically. Tests explicitly verify this behavior.

## Inventory and supplier policy

Supplier lead-time bands remain:

| Shortage quantity | Lead time |
|---:|---:|
| 10 or fewer | Same day |
| 11-100 | 1 day |
| 101-1,000 | 4 days |
| More than 1,000 | 7 days |

A reorder is accepted only when:

- the supplier arrival is no later than the customer deadline; and
- current company cash can fund the purchase.

The system aggregates duplicate lines that resolve to the same catalog item,
preventing multiple lines from independently reserving the same stock.

## Pricing strategy

The pricing service uses `Decimal` throughout:

1. Begin with catalog cost plus a 35% operating uplift.
2. Search historical quotes using meaningful terms from the catalog item.
3. Normalize historical quote totals by parsed product quantity.
4. Blend current pricing at 75% and the historical unit anchor at 25%.
5. Enforce a floor of 12% above catalog cost.
6. Apply the quantity discount.

| Quantity | Discount |
|---:|---:|
| 1-499 | 0% |
| 500-999 | 5% |
| 1,000-1,999 | 10% |
| 2,000+ | 15% |

Customer responses expose unit prices, total, delivery date, and discount
rationale without revealing cash balances, exact margins, database errors, or
other customer information.

## Testing strategy

`tests/test_system.py` covers:

1. opening cash, inventory value, and total assets;
2. aliases and dimensions such as `8.5"x11"`;
3. unsupported product rejection with no cash change;
4. rollback of an earlier reorder when a later line fails;
5. stock and cash effects of a fulfilled order;
6. every volume discount boundary; and
7. deterministic full-dataset evaluation and rubric thresholds.

The automated suite passes **7 tests**.

## Evaluation method

```powershell
python -m pip install -e ".[dev,diagram]"
beavers-choice --database beavers_choice.db `
  --evaluate quote_requests_sample.csv `
  --results test_results.csv --reset
```

## Evaluation results

| Metric | Result |
|---|---:|
| Requests evaluated | 20 |
| Successfully fulfilled | 10 |
| Rejected/unfulfilled | 10 |
| Requests changing cash balance | 10 |
| Fulfilled quote value | $4,143.43 |
| Final cash balance in the evaluation horizon | $50,180.43 |

The system exceeds the rubric minimum of three fulfilled requests and three cash
changes while intentionally rejecting some requests.

- Two requests are rejected for unsupported products: balloons and tickets.
- Eight are rejected because supplier replenishment cannot meet the stated
  event deadline.

Every rejection includes an actionable reason. Rejected orders do not change
cash or leave partial replenishment writes.

## Strengths

1. **Clear agent boundaries:** Agent responsibilities and tool ownership match
   the workflow diagram.
2. **Transactional correctness:** Complete orders commit or roll back as one
   unit.
3. **Exact money handling:** Integer cents and `Decimal` avoid rounding drift.
4. **Efficient reporting:** Grouped SQL and indexes replace N+1 reads.
5. **Explainability:** Quotes and rejections expose customer-relevant rationale.
6. **No hallucinated products:** Product resolution is validated against the
   catalog.
7. **Repeatability:** Evaluation is deterministic and API-key independent.
8. **Maintainability:** Domain, persistence, orchestration, and delivery
   concerns are independently testable.

## Further improvements

1. Add purchase-order, in-transit, received, reserved, shipped, and invoiced
   states instead of representing all commitments in the transaction ledger.
2. Add a fifth Business Advisor Agent to recommend reorder points, catalog
   additions, and pricing changes from rejection and sell-through data.
3. Add guarded LLM extraction for unfamiliar language, with structured output,
   confidence thresholds, and deterministic catalog validation.
4. Offer alternatives before rejection: later delivery, reduced quantity, or a
   supported substitute.
5. Move from SQLite to PostgreSQL for concurrent workers, row-level locking,
   migrations, and production observability.
6. Add OpenTelemetry traces and structured logs with request and transaction
   correlation IDs.
7. Add authentication, authorization, rate limiting, idempotency keys, and an
   API adapter for external deployment.

## Running the project

```powershell
# Install
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,diagram]"

# Test
.\.venv\Scripts\python.exe -m pytest

# Evaluate
beavers-choice --evaluate quote_requests_sample.csv --reset

# Process one request
beavers-choice `
  --request "Please quote 500 sheets of glossy paper by April 15, 2025." `
  --date 2025-04-08

# Financial report
beavers-choice --report 2025-05-15

# Diagram
beavers-choice --diagram agent_workflow.png
```
